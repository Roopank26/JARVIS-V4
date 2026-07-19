"""
Conversation Manager for JARVIS voice system.

Manages conversation mode: after JARVIS finishes speaking, remain
listening for follow-up questions until a configurable timeout.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Tracks conversation mode state and handles timeout.

    When active, JARVIS stays in LISTENING state after speaking,
    ready for follow-up questions. After ``timeout`` seconds of
    inactivity, the conversation ends and returns to wake-word mode.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        bus=None,
        on_timeout: Callable[[], None] | None = None,
    ) -> None:
        self._timeout = timeout
        self._bus = bus
        self._on_timeout = on_timeout
        self._active = False
        self._timer_task: asyncio.Task | None = None

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        """Enter conversation mode and start the timeout timer."""
        if self._active:
            self._reset_timer()
            return
        self._active = True
        self._reset_timer()
        logger.debug("Conversation mode started")

    def stop(self) -> None:
        """Exit conversation mode and cancel the timer."""
        self._active = False
        self._cancel_timer()
        logger.debug("Conversation mode stopped")

    def touch(self) -> None:
        """Reset the inactivity timer (call on user activity)."""
        if not self._active:
            return
        self._reset_timer()

    def _reset_timer(self) -> None:
        self._cancel_timer()
        loop = asyncio.get_event_loop()
        self._timer_task = loop.create_task(self._timeout_task())

    def _cancel_timer(self) -> None:
        if self._timer_task is not None:
            self._timer_task.cancel()
            with contextlib.suppress(Exception):
                self._timer_task.result()
            self._timer_task = None

    async def _timeout_task(self) -> None:
        try:
            await asyncio.sleep(self._timeout)
        except asyncio.CancelledError:
            return
        if not self._active:
            return
        self._active = False
        logger.debug("Conversation timeout")
        if self._on_timeout:
            try:
                self._on_timeout()
            except Exception as e:
                logger.debug("Conversation timeout callback error: %s", e)
        if self._bus:
            try:
                from jarvis.voice.voice_events import emit_conversation_timeout
                emit_conversation_timeout(self._bus)
            except Exception:
                pass
