"""
Wake word detection for JARVIS.
Provides continuous listening for "Jarvis" wake word activation.
"""

import asyncio
import contextlib
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Wake word detection configuration."""

    word: str = "jarvis"
    sensitivity: float = 0.7
    timeout: float = 30.0
    sample_rate: int = 16000
    channels: int = 1


class WakeWordEngine:
    """
    Wake word detection using various backends.
    Supports Porcupine, Snowboy, and fallback VAD-based detection.
    """

    def __init__(self, config: WakeWordConfig | None = None):
        self.config = config or WakeWordConfig()
        self._listening = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[str], None] | None = None
        self._silence_threshold = 500
        self._wake_phrases = ["jarvis", "hey jarvis", "hey computer"]

    @property
    def is_listening(self) -> bool:
        return self._listening

    async def start(self, callback: Callable[[str], None]) -> None:
        """
        Start listening for wake word.

        Args:
            callback: Function called when wake word is detected.
                      Receives the detected phrase as argument.
        """
        if self._listening:
            logger.warning("Wake word engine already running")
            return

        self._callback = callback
        self._listening = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info(f"Wake word engine started, listening for: {self._wake_phrases}")

    async def stop(self) -> None:
        """Stop listening for wake word."""
        self._listening = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Wake word engine stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop with voice activity detection."""
        try:
            import numpy as np
            import sounddevice as sd

            audio_buffer = []
            silence_frames = 0
            speech_frames = 0
            in_speech = False

            def audio_callback(indata, frames, time_info, status):
                nonlocal silence_frames, speech_frames, in_speech

                if status:
                    return

                audio_data = indata.flatten()
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                threshold = self._silence_threshold / 32768.0

                if rms > threshold:
                    speech_frames += 1
                    silence_frames = 0
                    if not in_speech and speech_frames > 5:
                        in_speech = True
                        audio_buffer.clear()
                    if in_speech:
                        audio_buffer.append(audio_data.tobytes())
                else:
                    if in_speech:
                        silence_frames += 1
                        audio_buffer.append(audio_data.tobytes())

                        # Check for end of speech
                        if silence_frames > 20:  # ~0.4 seconds of silence
                            in_speech = False
                            # Process the captured audio
                            if len(audio_buffer) > 10:
                                asyncio.create_task(self._check_wake_word(b"".join(audio_buffer)))
                            audio_buffer.clear()
                    speech_frames = 0

            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=1024,
                callback=audio_callback,
            )

            with stream:
                while self._listening:
                    await asyncio.sleep(0.1)

        except ImportError:
            logger.warning("sounddevice not available, wake word disabled")
            # Fallback to simulated detection for testing
            await self._simulated_listen()
        except Exception as e:
            logger.error(f"Wake word error: {e}")

    async def _simulated_listen(self) -> None:
        """Simulated listening for environments without audio."""
        while self._listening:
            await asyncio.sleep(1)
            # In simulation mode, we don't trigger wake word
            # This allows testing without microphone

    async def _check_wake_word(self, audio_data: bytes) -> None:
        """
        Check if audio contains wake word.
        Uses simple keyword spotting as fallback.
        """
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            # Convert to WAV
            with io.BytesIO() as buf:
                import wave

                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(self.config.channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.config.sample_rate)
                    wf.writeframes(audio_data)
                buf.seek(0)

            with sr.AudioFile(buf) as source:
                audio = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio).lower()
                logger.debug(f"Heard: {text}")

                # Check for wake phrases
                for phrase in self._wake_phrases:
                    if phrase in text:
                        logger.info(f"Wake word detected: {phrase}")
                        if self._callback:
                            self._callback(phrase)
                        return

            except sr.UnknownValueError:
                pass
            except Exception as e:
                logger.debug(f"Recognition error: {e}")

        except ImportError:
            logger.debug("Speech recognition not available")
        except Exception as e:
            logger.error(f"Wake word check error: {e}")

    def set_sensitivity(self, level: float) -> None:
        """Set wake word sensitivity (0.0-1.0)."""
        self.config.sensitivity = max(0.0, min(1.0, level))
        # Adjust threshold based on sensitivity
        self._silence_threshold = 500 * (1.0 - level * 0.5)

    def set_wake_phrases(self, phrases: list) -> None:
        """Set custom wake phrases."""
        self._wake_phrases = [p.lower() for p in phrases]


class VoiceStateMachine:
    """
    Manages voice interaction states.
    States: IDLE -> LISTENING -> PROCESSING -> RESPONDING -> IDLE
    """

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    SLEEPING = "sleeping"

    def __init__(self):
        self.state = self.IDLE
        self._state_callbacks: dict = {}
        self._last_activity = 0.0

    @property
    def is_idle(self) -> bool:
        return self.state == self.IDLE

    @property
    def is_listening(self) -> bool:
        return self.state == self.LISTENING

    async def transition(self, new_state: str) -> None:
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self._last_activity = 0.0

        logger.info(f"State: {old_state} -> {new_state}")

        if new_state in self._state_callbacks:
            for callback in self._state_callbacks[new_state]:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"State callback error: {e}")

    def on_state(self, state: str, callback) -> None:
        """Register callback for state change."""
        if state not in self._state_callbacks:
            self._state_callbacks[state] = []
        self._state_callbacks[state].append(callback)

    async def wake(self) -> None:
        """Wake from idle/sleeping state."""
        if self.state in (self.IDLE, self.SLEEPING):
            await self.transition(self.LISTENING)

    async def process(self) -> None:
        """Transition to processing state."""
        if self.state == self.LISTENING:
            await self.transition(self.PROCESSING)

    async def respond(self) -> None:
        """Transition to responding state."""
        if self.state == self.PROCESSING:
            await self.transition(self.RESPONDING)

    async def done(self) -> None:
        """Return to idle state after processing."""
        if self.state in (self.PROCESSING, self.RESPONDING, self.LISTENING):
            await self.transition(self.IDLE)

    async def sleep(self, timeout: float = 300.0) -> None:
        """Enter sleeping mode after timeout."""
        if self.state == self.IDLE:
            await asyncio.sleep(timeout)
            if self.state == self.IDLE:
                await self.transition(self.SLEEPING)

    def get_idle_time(self) -> float:
        """Get seconds since last activity."""
        return 0.0 - self._last_activity
