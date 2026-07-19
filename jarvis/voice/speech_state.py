"""
Speech state machine for JARVIS voice system.

Replaces boolean speaking/listening flags with a proper state machine
that emits events on every transition.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import StrEnum

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class SpeechState(StrEnum):
    """Voice interaction states."""

    IDLE = "idle"
    WAKE_LISTENING = "wake_listening"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PLANNING = "planning"
    RESPONDING = "responding"
    STREAMING = "streaming"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


# Valid transitions: (from_state, to_state) or None for any
_VALID_TRANSITIONS = {
    SpeechState.IDLE: {
        SpeechState.WAKE_LISTENING,
        SpeechState.LISTENING,
    },
    SpeechState.WAKE_LISTENING: {
        SpeechState.LISTENING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.LISTENING: {
        SpeechState.TRANSCRIBING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.TRANSCRIBING: {
        SpeechState.PLANNING,
        SpeechState.RESPONDING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.PLANNING: {
        SpeechState.RESPONDING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.RESPONDING: {
        SpeechState.STREAMING,
        SpeechState.SPEAKING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.STREAMING: {
        SpeechState.SPEAKING,
        SpeechState.INTERRUPTED,
        SpeechState.IDLE,
    },
    SpeechState.SPEAKING: {
        SpeechState.LISTENING,
        SpeechState.WAKE_LISTENING,
        SpeechState.IDLE,
        SpeechState.INTERRUPTED,
    },
    SpeechState.INTERRUPTED: {
        SpeechState.LISTENING,
        SpeechState.IDLE,
        SpeechState.TRANSCRIBING,
    },
}

_TRANSITION_EVENT_MAP = {
    SpeechState.IDLE: EventType.VOICE_STATE,
    SpeechState.WAKE_LISTENING: EventType.VOICE_STATE,
    SpeechState.LISTENING: EventType.VOICE_STATE,
    SpeechState.TRANSCRIBING: EventType.VOICE_STATE,
    SpeechState.PLANNING: EventType.VOICE_STATE,
    SpeechState.RESPONDING: EventType.VOICE_STATE,
    SpeechState.STREAMING: EventType.VOICE_STATE,
    SpeechState.SPEAKING: EventType.VOICE_STATE,
    SpeechState.INTERRUPTED: EventType.VOICE_INTERRUPT,
}


class SpeechStateMachine:
    """
    Event-driven state machine for voice interactions.

    Every transition emits a VOICE_STATE (or VOICE_INTERRUPT) event on the
    global event bus so the UI and other subsystems can react without
    polling.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or get_event_bus()
        self._state = SpeechState.IDLE
        self._previous_state = SpeechState.IDLE
        self._listeners: list[Callable[[SpeechState, SpeechState], None]] = []

    @property
    def state(self) -> SpeechState:
        return self._state

    @property
    def previous_state(self) -> SpeechState:
        return self._previous_state

    def on_transition(
        self, callback: Callable[[SpeechState, SpeechState], None]
    ) -> Callable[[], None]:
        """Register a listener for state transitions."""
        self._listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return unsubscribe

    def transition(self, new_state: SpeechState) -> bool:
        """
        Attempt to transition to a new state.

        Returns True if the transition was accepted and an event was emitted.
        """
        if new_state == self._state:
            return False

        allowed = _VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            logger.warning(
                "Invalid speech state transition: %s -> %s",
                self._state.value,
                new_state.value,
            )
            return False

        old_state = self._state
        self._previous_state = old_state
        self._state = new_state

        logger.debug("Speech state: %s -> %s", old_state.value, new_state.value)

        event_type = _TRANSITION_EVENT_MAP.get(new_state, EventType.VOICE_STATE)
        self._bus.emit(event_type, {
            "state": new_state.value,
            "previous_state": old_state.value,
        })

        for listener in list(self._listeners):
            try:
                listener(old_state, new_state)
            except Exception as e:  # pragma: no cover - defensive
                logger.error("State transition listener error: %s", e)

        return True

    def is_speaking(self) -> bool:
        return self._state in {
            SpeechState.SPEAKING,
            SpeechState.STREAMING,
            SpeechState.RESPONDING,
        }

    def is_listening(self) -> bool:
        return self._state in {
            SpeechState.WAKE_LISTENING,
            SpeechState.LISTENING,
            SpeechState.TRANSCRIBING,
        }

    def is_idle(self) -> bool:
        return self._state == SpeechState.IDLE

    def __repr__(self) -> str:
        return f"SpeechStateMachine(state={self._state.value})"
