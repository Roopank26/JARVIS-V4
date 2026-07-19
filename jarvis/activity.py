"""
Activity Center for JARVIS (Feature 12).

Maintains a categorized history of everything JARVIS does: voice commands,
research sessions, files opened, models used, plugins used, memory updates,
and searches. It subscribes to the event bus, so it records activity from the
existing backend without any backend changes.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ActivityEntry:
    id: str
    category: str
    title: str
    detail: str
    ts: float = field(default_factory=time.time)


_CATEGORY_MAP = {
    EventType.VOICE_TRANSCRIPT: "voice",
    EventType.RESEARCH: "research",
    EventType.TOOL: "tool",
    EventType.USER_MESSAGE: "chat",
    EventType.ASSISTANT_MESSAGE: "chat",
    EventType.PLAN: "plan",
    EventType.PLUGIN: "plugin",
    EventType.TASK: "task",
    EventType.ERROR: "error",
}


class ActivityCenter:
    """Records and queries activity history."""

    def __init__(self, bus: EventBus | None = None, limit: int = 500) -> None:
        self.bus = bus or get_event_bus()
        self.limit = limit
        self._entries: list[ActivityEntry] = []
        self._subs = []
        self._wire()

    def _wire(self) -> None:
        self._subs.append(self.bus.subscribe(None, self._on_event))

    def _on_event(self, event: Any) -> None:
        cat = _CATEGORY_MAP.get(event.type)
        if cat is None:
            return
        entry = self._to_entry(cat, event)
        if entry is None:
            return
        self._entries.append(entry)
        if len(self._entries) > self.limit:
            self._entries = self._entries[-self.limit :]

    def _to_entry(self, cat: str, event: Any) -> ActivityEntry | None:
        d = event.data or {}
        if cat == "voice":
            return ActivityEntry(
                str(event.id), "voice", "Voice command", str(d.get("text", ""))[:120]
            )
        if cat == "chat":
            role = "You" if event.type == EventType.USER_MESSAGE else "JARVIS"
            return ActivityEntry(
                str(event.id), "chat", f"{role} message", str(d.get("content", ""))[:120]
            )
        if cat == "tool":
            if d.get("phase") != "complete":
                return None
            return ActivityEntry(
                str(event.id), "tool", f"Tool: {d.get('tool')}", str(d.get("summary", ""))[:120]
            )
        if cat == "plan":
            return ActivityEntry(
                str(event.id),
                "plan",
                "Autonomous plan",
                str(d.get("plan", {}).get("goal", ""))[:120],
            )
        if cat == "research":
            return ActivityEntry(
                str(event.id), "research", "Research session", str(d.get("topic", ""))[:120]
            )
        if cat == "plugin":
            return ActivityEntry(str(event.id), "plugin", "Plugin", str(d)[:120])
        if cat == "task":
            state = d.get("state", "")
            return ActivityEntry(
                str(event.id),
                "task",
                f"Task {state}: {d.get('name', '')}",
                str(d.get("result", ""))[:120],
            )
        if cat == "error":
            return ActivityEntry(
                str(event.id), "error", d.get("title", "Error"), d.get("reason", "")[:120]
            )
        return None

    def recent(self, category: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items = self._entries
        if category:
            items = [e for e in items if e.category == category]
        return [asdict(e) for e in reversed(items[-limit:])]

    def categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._entries:
            counts[e.category] = counts.get(e.category, 0) + 1
        return counts

    def clear(self) -> None:
        self._entries.clear()


# Global default center
_default_center: ActivityCenter | None = None


def get_activity_center() -> ActivityCenter:
    global _default_center
    if _default_center is None:
        _default_center = ActivityCenter()
    return _default_center


def reset_activity_center() -> None:
    global _default_center
    _default_center = None
