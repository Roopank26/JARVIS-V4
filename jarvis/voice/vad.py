"""
Voice Activity Detection (VAD) for JARVIS.

Supports:
1. Silero VAD (preferred) - requires torch + silero-vad
2. WebRTC VAD (fallback) - requires webrtcvad
3. Energy-based fallback - always available

Detects:
- User starts speaking
- User stops speaking
- Silence duration
- Conversation timeout
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VADResult:
    """Result of a VAD check."""

    is_speech: bool
    confidence: float = 0.0
    silence_duration: float = 0.0
    speech_duration: float = 0.0


class VAD:
    """
    Unified Voice Activity Detection interface.

    Tries backends in order: Silero -> WebRTC -> energy.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 500.0,
        silence_duration: float = 0.8,
        speech_duration: float = 0.3,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.speech_duration = speech_duration

        self._backend: str = "none"
        self._silero_model = None
        self._webrtc_vad = None
        self._initialize_backends()

        # Tracking state
        self._speech_start: float | None = None
        self._silence_start: float | None = None
        self._speech_frames = 0
        self._silence_frames = 0
        self._frame_size = int(0.032 * sample_rate)  # 32ms frames
        self._last_result = VADResult(is_speech=False)

    def _initialize_backends(self) -> None:
        # Try Silero VAD
        try:
            import torch  # noqa: F401

            try:
                from silero_vad import load_silero_vad

                self._silero_model = load_silero_vad()
                self._backend = "silero"
                logger.info("VAD backend: silero")
                return
            except Exception as e:
                logger.debug("Silero VAD unavailable: %s", e)
        except ImportError:
            pass

        # Try WebRTC VAD
        try:
            import webrtcvad

            self._webrtc_vad = webrtcvad.Vad(2)
            self._backend = "webrtc"
            logger.info("VAD backend: webrtc")
            return
        except Exception as e:
            logger.debug("WebRTC VAD unavailable: %s", e)

        # Fallback to energy-based
        self._backend = "energy"
        logger.info("VAD backend: energy")

    def reset(self) -> None:
        """Reset VAD tracking state."""
        self._speech_start = None
        self._silence_start = None
        self._speech_frames = 0
        self._silence_frames = 0

    def process_frame(self, audio_frame: bytes) -> VADResult:
        """
        Process a single audio frame and return VAD result.

        ``audio_frame`` should be 16-bit PCM mono at ``sample_rate``.
        Frame size should match ``_frame_size`` (32ms).
        """
        frame_array = np.frombuffer(audio_frame, dtype=np.int16)
        if frame_array.size == 0:
            return self._last_result

        is_speech = False
        confidence = 0.0

        if self._backend == "silero":
            is_speech, confidence = self._process_silero(frame_array)
        elif self._backend == "webrtc":
            is_speech = self._process_webrtc(audio_frame)
            confidence = 0.8 if is_speech else 0.2
        else:
            is_speech, confidence = self._process_energy(frame_array)

        now = time.time()
        if is_speech:
            if self._speech_start is None:
                self._speech_start = now
            self._silence_start = None
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            if self._silence_start is None:
                self._silence_start = now
            self._silence_frames += 1
            self._speech_frames = 0

        silence_duration = 0.0
        speech_duration = 0.0
        if self._silence_start is not None:
            silence_duration = now - self._silence_start
        if self._speech_start is not None:
            speech_duration = now - self._speech_start

        self._last_result = VADResult(
            is_speech=is_speech,
            confidence=confidence,
            silence_duration=silence_duration,
            speech_duration=speech_duration,
        )
        return self._last_result

    def _process_silero(self, frame_array: np.ndarray) -> tuple[bool, float]:
        try:
            import torch

            tensor = torch.from_numpy(frame_array).float() / 32768.0
            with torch.no_grad():
                prob = float(self._silero_model(tensor, self.sample_rate).item())
            return prob > 0.5, prob
        except Exception:
            return self._process_energy(frame_array)

    def _process_webrtc(self, audio_frame: bytes) -> bool:
        try:
            return self._webrtc_vad.is_speech(audio_frame, self.sample_rate)
        except Exception:
            energy = float(
                np.sqrt(np.mean(np.frombuffer(audio_frame, dtype=np.int16).astype(float) ** 2))
            )
            return energy > self.energy_threshold

    def _process_energy(self, frame_array: np.ndarray) -> tuple[bool, float]:
        energy = float(np.sqrt(np.mean(frame_array.astype(float) ** 2)))
        confidence = min(1.0, energy / (self.energy_threshold * 2))
        return energy > self.energy_threshold, confidence

    def speech_detected(self) -> bool:
        """Return True if speech is currently detected."""
        return self._last_result.is_speech

    def silence_exceeded(self) -> bool:
        """Return True if silence duration exceeds the configured threshold."""
        return self._last_result.silence_duration >= self.silence_duration

    def speech_sufficient(self) -> bool:
        """Return True if accumulated speech duration is sufficient."""
        return self._last_result.speech_duration >= self.speech_duration

    async def wait_for_speech(
        self,
        stream_callback,
        timeout: float = 10.0,
    ) -> VADResult | None:
        """
        Wait for speech to start in an audio stream.

        ``stream_callback`` should be a callable that returns audio chunks
        (bytes) and raises ``StopIteration`` or returns ``None`` when done.
        """
        loop = asyncio.get_event_loop()
        start = loop.time()

        while True:
            remaining = timeout - (loop.time() - start)
            if remaining <= 0:
                return None

            try:
                chunk = await asyncio.wait_for(
                    asyncio.to_thread(stream_callback),
                    timeout=min(remaining, 0.5),
                )
            except TimeoutError:
                continue
            except StopIteration:
                return None

            if chunk is None:
                return None

            result = self.process_frame(chunk)
            if result.is_speech and result.speech_duration >= self.speech_duration:
                return result
