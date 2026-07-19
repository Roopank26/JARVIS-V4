"""
Streaming Text-to-Speech for JARVIS.

Streams audio chunks as they are generated, supporting cancellation
for interruptible playback.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class StreamingTTS:
    """
    Streaming TTS wrapper.

    Yields audio chunks as they become available so the playback system
    can start speaking before the full response is synthesized.
    """

    def __init__(self, tts_backend) -> None:
        self._backend = tts_backend
        self._chunk_index = 0

    async def stream_speak(self, text: str, interrupt_event: asyncio.Event) -> AsyncIterator[bytes]:
        """
        Yield audio chunks for ``text`` until interrupted or exhausted.
        """
        self._chunk_index = 0

        if not self._backend:
            return

        try:
            if hasattr(self._backend, "speak"):
                audio = await self._backend.speak(text)
                if audio and not interrupt_event.is_set():
                    self._chunk_index += 1
                    yield audio
            elif hasattr(self._backend, "synthesize_stream"):
                async for chunk in self._backend.synthesize_stream(text):
                    if interrupt_event.is_set():
                        break
                    self._chunk_index += 1
                    yield chunk
            else:
                # Fallback: synthesize whole audio then yield
                if hasattr(self._backend, "speak_to_file"):
                    import os
                    import tempfile

                    fd = None
                    path = None
                    try:
                        fd, path = tempfile.mkstemp(suffix=".wav")
                        ok = await self._backend.speak_to_file(text, path)
                        if ok and not interrupt_event.is_set():
                            with open(path, "rb") as f:
                                data = f.read()
                            self._chunk_index += 1
                            yield data
                    finally:
                        if fd is not None:
                            with contextlib.suppress(Exception):
                                os.close(fd)
                        if path:
                            with contextlib.suppress(Exception):
                                os.unlink(path)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("Streaming TTS error: %s", e)

    @property
    def chunk_index(self) -> int:
        return self._chunk_index
