"""
JARVIS V4 — Autonomous Voice System Validation & Self-Healing Suite.

Exercises the real VoiceRuntime pipeline (state machine, interrupt manager,
VAD, streaming STT/TTS, audio queue, conversation manager, push-to-talk,
and UI events) with mocked audio I/O so it is deterministic and headless.

A single shared VoiceRuntime is initialized once per session (the STT model
load is the only slow step) and reused across every validation step.

Run:
    pytest tests/test_voice_validation.py -v
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import os
import tempfile
import time
import wave
from unittest.mock import MagicMock

import numpy as np
import pytest

from jarvis.events import EventType, get_event_bus, reset_event_bus
from jarvis.voice.audio_queue import AudioChunk, AudioQueue
from jarvis.voice.conversation_manager import ConversationManager
from jarvis.voice.speech_state import SpeechState, SpeechStateMachine
from jarvis.voice.streaming_stt import StreamingSTT
from jarvis.voice.streaming_tts import StreamingTTS
from jarvis.voice.vad import VAD
from jarvis.voice.voice_events import (
    emit_playback_finished,
    emit_playback_started,
    emit_stt_final,
    emit_stt_partial,
    emit_tts_chunk,
    emit_tts_finished,
    emit_tts_started,
    emit_voice_interrupted,
    emit_voice_started,
    emit_voice_stopped,
)
from jarvis.voice.voice_runtime import VoiceConfig, VoiceInitResult, VoiceRuntime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared session runtime (initialize once — STT model load is the slow part)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def runtime():
    rt = VoiceRuntime(VoiceConfig())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(asyncio.wait_for(rt.initialize(), timeout=120))
        yield result, rt
        loop.run_until_complete(rt.shutdown())
    finally:
        # Cancel any lingering tasks, then close the loop cleanly.
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(asyncio.sleep(0)) if not loop.is_closed() else None
        loop.close()


@pytest.fixture(autouse=True)
def _isolate_runtime(runtime, request):
    """Ensure every test starts (and ends) from a clean shared runtime.

    The shared runtime is reused across the whole module, so tests that call
    ``rt.interrupt()`` must not leak interrupt/queue/state into the next test.
    """
    _, rt = runtime
    logger.warning(
        "[iso BEFORE %s] interrupted=%s state=%s qsize=%s conv=%s",
        request.node.name,
        rt._interrupt_manager.is_interrupted(),
        rt.speech_state.value,
        rt._audio_queue._queue.qsize(),
        rt._conversation_manager.active,
    )
    yield
    logger.warning(
        "[iso AFTER %s] interrupted=%s state=%s qsize=%s conv=%s",
        request.node.name,
        rt._interrupt_manager.is_interrupted(),
        rt.speech_state.value,
        rt._audio_queue._queue.qsize(),
        rt._conversation_manager.active,
    )
    rt.reset_state()


def make_wav_bytes(seconds: float = 1.0, sr: int = 16000) -> bytes:
    n = int(seconds * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((np.zeros(n, dtype=np.int16)).tobytes())
    return buf.getvalue()


def make_tone_wav_bytes(seconds: float = 1.0, sr: int = 16000, freq: float = 440.0) -> bytes:
    n = int(seconds * sr)
    t = np.linspace(0, seconds, n, endpoint=False)
    tone = (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(tone.tobytes())
    return buf.getvalue()


class FakeSTT:
    def __init__(self, words):
        self._words = list(words)
        self.status = MagicMock()
        self.status.READY = "ready"
        self.calls = 0

    async def transcribe_bytes(self, audio):
        self.calls += 1
        return " ".join(self._words[: min(self.calls, len(self._words))]) or None


class FakeStreamingSTT:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.status = MagicMock()
        self.status.READY = "ready"
        self.stream_calls = 0

    async def transcribe_bytes(self, audio):
        return " ".join(self._chunks)

    async def transcribe_stream(self, audio_path):
        self.stream_calls += 1
        for chunk in self._chunks:
            yield chunk


async def _async_gen(items):
    for i in items:
        yield i


class _FakeStreamingTTS:
    """Plain fake exposing ``synthesize_stream`` (the real streaming contract)."""

    status = "ready"

    def __init__(self, chunks: int = 3):
        self._chunks = [
            np.zeros(800, dtype=np.int16).tobytes() for _ in range(chunks)
        ]

    def synthesize_stream(self, text):
        async def _gen():
            for c in self._chunks:
                yield c

        return _gen()


def _make_fake_tts(chunks: int = 3):
    return _FakeStreamingTTS(chunks)


# ---------------------------------------------------------------------------
# STEP 1 — Startup Validation
# ---------------------------------------------------------------------------


class TestStartupValidation:
    @pytest.mark.asyncio
    async def test_runtime_initializes_all_components(self, runtime):
        result, rt = runtime
        assert isinstance(result, VoiceInitResult)
        assert rt._interrupt_manager is not None
        assert rt._state_machine is not None
        assert rt._vad is not None
        assert rt._audio_queue is not None
        assert rt._streaming_stt is not None
        assert rt._streaming_tts is not None
        assert rt._conversation_manager is not None
        assert rt.wake_word is not None
        assert rt.stt is not None
        assert rt.tts is not None

    @pytest.mark.asyncio
    async def test_no_exception_during_init(self, runtime):
        result, _ = runtime
        assert result is not None


# ---------------------------------------------------------------------------
# STEP 2 — State Machine Validation
# ---------------------------------------------------------------------------


class TestStateMachineValidation:
    # Start state is IDLE; the list below is the sequence of *transitions*
    # beginning from IDLE (first element is the first transition target).
    EXPECTED = [
        SpeechState.WAKE_LISTENING,
        SpeechState.LISTENING,
        SpeechState.TRANSCRIBING,
        SpeechState.PLANNING,
        SpeechState.RESPONDING,
        SpeechState.STREAMING,
        SpeechState.SPEAKING,
        SpeechState.INTERRUPTED,
        SpeechState.LISTENING,
        SpeechState.IDLE,
    ]

    def setup_method(self):
        reset_event_bus()
        self.sm = SpeechStateMachine()
        self.seen = []
        self.sm.on_transition(lambda old, new: self.seen.append(new))

    @staticmethod
    def _goto(sm, target):
        # Walk valid edges (BFS) so we can realistically reach any state.
        from jarvis.voice.speech_state import _VALID_TRANSITIONS

        if sm.state == target:
            return
        visited = {sm.state}
        queue = [(sm.state, [])]
        path = None
        while queue:
            node, route = queue.pop(0)
            for nxt in _VALID_TRANSITIONS.get(node, set()):
                if nxt in visited:
                    continue
                visited.add(nxt)
                if nxt == target:
                    path = route + [nxt]
                    break
                queue.append((nxt, route + [nxt]))
            if path:
                break
        assert path is not None, f"no path to {target}"
        for step in path:
            assert sm.transition(step), f"transition to {step} rejected"

    def test_full_expected_sequence(self):
        for nxt in self.EXPECTED:
            assert self.sm.transition(nxt), f"transition to {nxt} rejected"
        assert self.seen == self.EXPECTED

    def test_no_duplicate_events(self):
        self.sm.transition(SpeechState.LISTENING)
        before = len(self.seen)
        assert self.sm.transition(SpeechState.LISTENING) is False
        assert len(self.seen) == before

    def test_no_invalid_transition(self):
        assert self.sm.transition(SpeechState.SPEAKING) is False
        assert self.sm.state == SpeechState.IDLE

    def test_interrupted_to_listening_valid(self):
        self._goto(self.sm, SpeechState.SPEAKING)
        assert self.sm.transition(SpeechState.INTERRUPTED)
        assert self.sm.transition(SpeechState.LISTENING)

    def test_all_transitions_idempotent_same_state(self):
        for state in SpeechState:
            sm = SpeechStateMachine()
            if sm.transition(state):
                assert sm.transition(state) is False


# ---------------------------------------------------------------------------
# STEP 3 — Interrupt Validation
# ---------------------------------------------------------------------------


class TestInterruptValidation:
    @pytest.mark.asyncio
    async def test_interrupt_clears_queue_and_state(self, runtime):
        _, rt = runtime
        rt._goto_state(SpeechState.SPEAKING)
        rt._audio_queue.enqueue(AudioChunk(data=np.zeros(1600, dtype=np.int16).tobytes()))
        assert not rt._audio_queue._queue.empty()
        bus = get_event_bus()
        bus.clear_history()
        rt.interrupt()
        assert rt._audio_queue._queue.empty()
        assert rt.speech_state == SpeechState.INTERRUPTED
        assert len(bus.history(EventType.VOICE_INTERRUPT)) >= 1

    @pytest.mark.asyncio
    async def test_interrupt_under_100ms(self, runtime):
        _, rt = runtime
        rt._state_machine.transition(SpeechState.SPEAKING)
        t0 = time.perf_counter()
        rt.interrupt()
        dt = (time.perf_counter() - t0) * 1000.0
        assert dt < 100.0, f"interrupt took {dt:.1f}ms"


# ---------------------------------------------------------------------------
# STEP 4 — Streaming STT Validation
# ---------------------------------------------------------------------------


class TestStreamingSTTValidation:
    @pytest.mark.asyncio
    async def test_partials_increasing_then_final(self):
        words = ["Hello", "Hello Jar", "Hello Jarvis"]
        backend = FakeSTT(words)
        stt = StreamingSTT(backend, sample_rate=16000, channels=1)
        stt.add_audio(make_wav_bytes(seconds=1.0))
        stt._partial_interval = 0.0  # remove throttle so every accumulation emits
        stop = asyncio.Event()

        async def collect():
            async for p in stt.stream_transcribe(stop, min_audio_seconds=0.0):
                partials.append(p)
                if len(partials) >= 3:
                    stop.set()

        partials = []
        await asyncio.wait_for(collect(), timeout=3.0)
        assert partials, "no partials produced"
        # Partials must be strictly increasing in length (no missing/duplicated chunks).
        for a, b in zip(partials, partials[1:]):
            assert len(b) >= len(a)
        # The latest partial must contain the complete final phrase.
        assert "Hello Jarvis" in partials[-1]

    @pytest.mark.asyncio
    async def test_streaming_backend_used_when_available(self):
        backend = FakeStreamingSTT(["Hello", "Hello Jar", "Hello Jarvis"])
        stt = StreamingSTT(backend, sample_rate=16000, channels=1)
        assert stt._streaming is True
        stt.add_audio(make_wav_bytes(seconds=1.0))
        stop = asyncio.Event()

        partials = []
        async for p in stt.stream_transcribe(stop, min_audio_seconds=0.0):
            partials.append(p)
            if len(partials) >= 3:
                stop.set()

        await asyncio.wait_for(asyncio.sleep(0), timeout=1.0)
        assert backend.stream_calls >= 1
        assert partials
        assert "Hello Jarvis" in partials[-1]

    @pytest.mark.asyncio
    async def test_faster_whisper_stt_stream_yields_partials(self):
        from jarvis.voice.voice_runtime import FasterWhisperSTT, VoiceConfig

        config = VoiceConfig(stt_model="tiny", stt_device="cpu")
        stt = FasterWhisperSTT(config)
        result = await stt.initialize()
        if not result.success:
            pytest.skip("faster-whisper model not available")

        wav = make_tone_wav_bytes(seconds=1.5, freq=440.0)
        fd = None
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".wav")
            with os.fdopen(fd, "wb") as f:
                f.write(wav)
                fd = -1
            partials = []
            async for p in stt.transcribe_stream(path):
                partials.append(p)
            # faster-whisper may or may not produce text from a pure tone;
            # we only verify that the stream yields at least the final batch.
            final = await stt.transcribe(path)
            if final:
                assert partials
                assert partials[-1] == final
            else:
                assert partials == []
        finally:
            if fd is not None and fd >= 0:
                with contextlib.suppress(Exception):
                    os.close(fd)
            if path:
                with contextlib.suppress(Exception):
                    os.unlink(path)


# ---------------------------------------------------------------------------
# STEP 5 — Streaming TTS Validation
# ---------------------------------------------------------------------------


class TestStreamingTTSValidation:
    @pytest.mark.asyncio
    async def test_chunks_streamed_then_queued(self, runtime):
        _, rt = runtime
        rt._interrupt_manager.clear()
        emit_tts_started()
        queued = 0
        # Stream chunks straight from a fake streaming backend and push them
        # into the live audio queue (validates immediate, non-blocking queuing).
        async for chunk in StreamingTTS(_make_fake_tts(3)).stream_speak(
            "hello", rt._interrupt_manager._async_event
        ):
            rt._audio_queue.enqueue(AudioChunk(data=chunk, sample_rate=16000))
            emit_tts_chunk(index=queued)
            queued += 1
        assert queued == 3


# ---------------------------------------------------------------------------
# STEP 6 — Audio Queue Validation
# ---------------------------------------------------------------------------


class TestAudioQueueValidation:
    @pytest.mark.asyncio
    async def test_append_cancel_flush_resume(self):
        q = AudioQueue(buffer_size=16)
        q.start(asyncio.get_event_loop())
        for _ in range(3):
            q.enqueue(AudioChunk(data=np.zeros(160, dtype=np.int16).tobytes()))
        assert q._queue.qsize() == 3
        q.pause()
        q.resume()
        q.cancel()
        assert q._queue.empty()
        await q.stop_async()

    @pytest.mark.asyncio
    async def test_concurrent_playback_no_leak(self):
        q = AudioQueue(buffer_size=16)
        q.start(asyncio.get_event_loop())
        for _ in range(10):
            q.enqueue(AudioChunk(data=np.zeros(160, dtype=np.int16).tobytes()))
        for _ in range(10):
            await asyncio.sleep(0.02)
        q.cancel()
        await q.stop_async()
        assert q._playback_task is None

    @pytest.mark.asyncio
    async def test_interrupt_while_playing_clears(self):
        q = AudioQueue(buffer_size=16)
        q.start(asyncio.get_event_loop())
        for _ in range(5):
            q.enqueue(AudioChunk(data=np.zeros(1600, dtype=np.int16).tobytes()))
        await asyncio.sleep(0.05)
        q.cancel()
        assert q._queue.empty()
        await q.stop_async()


# ---------------------------------------------------------------------------
# STEP 7 — Conversation Mode Validation
# ---------------------------------------------------------------------------


class TestConversationModeValidation:
    @pytest.mark.asyncio
    async def test_followup_then_timeout(self):
        cb = []
        mgr = ConversationManager(timeout=0.1, on_timeout=lambda: cb.append(True))
        mgr.start()
        assert mgr.active
        await asyncio.sleep(0.05)
        mgr.touch()
        await asyncio.sleep(0.05)
        assert mgr.active
        await asyncio.sleep(0.2)
        assert not mgr.active
        assert cb == [True]

    @pytest.mark.asyncio
    async def test_repeat_multiple_rounds(self):
        rounds = []
        mgr = ConversationManager(timeout=0.08, on_timeout=lambda: rounds.append(1))
        for _ in range(3):
            mgr.start()
            await asyncio.sleep(0.04)
            mgr.touch()
            await asyncio.sleep(0.04)
            mgr.stop()
        assert len(rounds) == 0


# ---------------------------------------------------------------------------
# STEP 8 — Push-to-Talk Validation
# ---------------------------------------------------------------------------


class TestPushToTalkValidation:
    @pytest.mark.asyncio
    async def test_enable_disable_no_restart(self, runtime):
        _, rt = runtime
        with pytest.MonkeyPatch().context() as mp:
            fake_kb = MagicMock()
            fake_kb.is_pressed.return_value = False
            mp.setattr("jarvis.voice.voice_runtime.keyboard", fake_kb, raising=False)
            await rt.start_push_to_talk()
            assert rt._push_to_talk_active
            await rt.stop_push_to_talk()
            assert not rt._push_to_talk_active


# ---------------------------------------------------------------------------
# STEP 9 — Voice Activity Detection Validation
# ---------------------------------------------------------------------------


class TestVADValidation:
    def setup_method(self):
        self.vad = VAD(energy_threshold=500.0, silence_duration=0.3, speech_duration=0.2)

    def test_speech_then_silence_detection(self):
        loud = (np.ones(1600, dtype=np.int16) * 8000).tobytes()
        silent = b"\x00\x00" * 1600
        assert self.vad.process_frame(loud).is_speech
        assert not self.vad.process_frame(silent).is_speech

    def test_silence_exceeded_eventually(self):
        silent = b"\x00\x00" * 1600
        t = 0.0
        with pytest.MonkeyPatch().context() as mp:
            def fake_time():
                nonlocal t
                t += 0.02
                return t

            mp.setattr("jarvis.voice.vad.time.time", fake_time)
            for _ in range(60):
                self.vad.process_frame(silent)
        assert self.vad.silence_exceeded()

    def test_energy_backend_available(self):
        assert self.vad._backend == "energy"


# ---------------------------------------------------------------------------
# STEP 10/11 — Conversation Simulation + Rapid Interrupt Stress
# ---------------------------------------------------------------------------


class TestConversationSimulation:
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, runtime, monkeypatch):
        _, rt = runtime
        monkeypatch.setattr(rt, "tts", _make_fake_tts(3))
        turns = ["Hello.", "Open VS Code.", "No, open Chrome.",
                  "Actually search obesity prediction.", "Stop."]
        for t in turns:
            rt._state_machine.transition(SpeechState.LISTENING)
            rt._state_machine.transition(SpeechState.TRANSCRIBING)
            emit_stt_partial(text=t)
            emit_stt_final(text=t)
            rt._state_machine.transition(SpeechState.RESPONDING)
            await rt.speak(f"You said: {t}")
            rt.clear_interrupt()

    @pytest.mark.asyncio
    async def test_rapid_interrupt_stress_no_crash(self, runtime, monkeypatch):
        _, rt = runtime
        monkeypatch.setattr(rt, "tts", _make_fake_tts(3))
        rt._state_machine.transition(SpeechState.SPEAKING)
        for _ in range(10):
            rt.interrupt()
            await asyncio.sleep(0.005)
            rt.clear_interrupt()
            rt._state_machine.transition(SpeechState.SPEAKING)
        assert rt._audio_queue._queue.empty()


# ---------------------------------------------------------------------------
# STEP 15 — UI Validation
# ---------------------------------------------------------------------------


class TestUIValidation:
    def setup_method(self):
        reset_event_bus()

    def test_voice_badges_events(self):
        emit_voice_started()
        emit_voice_stopped()
        emit_voice_interrupted(reason="user_speech")
        emit_tts_started()
        emit_tts_chunk(index=1)
        emit_tts_finished()
        emit_playback_started()
        emit_playback_finished()
        emit_stt_partial(text="he")
        emit_stt_final(text="hello")
        bus = get_event_bus()
        assert len(bus.history(EventType.VOICE_STATE)) >= 6
        assert len(bus.history(EventType.VOICE_INTERRUPT)) >= 1
        assert len(bus.history(EventType.VOICE_TRANSCRIPT)) == 2


# ---------------------------------------------------------------------------
# STEP 12/13/14 — Planner interrupt logic
# ---------------------------------------------------------------------------


class TestBackgroundAndPlanner:
    @pytest.mark.asyncio
    async def test_interrupt_during_planning(self):
        sm = SpeechStateMachine()
        assert sm.transition(SpeechState.LISTENING)
        assert sm.transition(SpeechState.TRANSCRIBING)
        assert sm.transition(SpeechState.PLANNING)
        assert sm.transition(SpeechState.INTERRUPTED)
        assert sm.transition(SpeechState.LISTENING)

    @pytest.mark.asyncio
    async def test_interrupt_during_response(self):
        sm = SpeechStateMachine()
        # Realistically reached via LISTENING -> TRANSCRIBING -> PLANNING -> RESPONDING.
        assert sm.transition(SpeechState.LISTENING)
        assert sm.transition(SpeechState.TRANSCRIBING)
        assert sm.transition(SpeechState.PLANNING)
        assert sm.transition(SpeechState.RESPONDING)
        assert sm.transition(SpeechState.INTERRUPTED)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
