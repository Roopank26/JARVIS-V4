"""
Event bus for JARVIS.

A lightweight async-friendly publish/subscribe bus used to decouple the
assistant's internal activity from the UI. The backend (agent, planner,
executor, tools, voice) stays untouched; orchestration layers emit typed
events here so the premium UI can react without polling.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """High-level event categories emitted by JARVIS."""

    # Reasoning / orchestration stages
    STAGE = "stage"  # A visible reasoning stage changed
    PLAN = "plan"  # An autonomous plan was generated
    STEP = "step"  # A plan step started/finished
    TOOL = "tool"  # A tool started/completed/errored
    TOKEN = "token"  # A streamed response token
    RESPONSE = "response"  # Final response ready

    # Conversation
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    CONTEXT_RESET = "context_reset"

    # Voice
    VOICE_STATE = "voice_state"  # listening/speaking/idle changes
    VOICE_TRANSCRIPT = "voice_transcript"
    VOICE_INTERRUPT = "voice_interrupt"

    # System
    STATUS = "status"  # CPU/RAM/provider/voice/memory metrics
    TASK = "task"  # background task state change
    SUGGESTION = "suggestion"  # proactive suggestion
    ERROR = "error"  # friendly error with fix
    TOAST = "toast"  # transient notification
    PLUGIN = "plugin"  # plugin discovered/enabled/disabled

    # Activity center
    RESEARCH = "research"  # research session events
    ACTIVITY = "activity"  # any activity-center event

    # Proactive / notifications
    NOTIFICATION = "notification"
    INTERRUPT = "interrupt"
    BACKGROUND_COMPLETE = "background_complete"
    WORKFLOW = "workflow"

    # Provider / model lifecycle
    PROVIDER_DISCOVERED = "provider_discovered"  # new provider detected at startup
    PROVIDER_AVAILABLE = "provider_available"  # provider became available
    PROVIDER_UNAVAILABLE = "provider_unavailable"  # provider became unavailable
    PROVIDER_SWITCHED = "provider_switched"  # active provider changed
    MODEL_SWITCHED = "model_switched"  # active model changed


@dataclass
class JarvisEvent:
    """A single event emitted on the bus."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


# Stage identifiers used by the orchestrator (high level, no internals leaked)
class Stage:
    THINKING = "thinking"
    PLANNING = "planning"
    SELECTING_TOOLS = "selecting_tools"
    EXECUTING = "executing"
    OBSERVING = "observing"
    GENERATING = "generating"
    COMPLETE = "complete"


_STAGE_LABELS: dict[str, str] = {
    Stage.THINKING: "Thinking",
    Stage.PLANNING: "Planning",
    Stage.SELECTING_TOOLS: "Selecting tools",
    Stage.EXECUTING: "Executing",
    Stage.OBSERVING: "Observing results",
    Stage.GENERATING: "Generating response",
    Stage.COMPLETE: "Complete",
}

# Ordering for timeline rendering
STAGE_ORDER: list[str] = [
    Stage.THINKING,
    Stage.PLANNING,
    Stage.SELECTING_TOOLS,
    Stage.EXECUTING,
    Stage.OBSERVING,
    Stage.GENERATING,
    Stage.COMPLETE,
]


def stage_label(stage: str) -> str:
    """Human label for a stage id."""
    return _STAGE_LABELS.get(stage, stage.replace("_", " ").title())


class EventBus:
    """
    In-process publish/subscribe bus.

    Handlers are plain callables ``(event: JarvisEvent) -> None``. They are
    invoked synchronously and exceptions are swallowed per-handler so a single
    bad subscriber cannot break emission.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[JarvisEvent], None]]] = {}
        self._any_handlers: list[Callable[[JarvisEvent], None]] = []
        self._history: list[JarvisEvent] = []
        self._history_limit = 500
        self._lock = asyncio.Lock() if False else None  # emission is sync/coroutine-free

    def subscribe(
        self,
        event_type: EventType | None,
        handler: Callable[[JarvisEvent], None],
    ) -> Callable[[], None]:
        """
        Subscribe to an event type (or all events if ``event_type`` is None).

        Returns an unsubscribe callable.
        """
        if event_type is None:
            self._any_handlers.append(handler)
        else:
            self._handlers.setdefault(event_type, []).append(handler)

        def unsubscribe() -> None:
            self.unsubscribe(event_type, handler)

        return unsubscribe

    def unsubscribe(
        self,
        event_type: EventType | None,
        handler: Callable[[JarvisEvent], None],
    ) -> None:
        """Remove a previously registered handler."""
        if event_type is None:
            if handler in self._any_handlers:
                self._any_handlers.remove(handler)
            return
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> JarvisEvent:
        """Emit an event to all matching subscribers."""
        event = JarvisEvent(type=event_type, data=data or {})
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

        for handler in list(self._any_handlers):
            try:
                handler(event)
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Event handler error: {e}")

        for handler in list(self._handlers.get(event_type, [])):
            try:
                handler(event)
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Event handler error: {e}")

        return event

    def history(self, event_type: EventType | None = None) -> list[JarvisEvent]:
        """Return recent events, optionally filtered by type."""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.type == event_type]

    def clear_history(self) -> None:
        """Clear the in-memory event history."""
        self._history.clear()


# Global default bus
_default_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get (or create) the process-wide event bus."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_event_bus() -> None:
    """Reset the global bus (used by tests)."""
    global _default_bus
    _default_bus = None
