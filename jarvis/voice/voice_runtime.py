"""
Real Voice Runtime for JARVIS — Enhanced Edition.

Extends the existing voice pipeline with:
- Interrupt Manager (thread-safe, async-safe)
- Speech State Machine (event-driven transitions)
- Voice Activity Detection (Silero / WebRTC / energy fallback)
- Streaming Speech Recognition (partial transcription)
- Streaming TTS (chunked audio generation)
- Audio Playback Queue (non-blocking, cancellable)
- Conversation Manager (auto timeout, push-to-talk)

Backward compatible: existing VoiceConfig, VoiceInitResult, and public
APIs remain unchanged.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import subprocess
import wave
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from jarvis.voice.audio_queue import AudioChunk, AudioQueue
from jarvis.voice.conversation_manager import ConversationManager
from jarvis.voice.interrupt_manager import InterruptManager
from jarvis.voice.speech_state import SpeechState, SpeechStateMachine
from jarvis.voice.streaming_stt import StreamingSTT
from jarvis.voice.streaming_tts import StreamingTTS
from jarvis.voice.vad import VAD
from jarvis.voice.voice_events import (
    emit_conversation_timeout,
    emit_playback_finished,
    emit_playback_started,
    emit_tts_chunk,
    emit_tts_finished,
    emit_tts_started,
    emit_voice_interrupted,
    emit_voice_started,
    emit_voice_stopped,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy types (preserved for backward compatibility)
# ---------------------------------------------------------------------------

class VoiceComponentStatus(Enum):
    """Status of voice components."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ComponentInitResult:
    """Result of component initialization."""
    success: bool
    status: VoiceComponentStatus
    message: str = ""
    error: str | None = None

    @classmethod
    def ok(cls, status: VoiceComponentStatus = VoiceComponentStatus.READY, message: str = "") -> ComponentInitResult:
        return cls(success=True, status=status, message=message)

    @classmethod
    def fail(cls, error: str, status: VoiceComponentStatus = VoiceComponentStatus.ERROR) -> ComponentInitResult:
        return cls(success=False, status=status, message="", error=error)


@dataclass
class VoiceInitResult:
    """Result of voice runtime initialization."""
    wake_word: ComponentInitResult
    stt: ComponentInitResult
    tts: ComponentInitResult
    ready: bool = False

    @classmethod
    def from_components(cls, wake_word, stt, tts) -> VoiceInitResult:
        results = cls(
            wake_word=ComponentInitResult.ok() if (wake_word and wake_word.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
            stt=ComponentInitResult.ok() if (stt and stt.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
            tts=ComponentInitResult.ok() if (tts and tts.status == VoiceComponentStatus.READY) else ComponentInitResult.fail("Not initialized"),
        )
        results.ready = all([results.wake_word.success, results.stt.success, results.tts.success])
        return results

    def to_dict(self) -> dict[str, Any]:
        return {
            "wake_word": {"status": self.wake_word.status.value, "success": self.wake_word.success, "error": self.wake_word.error},
            "stt": {"status": self.stt.status.value, "success": self.stt.success, "error": self.stt.error},
            "tts": {"status": self.tts.status.value, "success": self.tts.success, "error": self.tts.error},
            "ready": self.ready
        }


@dataclass
class VoiceConfig:
    """Voice configuration (extended with new options)."""
    # STT settings
    stt_model: str = "base"
    stt_language: str = "en"
    stt_device: str = "auto"

    # TTS settings
    tts_model: str = "en_US-lessac-medium"
    tts_voice: str = "en_US-lessac-medium.onnx"
    tts_speaker: int = 0

    # Wake word settings
    wake_word: str = "jarvis"
    wake_word_threshold: float = 0.5
    wake_word_model: str = "jarvis-onnx"

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1

    # Runtime settings
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    phrase_threshold: float = 0.3
    non_speech_threshold: float = 0.2

    # New conversation options
    continuous_listening: bool = True
    conversation_timeout: float = 10.0
    push_to_talk: bool = False
    push_to_talk_key: str = "space"
    vad_engine: str = "silero"
    streaming: bool = True
    interrupt_enabled: bool = True
    audio_chunk_ms: int = 200
    tts_chunk_size: str = "auto"

    @classmethod
    def from_file(cls, path: str) -> VoiceConfig:
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        return cls()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VoiceComponent:
    """Base class for voice components."""

    def __init__(self, name: str):
        self.name = name
        self.status = VoiceComponentStatus.NOT_INITIALIZED
        self.error_message: str | None = None
        self._instance = None

    async def initialize(self) -> ComponentInitResult:
        self.status = VoiceComponentStatus.INITIALIZING
        raise NotImplementedError("Subclasses must implement initialize()")

    async def shutdown(self) -> None:
        self._instance = None
        self.status = VoiceComponentStatus.NOT_INITIALIZED


# ---------------------------------------------------------------------------
# Backend components (preserved from legacy implementation)
# ---------------------------------------------------------------------------

class FasterWhisperSTT(VoiceComponent):
    """Speech-to-Text using faster-whisper."""

    def __init__(self, config: VoiceConfig):
        super().__init__("STT")
        self.config = config
        self._instance = None
        self._model = None

    async def initialize(self) -> ComponentInitResult:
        self.status = VoiceComponentStatus.INITIALIZING
        try:
            from faster_whisper import WhisperModel
            compute_type = "int8"
            if self.config.stt_device == "cuda":
                try:
                    import torch
                    if torch.cuda.is_available():
                        compute_type = "float16"
                except ImportError:
                    pass
            logger.info("Loading faster-whisper %s...", self.config.stt_model)
            self._model = WhisperModel(
                self.config.stt_model,
                device=self.config.stt_device,
                compute_type=compute_type
            )
            self.status = VoiceComponentStatus.READY
            logger.info("STT initialized successfully")
            return ComponentInitResult.ok(
                status=VoiceComponentStatus.READY,
                message=f"Model '{self.config.stt_model}' loaded"
            )
        except ImportError as e:
            self.status = VoiceComponentStatus.DISABLED
            self.error_message = f"faster-whisper not installed: {e}"
            logger.warning("STT disabled: %s", e)
            return ComponentInitResult.fail(str(e), status=VoiceComponentStatus.DISABLED)
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.error("STT initialization failed: %s", e)
            return ComponentInitResult.fail(str(e))

    async def transcribe(self, audio_path: str) -> str | None:
        if self.status != VoiceComponentStatus.READY or not self._model:
            return None
        try:
            segments, _ = self._model.transcribe(
                audio_path,
                language=self.config.stt_language,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            text = " ".join([seg.text for seg in segments])
            return text.strip() if text else None
        except Exception as e:
            logger.error("Transcription error: %s", e)
            return None

    async def transcribe_bytes(self, audio_data: bytes) -> str | None:
        import tempfile
        fd = None
        path = None
        try:
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(audio_data)
            wav_buffer.seek(0)
            wav_bytes = wav_buffer.read()
            fd, path = tempfile.mkstemp(suffix='.wav')
            with os.fdopen(fd, 'wb') as f:
                f.write(wav_bytes)
                f.flush()
                fd = -1
            if not os.path.exists(path) or os.path.getsize(path) <= 44:
                return None
            return await self.transcribe(path)
        except Exception as e:
            logger.debug("Transcription error: %s", e)
            return None
        finally:
            if fd is not None and fd >= 0:
                try:
                    os.close(fd)
                except Exception:
                    pass
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception:
                    pass


class SpeechRecognitionSTT(VoiceComponent):
    """Speech-to-Text fallback using SpeechRecognition + PyAudio."""

    def __init__(self, config: VoiceConfig):
        super().__init__("STT")
        self.config = config

    async def initialize(self) -> ComponentInitResult:
        self.status = VoiceComponentStatus.INITIALIZING
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self.status = VoiceComponentStatus.READY
            return ComponentInitResult.ok(status=VoiceComponentStatus.READY, message="SpeechRecognition fallback ready")
        except ImportError as e:
            self.status = VoiceComponentStatus.DISABLED
            return ComponentInitResult.fail(str(e), status=VoiceComponentStatus.DISABLED)
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            return ComponentInitResult.fail(str(e))

    async def listen(self, timeout: float = 10.0) -> str | None:
        if self.status != VoiceComponentStatus.READY:
            return None
        try:
            import pyaudio
            import speech_recognition as sr
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=1024,
            )
            stream.start_stream()
            frames = []
            start = asyncio.get_event_loop().time()
            while True:
                if asyncio.get_event_loop().time() - start > timeout:
                    break
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    frames.append(data)
                except Exception:
                    break
            stream.stop_stream()
            stream.close()
            audio.terminate()
            if not frames:
                return None
            wav_data = self._to_wav(b"".join(frames))
            source = sr.AudioFile(wav_data)
            with source as src:
                audio_data = self._recognizer.record(src)
            return self._recognizer.recognize_google(audio_data)
        except Exception:
            return None

    def _to_wav(self, raw: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(raw)
        buffer.seek(0)
        return buffer.read()

    async def transcribe(self, audio_path: str) -> str | None:
        try:
            import speech_recognition as sr
            with sr.AudioFile(audio_path) as source:
                audio = self._recognizer.record(source)
            return self._recognizer.recognize_google(audio)
        except Exception:
            return None


class PiperTTS(VoiceComponent):
    """Text-to-Speech using Piper."""

    def __init__(self, config: VoiceConfig):
        super().__init__("TTS")
        self.config = config
        self._session = None
        self._command_mode = False
        self._available = False

    async def initialize(self) -> ComponentInitResult:
        self.status = VoiceComponentStatus.INITIALIZING
        try:
            import grpc
            import piper_pb2
            import piper_pb2_grpc
            server = os.environ.get("PIPPER_SERVER", "localhost:50000")
            self._channel = grpc.aio.insecure_channel(server)
            self._session = piper_pb2_grpc.PiperSessionStub(self._channel)
            await asyncio.wait_for(
                self._session.IsReady(piper_pb2.Void()),
                timeout=5.0
            )
            self._available = True
            self.status = VoiceComponentStatus.READY
            logger.info("TTS initialized successfully")
            return ComponentInitResult.ok(status=VoiceComponentStatus.READY, message="Connected to Piper TTS server")
        except ImportError:
            self._available = False
            self.status = VoiceComponentStatus.ERROR
            logger.debug("Piper not installed, will use fallback TTS")
            return ComponentInitResult.fail("piper not installed", status=VoiceComponentStatus.ERROR)
        except Exception as e:
            self._available = False
            self.status = VoiceComponentStatus.ERROR
            logger.debug("Piper initialization failed: %s", e)
            return ComponentInitResult.fail(str(e))

    async def speak(self, text: str) -> bytes | None:
        if self.status != VoiceComponentStatus.READY or not self._available:
            return None
        try:
            if self._command_mode:
                return await self._speak_command(text)
            import piper_pb2
            request = piper_pb2.SynthesisRequest(
                text=text,
                speaker_id=self.config.tts_speaker
            )
            audio_chunks = []
            async for resp in self._session.Synthesize(request):
                if resp.audio.HasField('audio'):
                    audio_chunks.append(resp.audio.audio)
            return b''.join(audio_chunks) if audio_chunks else None
        except Exception as e:
            logger.debug("Piper TTS error: %s", e)
            return None

    async def _speak_command(self, text: str) -> bytes | None:
        try:
            result = subprocess.run(
                ["piper", "--model", self.config.tts_model, "--output-raw"],
                input=text.encode(),
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    async def speak_to_file(self, text: str, output_path: str) -> bool:
        audio = await self.speak(text)
        if audio:
            with open(output_path, 'wb') as f:
                f.write(audio)
            return True
        return False

    async def shutdown(self) -> None:
        if hasattr(self, '_channel'):
            await self._channel.close()
        await super().shutdown()


class OpenWakeWord(VoiceComponent):
    """Wake word detection using OpenWakeWord."""

    def __init__(self, config: VoiceConfig):
        super().__init__("Wake Word")
        self.config = config
        self._predictor = None
        self._running = False

    async def initialize(self) -> ComponentInitResult:
        self.status = VoiceComponentStatus.INITIALIZING
        try:
            try:
                from openwakeword import WakeWordClassifier
                self._framework = "openwakeword"
                logger.info("Using OpenWakeWord framework")
            except ImportError:
                self._framework = "vad"
                logger.info("Using VAD-based wake word detection")
                self.status = VoiceComponentStatus.READY
                return ComponentInitResult.ok(status=VoiceComponentStatus.READY, message="Using VAD-based wake word detection")
            self._predictor = WakeWordClassifier(verbose=False, inference_framework="onnx")
            model_path = Path("models") / f"{self.config.wake_word_model}.onnx"
            if model_path.exists():
                self._predictor.add_model(str(model_path))
            else:
                self._predictor.add_model("jarvis")
            self.status = VoiceComponentStatus.READY
            logger.info("Wake word detection initialized")
            return ComponentInitResult.ok(status=VoiceComponentStatus.READY, message=f"Wake word '{self.config.wake_word}' ready")
        except ImportError:
            self.status = VoiceComponentStatus.DISABLED
            self.error_message = "openwakeword not installed"
            logger.warning("Wake word disabled (use 'pip install openwakeword')")
            return ComponentInitResult.fail("openwakeword not installed", status=VoiceComponentStatus.DISABLED)
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.error("Wake word initialization failed: %s", e)
            return ComponentInitResult.fail(str(e))

    async def detect(self, audio_chunk: bytes) -> bool:
        if self.status != VoiceComponentStatus.READY:
            return False
        if self._framework == "vad":
            return await self._detect_vad(audio_chunk)
        try:
            import numpy as np
            audio = np.frombuffer(audio_chunk, dtype=np.int16)
            predictions = self._predictor.predict(audio)
            for model_name, score in predictions.items():
                if score > self.config.wake_word_threshold:
                    logger.info("Wake word detected: %s (%.2f)", model_name, score)
                    return True
            return False
        except Exception as e:
            logger.error("Wake word detection error: %s", e)
            return False

    async def _detect_vad(self, audio_chunk: bytes) -> bool:
        import numpy as np
        audio = np.frombuffer(audio_chunk, dtype=np.int16)
        energy = np.sqrt(np.mean(audio.astype(float) ** 2))
        return energy > 1000

    async def shutdown(self) -> None:
        self._running = False
        await super().shutdown()


# ---------------------------------------------------------------------------
# Enhanced VoiceRuntime
# ---------------------------------------------------------------------------

class VoiceRuntime:
    """
    Complete enhanced voice runtime for JARVIS.

    Pipeline (enhanced):
    Wake Word → VAD → Streaming STT → Agent → Streaming TTS → Audio Queue
    """

    def __init__(self, config: VoiceConfig | None = None):
        self.config = config or VoiceConfig()

        # Legacy components
        self.wake_word: OpenWakeWord | None = None
        self.stt: FasterWhisperSTT | None = None
        self.tts: PiperTTS | None = None
        self._fallback_tts = None
        self._tts_backups: list[tuple] = []

        # Enhanced components
        self._interrupt_manager = InterruptManager()
        self._state_machine = SpeechStateMachine()
        self._vad = VAD(
            sample_rate=self.config.sample_rate,
            energy_threshold=self.config.energy_threshold,
            silence_duration=self.config.pause_threshold,
        )
        self._streaming_stt: StreamingSTT | None = None
        self._streaming_tts: StreamingTTS | None = None
        self._audio_queue = AudioQueue()
        self._conversation_manager = ConversationManager(
            timeout=self.config.conversation_timeout,
            on_timeout=self._on_conversation_timeout,
        )

        # Runtime state
        self._running = False
        self._listen_task: asyncio.Task | None = None
        self._pipeline_lock = asyncio.Lock()

        # Input device selection and caching
        self._input_device: int | None = None
        self._input_device_error_count: int = 0
        self._last_input_device_error: str | None = None

        # Push-to-talk state
        self._push_to_talk_active = False
        self._keyboard_listener_task: asyncio.Task | None = None

        # Callbacks
        self.on_wake_word: Callable | None = None
        self.on_transcription: Callable[[str], None] | None = None
        self.on_response: Callable[[str], None] | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> VoiceInitResult:
        """Initialize all voice components."""
        # Legacy components
        self.wake_word = OpenWakeWord(self.config)
        wake_result = await self.wake_word.initialize()

        self.stt = FasterWhisperSTT(self.config)
        stt_result = await self.stt.initialize()
        if not stt_result.success:
            try:
                fallback = SpeechRecognitionSTT(self.config)
                fallback_result = await fallback.initialize()
                if fallback_result.success:
                    self.stt = fallback
                    stt_result = fallback_result
                    logger.info("STT initialized with SpeechRecognition fallback")
            except Exception as e:
                logger.warning("Fallback STT failed: %s", e)

        self.tts = PiperTTS(self.config)
        tts_result = await self.tts.initialize()
        if not tts_result.success:
            self._fallback_tts = None
            self._tts_backups = []
            try:
                import pyttsx3
                tts = pyttsx3.init()
                tts.setProperty('rate', 150)
                tts.setProperty('volume', 1.0)
                self._tts_backups.append(("pyttsx3", tts))
                logger.info("TTS fallback: pyttsx3 available")
            except Exception:
                pass
            try:
                from jarvis.voice.audio import AudioConfig, TextToSpeech
                gtts = TextToSpeech(AudioConfig(
                    sample_rate=self.config.sample_rate,
                    channels=self.config.channels,
                ))
                self._tts_backups.append(("gtts", gtts))
                logger.info("TTS fallback: gTTS available")
            except Exception:
                pass
            if self._tts_backups:
                tts_result = ComponentInitResult.ok(
                    status=VoiceComponentStatus.READY,
                    message=f"Using fallback TTS ({self._tts_backups[0][0]})"
                )
                self.tts.status = VoiceComponentStatus.READY
                logger.info("TTS initialized with fallback backend: %s", self._tts_backups[0][0])
            else:
                logger.warning("No TTS backend available")

        # Initialize enhanced components
        self._streaming_stt = StreamingSTT(self.stt, self.config.sample_rate, self.config.channels)
        self._streaming_tts = StreamingTTS(self.tts if self.tts.status == VoiceComponentStatus.READY else None)

        # Start audio queue if loop is available
        try:
            loop = asyncio.get_event_loop()
            self._audio_queue.start(loop)
        except RuntimeError:
            pass

        result = VoiceInitResult(
            wake_word=wake_result,
            stt=stt_result,
            tts=tts_result,
            ready=wake_result.success and stt_result.success and tts_result.success
        )
        return result

    async def shutdown(self) -> None:
        """Shutdown all voice components."""
        self._running = False
        self.stop_push_to_talk()
        self._conversation_manager.stop()
        self._audio_queue.stop()

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self.wake_word:
            await self.wake_word.shutdown()
        if self.stt:
            await self.stt.shutdown()
        if self.tts:
            await self.tts.shutdown()

    # ------------------------------------------------------------------
    # Interrupt management
    # ------------------------------------------------------------------

    def interrupt(self) -> None:
        """Trigger interrupt: stop speaking, cancel queued audio, clear STT."""
        self._interrupt_manager.interrupt()
        self._audio_queue.cancel()
        self._state_machine.transition(SpeechState.INTERRUPTED)
        emit_voice_interrupted(reason="user_speech")
        logger.info("Voice interrupted")

    def clear_interrupt(self) -> None:
        """Clear interrupt state."""
        self._interrupt_manager.clear()

    # ------------------------------------------------------------------
    # Speech state machine
    # ------------------------------------------------------------------

    @property
    def speech_state(self) -> SpeechState:
        return self._state_machine.state

    # ------------------------------------------------------------------
    # Input device selection
    # ------------------------------------------------------------------

    def _select_input_device(self) -> int | None:
        import sounddevice as sd
        if self._input_device is not None:
            try:
                dev = sd.query_devices(self._input_device)
                if dev["max_input_channels"] > 0:
                    return self._input_device
            except Exception:
                self._input_device = None
        try:
            devices = sd.query_devices()
        except Exception as e:
            if self._last_input_device_error != str(e):
                self._last_input_device_error = str(e)
                logger.error("Error querying audio devices: %s", e)
            return None
        candidates = [i for i, dev in enumerate(devices) if dev["max_input_channels"] > 0]
        if not candidates:
            if self._last_input_device_error != "no_input_devices":
                self._last_input_device_error = "no_input_devices"
                logger.error("No usable microphone found.")
            return None
        for idx in candidates:
            try:
                stream = sd.InputStream(device=idx, channels=1, samplerate=16000, blocksize=1024)
                stream.start()
                stream.stop()
                stream.close()
                self._input_device = idx
                self._last_input_device_error = None
                logger.info("Selected input device: %s", idx)
                return idx
            except Exception:
                continue
        if self._last_input_device_error != "no_working_device":
            self._last_input_device_error = "no_working_device"
            logger.error("No usable microphone found.")
        return None

    # ------------------------------------------------------------------
    # Listening (enhanced with VAD + streaming STT)
    # ------------------------------------------------------------------

    async def listen_once(self, timeout: float = 10.0) -> str | None:
        """Listen for one voice command and return transcription."""
        if not self.stt or self.stt.status != VoiceComponentStatus.READY:
            logger.debug("listen_once: STT not ready")
            return None
        device = self._select_input_device()
        if device is None:
            logger.debug("listen_once: no usable input device")
            return None

        self._state_machine.transition(SpeechState.LISTENING)
        emit_voice_started()

        try:
            import threading

            import sounddevice as sd

            logger.info("Recording started")
            audio_data = []
            stop_event = threading.Event()

            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning("Audio status: %s", status)
                audio = indata.flatten()
                audio_data.append(audio.tobytes())
                vad_result = self._vad.process_frame(audio.tobytes())
                if vad_result.speech_sufficient() and vad_result.silence_exceeded():
                    stop_event.set()
                elif vad_result.is_speech:
                    pass  # Continue accumulating speech

            stream = sd.InputStream(
                device=device,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=1024,
                callback=callback
            )
            with stream:
                await asyncio.wait_for(
                    asyncio.to_thread(stop_event.wait),
                    timeout=timeout
                )
            logger.info("Recording finished")

        except TimeoutError:
            logger.debug("Listen timeout")
            self._state_machine.transition(SpeechState.IDLE)
            emit_voice_stopped()
            return None
        except Exception as e:
            logger.error("Listen error: %s", e)
            self._state_machine.transition(SpeechState.IDLE)
            emit_voice_stopped()
            return None

        self._state_machine.transition(SpeechState.TRANSCRIBING)

        if audio_data:
            audio_bytes = b''.join(audio_data)
            logger.debug("Starting transcription (%s bytes)", len(audio_bytes))
            text = await self.stt.transcribe_bytes(audio_bytes)
            logger.debug("Transcription finished: %s", text)
            self._state_machine.transition(SpeechState.IDLE)
            emit_voice_stopped()
            return text

        self._state_machine.transition(SpeechState.IDLE)
        emit_voice_stopped()
        return None

    # ------------------------------------------------------------------
    # Speaking (enhanced with streaming TTS + audio queue)
    # ------------------------------------------------------------------

    async def speak(self, text: str) -> bool:
        """Speak text using TTS with interruptible streaming."""
        if not text:
            return False

        self._interrupt_manager.clear()
        self._state_machine.transition(SpeechState.STREAMING)
        emit_tts_started()

        played = False

        # Try streaming via primary TTS backend
        if self.tts and self.tts.status == VoiceComponentStatus.READY:
            stream = StreamingTTS(self.tts)
            async for chunk in stream.stream_speak(text, self._interrupt_manager._async_event):
                if self._interrupt_manager.is_interrupted():
                    break
                audio_chunk = AudioChunk(
                    data=chunk,
                    sample_rate=self.config.sample_rate,
                    channels=self.config.channels,
                )
                self._audio_queue.enqueue(audio_chunk)
                emit_tts_chunk(stream.chunk_index)
                played = True

        # Fallback backends
        if not played and self._tts_backups:
            for name, backend in self._tts_backups:
                if name == "pyttsx3":
                    try:
                        backend.say(text)
                        backend.runAndWait()
                        played = True
                        break
                    except Exception as e:
                        logger.debug("pyttsx3 TTS error: %s", e)
                        continue
                if name == "gtts":
                    try:
                        audio = await backend.speak(text, blocking=False)
                        if audio:
                            import numpy as np
                            import sounddevice as sd
                            buffer = io.BytesIO(audio)
                            with wave.open(buffer, 'rb') as wf:
                                frames = wf.readframes(wf.getnframes())
                                audio_array = np.frombuffer(frames, dtype='int16')
                            sd.play(audio_array, self.config.sample_rate)
                            sd.wait()
                            played = True
                            break
                    except Exception as e:
                        logger.debug("gTTS error: %s", e)
                        continue

        emit_tts_finished()
        self._state_machine.transition(SpeechState.SPEAKING)
        emit_playback_started()
        self._state_machine.transition(SpeechState.RESPONDING)

        if self.config.continuous_listening and not self._interrupt_manager.is_interrupted():
            self._conversation_manager.start()
            self._state_machine.transition(SpeechState.LISTENING)
        else:
            self._state_machine.transition(SpeechState.IDLE)

        emit_playback_finished()
        emit_voice_stopped()
        return played or False

    # ------------------------------------------------------------------
    # Wake-word loop (enhanced)
    # ------------------------------------------------------------------

    async def start_wake_word_listening(self, agent=None) -> None:
        """Start continuous wake-word listening in background."""
        if self._running:
            return
        self._running = True
        self._state_machine.transition(SpeechState.WAKE_LISTENING)
        self._listen_task = asyncio.create_task(self._wake_word_loop(agent))
        logger.info("Wake-word listening started")

    async def stop_wake_word_listening(self) -> None:
        """Stop continuous wake-word listening."""
        self._running = False
        self._conversation_manager.stop()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        self._state_machine.transition(SpeechState.IDLE)
        logger.info("Wake-word listening stopped")

    async def _wake_word_loop(self, agent=None) -> None:
        """Background loop for wake-word detection."""
        retry_count = 0
        while self._running:
            try:
                async with self._pipeline_lock:
                    text = await self._listen_for_wake_word()
                    if not text:
                        retry_count += 1
                        backoff = min(5, 1 if retry_count == 1 else 2 if retry_count == 2 else 5)
                        await asyncio.sleep(backoff)
                        continue
                    retry_count = 0
                    logger.info("Wake word detected: %s", text)

                    if self.on_wake_word:
                        self.on_wake_word(text)

                    command = await self.listen_once(timeout=10.0)
                    if command:
                        logger.info("Command: %s", command)
                        if self.on_transcription:
                            self.on_transcription(command)
                        if agent:
                            response = await agent.process(command)
                            if self.on_response:
                                self.on_response(response)
                            await self.speak(response)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Wake-word loop error: %s", e)
                await asyncio.sleep(1)

    async def _listen_for_wake_word(self, timeout: float = 3.0) -> str | None:
        """Listen for wake word phrase."""
        if not self.stt or self.stt.status != VoiceComponentStatus.READY:
            return None
        device = self._select_input_device()
        if device is None:
            return None
        try:
            import threading

            import numpy as np
            import sounddevice as sd

            audio_data = []
            speaking = False
            silence_frames = 0
            max_frames = int(timeout * self.config.sample_rate / 1024)
            frame_count = 0
            stop_event = threading.Event()

            def callback(indata, frames, time_info, status):
                nonlocal speaking, silence_frames, frame_count
                if status:
                    logger.warning("Audio status: %s", status)
                audio = indata.flatten()
                audio_data.append(audio.tobytes())
                frame_count += 1
                energy = np.sqrt(np.mean(audio.astype(float) ** 2))
                if energy > 500:
                    speaking = True
                    silence_frames = 0
                elif speaking:
                    silence_frames += 1
                    if silence_frames > 30:
                        stop_event.set()
                if frame_count > max_frames:
                    stop_event.set()

            stream = sd.InputStream(
                device=device,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=1024,
                callback=callback
            )
            with stream:
                await asyncio.wait_for(
                    asyncio.to_thread(stop_event.wait),
                    timeout=timeout
                )
        except TimeoutError:
            pass
        except Exception as e:
            logger.error("Wake-word listen error: %s", e)
            return None

        if audio_data:
            audio_bytes = b''.join(audio_data)
            text = await self.stt.transcribe_bytes(audio_bytes)
            if text:
                text_lower = text.lower().strip()
                wake_words = ["hey jarvis", "jarvis", "hello jarvis"]
                if any(text_lower.startswith(w) for w in wake_words):
                    return text
        return None

    # ------------------------------------------------------------------
    # Push-to-talk
    # ------------------------------------------------------------------

    async def start_push_to_talk(self) -> None:
        """Enable push-to-talk mode."""
        if self._keyboard_listener_task is not None:
            return
        self._push_to_talk_active = True
        self._state_machine.transition(SpeechState.LISTENING)
        self._keyboard_listener_task = asyncio.create_task(self._push_to_talk_loop())
        logger.info("Push-to-talk enabled")

    async def stop_push_to_talk(self) -> None:
        """Disable push-to-talk mode."""
        self._push_to_talk_active = False
        if self._keyboard_listener_task is not None:
            self._keyboard_listener_task.cancel()
            try:
                await self._keyboard_listener_task
            except asyncio.CancelledError:
                pass
            self._keyboard_listener_task = None
        self._state_machine.transition(SpeechState.IDLE)
        logger.info("Push-to-talk disabled")

    async def _push_to_talk_loop(self) -> None:
        """Listen while push-to-talk key is held."""
        try:
            import keyboard
        except ImportError:
            logger.warning("keyboard module not available; push-to-talk disabled")
            return

        key = self.config.push_to_talk_key
        try:
            while self._push_to_talk_active:
                if keyboard.is_pressed(key):
                    self._state_machine.transition(SpeechState.LISTENING)
                    text = await self.listen_once(timeout=30.0)
                    if text and self.on_transcription:
                        self.on_transcription(text)
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Push-to-talk error: %s", e)

    # ------------------------------------------------------------------
    # Playback helpers
    # ------------------------------------------------------------------

    async def _play_activation_sound(self) -> None:
        """Play activation sound."""
        try:
            import numpy as np
            import sounddevice as sd
            sample_rate = 16000
            duration = 0.15
            frequency = 880
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)
            tone = (tone * 0.3).astype(np.float32)
            sd.play(tone, sample_rate)
            sd.wait()
        except Exception as e:
            logger.debug("Activation sound error: %s", e)

    def _on_conversation_timeout(self) -> None:
        """Handle conversation timeout."""
        logger.debug("Conversation timeout")
        self._state_machine.transition(SpeechState.IDLE)
        emit_conversation_timeout()

    # ------------------------------------------------------------------
    # Status / diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        return {
            "wake_word": {
                "status": self.wake_word.status.value if self.wake_word else "not_initialized",
                "error": self.wake_word.error_message if self.wake_word else None
            },
            "stt": {
                "status": self.stt.status.value if self.stt else "not_initialized",
                "model": self.config.stt_model,
                "error": self.stt.error_message if self.stt else None
            },
            "tts": {
                "status": self.tts.status.value if self.tts else "not_initialized",
                "model": self.config.tts_model,
                "error": self.tts.error_message if self.tts else None
            },
            "speech_state": self._state_machine.state.value,
            "conversation_active": self._conversation_manager.active,
            "push_to_talk": self.config.push_to_talk,
            "ready": all([
                self.wake_word.status == VoiceComponentStatus.READY if self.wake_word else True,
                self.stt.status == VoiceComponentStatus.READY if self.stt else True,
                self.tts.status == VoiceComponentStatus.READY if self.tts else True,
            ])
        }

    def format_status(self) -> str:
        status = self.get_status()
        lines = ["[Voice Status]", "=" * 40]
        for component in ["wake_word", "stt", "tts"]:
            info = status[component]
            name = component.replace("_", " ").title()
            icon = "✓" if "ready" in info.get("status", "") else "✗" if "error" in info.get("status", "") else "○"
            lines.append(f"{icon} {name}: {info.get('status', 'unknown')}")
            if info.get("model"):
                lines.append(f"   Model: {info['model']}")
        lines.append(f"   State: {status.get('speech_state', 'unknown')}")
        lines.append(f"   Conversation: {'active' if status.get('conversation_active') else 'inactive'}")
        return "\n".join(lines)

    def get_wake_word_status(self) -> str:
        if not self.wake_word:
            return "Wake word: not initialized"
        status = self.wake_word.status.value
        framework = getattr(self.wake_word, '_framework', 'unknown')
        return f"Wake word: {status} ({framework})"


# ---------------------------------------------------------------------------
# Global singletons (preserved)
# ---------------------------------------------------------------------------

_voice_runtime: VoiceRuntime | None = None


def get_voice_runtime(config: VoiceConfig | None = None) -> VoiceRuntime:
    """Get or create global voice runtime."""
    global _voice_runtime
    if _voice_runtime is None:
        _voice_runtime = VoiceRuntime(config)
    return _voice_runtime


async def initialize_voice(config_path: str | None = None) -> VoiceRuntime:
    """Initialize voice runtime with config."""
    global _voice_runtime

    config = VoiceConfig()
    if config_path and Path(config_path).exists():
        config = VoiceConfig.from_file(config_path)

    _voice_runtime = VoiceRuntime(config)
    await _voice_runtime.initialize()

    return _voice_runtime
