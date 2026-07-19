"""
Non-blocking audio playback queue for JARVIS.

Supports appending chunks, cancelling the queue, pausing, resuming,
and flushing. Uses sounddevice for low-latency playback in a background
task so the rest of the system remains responsive.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """A single audio chunk for playback."""

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"


class AudioQueue:
    """
    Thread-safe, async-aware audio playback queue.

    - ``enqueue`` appends a chunk without blocking.
    - The background playback task drains the queue sequentially.
    - ``cancel`` stops playback and clears remaining items.
    - ``pause`` / ``resume`` toggle playback.
    - ``flush`` drops all pending items.
    """

    def __init__(self, buffer_size: int = 64) -> None:
        self._queue: queue.Queue[AudioChunk | None] = queue.Queue(maxsize=buffer_size)
        self._lock = threading.Lock()
        self._playback_task: asyncio.Task | None = None
        self._cancelled = False
        self._paused = False
        self._current_stream: sd.OutputStream | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the background playback task."""
        if self._playback_task is not None:
            return
        self._event_loop = loop
        self._cancelled = False
        self._paused = False
        self._playback_task = asyncio.ensure_future(self._playback_loop(), loop=loop)

    def stop(self) -> None:
        """Stop playback and cancel the background task."""
        self.cancel()
        if self._playback_task is not None:
            self._playback_task.cancel()
            self._playback_task = None

    def enqueue(self, chunk: AudioChunk) -> bool:
        """Append a chunk. Returns False if the queue is cancelled."""
        with self._lock:
            if self._cancelled:
                return False
            try:
                self._queue.put_nowait(chunk)
            except queue.Full:
                logger.warning("Audio queue full; dropping chunk")
                return False
            return True

    def cancel(self) -> None:
        """Cancel playback and clear the queue."""
        with self._lock:
            self._cancelled = True
            self._paused = False
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._stop_stream()

    def pause(self) -> None:
        """Pause playback."""
        with self._lock:
            self._paused = True
        self._stop_stream()

    def resume(self) -> None:
        """Resume playback."""
        with self._lock:
            self._paused = False

    def flush(self) -> None:
        """Drop all pending items."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return not self._queue.empty() and not self._paused and not self._cancelled

    def _stop_stream(self) -> None:
        if self._current_stream is not None:
            try:
                self._current_stream.stop()
                self._current_stream.close()
            except Exception:
                pass
            self._current_stream = None

    async def _playback_loop(self) -> None:
        """Background task that drains the queue."""
        while True:
            try:
                chunk = await asyncio.to_thread(self._queue.get)
                if chunk is None:
                    break

                with self._lock:
                    if self._cancelled or self._paused:
                        continue

                await self._play_chunk(chunk)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Audio playback error: %s", e)

    async def _play_chunk(self, chunk: AudioChunk) -> None:
        """Play a single audio chunk."""
        try:
            audio_array = np.frombuffer(chunk.data, dtype=np.int16)
            if chunk.channels > 1:
                audio_array = audio_array.reshape(-1, chunk.channels)

            event = asyncio.Event()

            def callback(outdata, frames, time_info, status):
                if status:
                    logger.debug("Audio stream status: %s", status)
                remaining = len(audio_array) - self._played_frames
                if remaining <= 0:
                    outdata[:] = 0
                    event.set()
                    raise sd.CallbackStop()
                to_write = min(frames, remaining)
                outdata[:to_write] = audio_array[
                    self._played_frames : self._played_frames + to_write
                ].reshape(-1, 1)
                if to_write < frames:
                    outdata[to_write:] = 0
                    event.set()
                    raise sd.CallbackStop()
                self._played_frames += to_write

            self._played_frames = 0
            stream = sd.OutputStream(
                samplerate=chunk.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=1024,
                callback=callback,
            )
            self._current_stream = stream
            stream.start()
            try:
                await asyncio.wait_for(event.wait(), timeout=30.0)
            except TimeoutError:
                pass
            finally:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass
                if self._current_stream is stream:
                    self._current_stream = None
        except Exception as e:
            logger.debug("Play chunk error: %s", e)
