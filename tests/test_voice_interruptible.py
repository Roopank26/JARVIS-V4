"""
Tests for enhanced JARVIS voice subsystem.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.events import EventType, get_event_bus, reset_event_bus
from jarvis.voice.audio_queue import AudioChunk, AudioQueue
from jarvis.voice.conversation_manager import ConversationManager
from jarvis.voice.interrupt_manager import InterruptManager
from jarvis.voice.speech_state import SpeechState, SpeechStateMachine
from jarvis.voice.streaming_stt import StreamingSTT
from jarvis.voice.streaming_tts import StreamingTTS
from jarvis.voice.vad import VAD
from jarvis.voice.voice_events import (
    emit_stt_final,
    emit_stt_partial,
    emit_voice_interrupted,
)


class TestInterruptManager:
    """Tests for InterruptManager."""

    def setup_method(self):
        self.manager = InterruptManager()

    def test_initial_state(self):
        assert not self.manager.is_interrupted()

    def test_interrupt_and_check(self):
        self.manager.interrupt()
        assert self.manager.is_interrupted()

    def test_clear_interrupt(self):
        self.manager.interrupt()
        self.manager.clear()
        assert not self.manager.is_interrupted()

    def test_double_interrupt_is_idempotent(self):
        self.manager.interrupt()
        self.manager.interrupt()
        assert self.manager.is_interrupted()

    def test_reset(self):
        self.manager.interrupt()
        self.manager.reset()
        assert not self.manager.is_interrupted()

    @pytest.mark.asyncio
    async def test_wait_if_interrupted_when_set(self):
        self.manager.interrupt()
        result = await asyncio.wait_for(self.manager.wait_if_interrupted(), timeout=1.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_if_interrupted_when_clear(self):
        self.manager.clear()
        start = time.time()
        task = asyncio.create_task(self.manager.wait_if_interrupted())
        await asyncio.sleep(0.1)
        self.manager.interrupt()
        await asyncio.wait_for(task, timeout=1.0)
        elapsed = time.time() - start
        assert elapsed < 0.5


class TestSpeechStateMachine:
    """Tests for SpeechStateMachine."""

    def setup_method(self):
        reset_event_bus()
        self.sm = SpeechStateMachine()

    def test_initial_state(self):
        assert self.sm.state == SpeechState.IDLE

    def test_valid_transition(self):
        assert self.sm.transition(SpeechState.WAKE_LISTENING)
        assert self.sm.state == SpeechState.WAKE_LISTENING

    def test_invalid_transition(self):
        assert self.sm.transition(SpeechState.SPEAKING) is False
        assert self.sm.state == SpeechState.IDLE

    def test_idempotent_same_state(self):
        assert self.sm.transition(SpeechState.IDLE) is False

    def test_emits_event(self):
        bus = get_event_bus()
        bus.clear_history()
        self.sm.transition(SpeechState.LISTENING)
        events = bus.history(EventType.VOICE_STATE)
        assert len(events) == 1
        assert events[0].data["state"] == SpeechState.LISTENING.value

    def test_interrupted_emits_interrupt_event(self):
        bus = get_event_bus()
        bus.clear_history()
        self.sm.transition(SpeechState.LISTENING)
        bus.clear_history()
        self.sm.transition(SpeechState.INTERRUPTED)
        events = bus.history(EventType.VOICE_INTERRUPT)
        assert len(events) == 1

    def test_listeners_called(self):
        calls = []
        self.sm.on_transition(lambda old, new: calls.append((old, new)))
        self.sm.transition(SpeechState.LISTENING)
        assert len(calls) == 1
        assert calls[0] == (SpeechState.IDLE, SpeechState.LISTENING)

    def test_is_speaking(self):
        assert not self.sm.is_speaking()
        self.sm.transition(SpeechState.LISTENING)
        self.sm.transition(SpeechState.TRANSCRIBING)
        self.sm.transition(SpeechState.RESPONDING)
        self.sm.transition(SpeechState.STREAMING)
        self.sm.transition(SpeechState.SPEAKING)
        assert self.sm.is_speaking()

    def test_is_listening(self):
        assert not self.sm.is_listening()
        self.sm.transition(SpeechState.LISTENING)
        assert self.sm.is_listening()


class TestVAD:
    """Tests for VAD."""

    def setup_method(self):
        self.vad = VAD(sample_rate=16000, energy_threshold=500.0, silence_duration=0.5)

    def test_energy_fallback_used_when_no_backends(self):
        assert self.vad._backend == "energy"

    def test_process_frame_silence(self):
        silent = b"\x00\x00" * 1600
        result = self.vad.process_frame(silent)
        assert not result.is_speech

    def test_process_frame_speech(self):
        import numpy as np

        loud = (np.ones(3200, dtype=np.int16) * 30000).tobytes()
        result = self.vad.process_frame(loud)
        assert result.is_speech

    def test_reset(self):
        import numpy as np

        loud = (np.ones(3200, dtype=np.int16) * 30000).tobytes()
        self.vad.process_frame(loud)
        self.vad.reset()
        assert self.vad._speech_start is None
        assert self.vad._silence_start is None

    def test_speech_detected(self):
        import numpy as np

        silent = b"\x00\x00" * 1600
        self.vad.process_frame(silent)
        assert not self.vad.speech_detected()
        loud = (np.ones(3200, dtype=np.int16) * 30000).tobytes()
        self.vad.process_frame(loud)
        assert self.vad.speech_detected()

    def test_silence_exceeded(self):
        silent = b"\x00\x00" * 1600
        t = 0.0
        with patch("jarvis.voice.vad.time.time", side_effect=lambda: t + 0.016):
            for _ in range(200):
                t += 0.016
                self.vad.process_frame(silent)
        assert self.vad.silence_exceeded()


class TestStreamingSTT:
    """Tests for StreamingSTT."""

    def setup_method(self):
        self.backend = MagicMock()
        self.stt = StreamingSTT(self.backend, sample_rate=16000, channels=1)

    def test_reset(self):
        self.stt.add_audio(b"\x00\x00")
        self.stt.reset()
        assert len(self.stt._accumulated) == 0

    def test_add_audio(self):
        self.stt.add_audio(b"\x00\x00" * 100)
        assert len(self.stt._accumulated) == 200

    def test_audio_length(self):
        self.stt.add_audio(b"\x00\x00" * 320)
        assert abs(self.stt.audio_length_seconds() - 0.02) < 0.001

    @pytest.mark.asyncio
    async def test_final_transcription_calls_backend(self):
        self.backend.transcribe_bytes = AsyncMock(return_value="hello world")
        self.stt.add_audio(b"\x00\x00" * 3200)
        text = await self.stt.final_transcription()
        assert text == "hello world"

    @pytest.mark.asyncio
    async def test_stream_transcribe_yields_partials(self):
        self.backend.transcribe_bytes = AsyncMock(return_value="hello")
        self.stt.add_audio(b"\x00\x00" * 3200)
        stop = asyncio.Event()
        stop.set()
        results = []
        async for partial in self.stt.stream_transcribe(stop, min_audio_seconds=0.0):
            results.append(partial)
        assert "hello" in results


class TestStreamingTTS:
    """Tests for StreamingTTS."""

    def setup_method(self):
        self.backend = MagicMock()
        self.tts = StreamingTTS(self.backend)

    @pytest.mark.asyncio
    async def test_stream_speak_yields_chunks(self):
        self.backend.speak = AsyncMock(return_value=b"audio_data")
        interrupt = asyncio.Event()
        chunks = []
        async for chunk in self.tts.stream_speak("hello", interrupt):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0] == b"audio_data"

    @pytest.mark.asyncio
    async def test_stream_speak_respects_interrupt(self):
        self.backend.speak = AsyncMock(return_value=b"audio_data")
        interrupt = asyncio.Event()
        interrupt.set()
        chunks = []
        async for chunk in self.tts.stream_speak("hello", interrupt):
            chunks.append(chunk)
        assert len(chunks) == 0


class TestAudioQueue:
    """Tests for AudioQueue."""

    def setup_method(self):
        self.queue = AudioQueue(buffer_size=8)

    def test_enqueue_and_cancel(self):
        loop = asyncio.new_event_loop()
        self.queue.start(loop)
        chunk = AudioChunk(data=b"\x00\x00", sample_rate=16000)
        assert self.queue.enqueue(chunk)
        self.queue.cancel()
        assert not self.queue.is_playing
        self.queue.stop()

    def test_flush(self):
        loop = asyncio.new_event_loop()
        self.queue.start(loop)
        chunk = AudioChunk(data=b"\x00\x00", sample_rate=16000)
        self.queue.enqueue(chunk)
        self.queue.flush()
        self.queue.stop()


class TestConversationManager:
    """Tests for ConversationManager."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        manager = ConversationManager(timeout=0.1)
        assert not manager.active
        manager.start()
        assert manager.active
        manager.stop()
        assert not manager.active

    @pytest.mark.asyncio
    async def test_timeout_callback(self):
        called = []
        manager = ConversationManager(timeout=0.05, on_timeout=lambda: called.append(True))
        manager.start()
        await asyncio.sleep(0.2)
        assert called == [True]

    @pytest.mark.asyncio
    async def test_touch_resets_timer(self):
        manager = ConversationManager(timeout=0.1)
        manager.start()
        await asyncio.sleep(0.05)
        manager.touch()
        await asyncio.sleep(0.08)
        assert manager.active


class TestVoiceEvents:
    """Tests for voice event emission."""

    def setup_method(self):
        reset_event_bus()

    def test_emit_stt_final(self):
        bus = get_event_bus()
        bus.clear_history()
        emit_stt_final(text="hello")
        events = bus.history(EventType.VOICE_TRANSCRIPT)
        assert len(events) == 1
        assert events[0].data["text"] == "hello"
        assert events[0].data["partial"] is False

    def test_emit_stt_partial(self):
        bus = get_event_bus()
        bus.clear_history()
        emit_stt_partial(text="he")
        events = bus.history(EventType.VOICE_TRANSCRIPT)
        assert len(events) == 1
        assert events[0].data["partial"] is True

    def test_emit_voice_interrupted(self):
        bus = get_event_bus()
        bus.clear_history()
        emit_voice_interrupted(reason="user_speech")
        events = bus.history(EventType.VOICE_INTERRUPT)
        assert len(events) == 1
        assert events[0].data["reason"] == "user_speech"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
