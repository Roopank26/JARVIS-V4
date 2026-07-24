"""
Shared Context Bus for JARVIS.

Extends EventBus with structured envelopes so agents can exchange:
- Task
- Goal
- Context
- Memory
- Progress
- Errors
- Plans
- Results
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class ContextEnvelope:
    """Structured envelope for context exchanges."""

    def __init__(
        self,
        task_id: str | None = None,
        goal_id: str | None = None,
        event_type: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = uuid.uuid4().hex[:12]
        self.task_id = task_id or ""
        self.goal_id = goal_id or ""
        self.event_type = event_type or "context"
        self.data = data or {}
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class ContextBus:
    """
    Facade over EventBus adding task/goal-structured envelopes.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._subscribers: dict[str, list[Callable[[ContextEnvelope], None]]] = {}

    def _dispatch(self, envelope: ContextEnvelope) -> None:
        handlers = list(self._subscribers.get(envelope.event_type, []))
        for h in handlers:
            try:
                h(envelope)
            except Exception as exc:
                logger.debug("Context bus handler error: %s", exc)

    def publish(
        self,
        event_type: str = "context",
        task_id: str | None = None,
        goal_id: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextEnvelope:
        envelope = ContextEnvelope(
            task_id=task_id,
            goal_id=goal_id,
            event_type=event_type,
            data=data or {},
            metadata=metadata or {},
        )
        self._bus.emit(
            EventType.STAGE,
            {
                "stage": event_type,
                "context_envelope": envelope.to_dict(),
            },
        )
        self._dispatch(envelope)
        return envelope

    def subscribe(
        self, event_type: str, handler: Callable[[ContextEnvelope], None]
    ) -> Callable[[], None]:
        self._subscribers.setdefault(event_type, []).append(handler)

        def unsubscribe() -> None:
            subs = self._subscribers.get(event_type, [])
            if handler in subs:
                subs.remove(handler)

        return unsubscribe

    def publish_task(self, task_id: str, data: dict[str, Any]) -> ContextEnvelope:
        envelope = self.publish(event_type="task", task_id=task_id, data=data)
        for h in list(self._subscribers.get(f"task:{task_id}", [])):
            try:
                h(envelope)
            except Exception as exc:
                logger.debug("Context bus task handler error: %s", exc)
        return envelope

    def publish_goal(self, goal_id: str, data: dict[str, Any]) -> ContextEnvelope:
        envelope = self.publish(event_type="goal", goal_id=goal_id, data=data)
        for h in list(self._subscribers.get(f"goal:{goal_id}", [])):
            try:
                h(envelope)
            except Exception as exc:
                logger.debug("Context bus goal handler error: %s", exc)
        return envelope

    def publish_result(self, task_id: str, data: dict[str, Any]) -> ContextEnvelope:
        return self.publish(event_type="result", task_id=task_id, data=data)

    def publish_error(self, task_id: str, data: dict[str, Any]) -> ContextEnvelope:
        return self.publish(event_type="error", task_id=task_id, data=data)

    def publish_plan(self, task_id: str, plan: Any) -> ContextEnvelope:
        return self.publish(event_type="plan", task_id=task_id, data={"plan": plan})

    def subscribe_task(self, task_id: str, handler: Callable[[ContextEnvelope], None]) -> Callable[[], None]:
        key = f"task:{task_id}"
        return self.subscribe(key, handler)

    def subscribe_goal(self, goal_id: str, handler: Callable[[ContextEnvelope], None]) -> Callable[[], None]:
        key = f"goal:{goal_id}"
        return self.subscribe(key, handler)

    def history(self, event_type: str | None = None) -> list[dict[str, Any]]:
        events = self._bus.history(EventType.STAGE)
        envelopes = []
        for ev in events:
            ctx = ev.data.get("context_envelope")
            if not ctx:
                continue
            if event_type is None or ctx.get("event_type") == event_type:
                envelopes.append(ctx)
        return envelopes


def get_context_bus() -> ContextBus:
    global _default_context_bus
    if "_default_context_bus" not in globals() or _default_context_bus is None:
        _default_context_bus = ContextBus()
    return _default_context_bus


def reset_context_bus() -> None:
    global _default_context_bus
    _default_context_bus = None
