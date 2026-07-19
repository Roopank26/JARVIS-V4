"""
Interrupt Manager for JARVIS voice system.

Provides a thread-safe, async-safe, event-driven interrupt mechanism.
All voice components should query this manager instead of using
scattered global flags.
"""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)


class InterruptManager:
    """
    Thread-safe interrupt manager.

    Wraps both a threading.Event (for callbacks from audio threads) and
    an asyncio.Event (for async consumers). Setting either propagates to
    the other, ensuring consistent interrupt state across sync/async
    boundaries.
    """

    def __init__(self) -> None:
        self._thread_event = threading.Event()
        self._async_event = asyncio.Event()
        self._lock = threading.Lock()
        self._interrupted = False

    def interrupt(self) -> None:
        """Signal that an interrupt has occurred."""
        with self._lock:
            if self._interrupted:
                return
            self._interrupted = True
        self._thread_event.set()
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._async_event.set)
        except RuntimeError:
            self._async_event.set()
        logger.debug("Interrupt signaled")

    def clear(self) -> None:
        """Clear the interrupt signal."""
        with self._lock:
            self._interrupted = False
        self._thread_event.clear()
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._async_event.clear)
        except RuntimeError:
            self._async_event.clear()
        logger.debug("Interrupt cleared")

    def is_interrupted(self) -> bool:
        """Return True if an interrupt is active."""
        return self._thread_event.is_set()

    async def wait_if_interrupted(self) -> None:
        """Async wait until the interrupt is cleared."""
        if self._async_event.is_set():
            await self._async_event.wait()

    async def wait_for_interrupt(self) -> None:
        """Async wait until an interrupt occurs."""
        await self._async_event.wait()

    def reset(self) -> None:
        """Reset the manager to its initial state."""
        self.clear()
