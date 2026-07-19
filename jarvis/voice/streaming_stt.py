"""
Streaming Speech-to-Text for JARVIS.

Provides partial (streaming) transcription by accumulating audio and
periodically producing intermediate results before the final transcript.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import os
import time
import wave
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class StreamingSTT:
    """
    Streaming Speech-to-Text.

    Wraps the existing STT backends (faster-whisper, SpeechRecognition)
    and exposes an async iterator that yields partial transcriptions.
    """

    def __init__(self, stt_backend, sample_rate: int = 16000, channels: int = 1):
        self._backend = stt_backend
        self.sample_rate = sample_rate
        self.channels = channels
        self._accumulated = bytearray()
        self._transcribe_lock = asyncio.Lock()
        self._final_text: str = ""
        self._partial_text: str = ""
        self._last_partial_time = 0.0
        self._partial_interval = 0.5  # seconds between partial emissions

    def reset(self) -> None:
        """Clear accumulated audio and transcript state."""
        self._accumulated.clear()
        self._final_text = ""
        self._partial_text = ""
        self._last_partial_time = 0.0

    def add_audio(self, audio_chunk: bytes) -> None:
        """Add raw PCM audio to the accumulation buffer."""
        self._accumulated.extend(audio_chunk)

    def audio_length_seconds(self) -> float:
        if self.sample_rate <= 0 or self.channels <= 0:
            return 0.0
        return len(self._accumulated) / (self.sample_rate * self.channels * 2)

    async def stream_transcribe(
        self,
        stop_event: asyncio.Event,
        min_audio_seconds: float = 0.5,
    ) -> AsyncIterator[str]:
        """
        Yield partial transcripts as audio accumulates.

        Stops when ``stop_event`` is set.
        """
        while not stop_event.is_set():
            if self.audio_length_seconds() < min_audio_seconds:
                await asyncio.sleep(0.1)
                continue

            async with self._transcribe_lock:
                if stop_event.is_set():
                    break
                now = time.time()
                if now - self._last_partial_time < self._partial_interval:
                    await asyncio.sleep(0.05)
                    continue

                text = await self._transcribe_accumulated()
                if text:
                    self._partial_text = text
                    self._last_partial_time = now
                    yield text

        # Final transcription
        async with self._transcribe_lock:
            if self._accumulated:
                text = await self._transcribe_accumulated()
                if text:
                    self._final_text = text
                    yield text

    async def final_transcription(self) -> str | None:
        """Produce the final transcript from accumulated audio."""
        if not self._accumulated:
            return None
        async with self._transcribe_lock:
            text = await self._transcribe_accumulated()
            if text:
                self._final_text = text
            return text or None

    async def _transcribe_accumulated(self) -> str:
        """Transcribe the current accumulation buffer."""
        if not self._accumulated:
            return ""

        try:
            wav_bytes = self._encode_wav(bytes(self._accumulated))
            if hasattr(self._backend, "transcribe_bytes"):
                text = await self._backend.transcribe_bytes(wav_bytes)
            elif hasattr(self._backend, "transcribe"):
                import tempfile

                fd = None
                path = None
                try:
                    fd, path = tempfile.mkstemp(suffix=".wav")
                    with os.fdopen(fd, "wb") as f:
                        f.write(wav_bytes)
                        fd = -1
                    text = await self._backend.transcribe(path)
                finally:
                    if fd is not None and fd >= 0:
                        with contextlib.suppress(Exception):
                            os.close(fd)
                    if path:
                        with contextlib.suppress(Exception):
                            os.unlink(path)
            else:
                text = None

            return (text or "").strip()
        except Exception as e:
            logger.debug("Streaming transcription error: %s", e)
            return ""

    def _encode_wav(self, pcm: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buffer.getvalue()
