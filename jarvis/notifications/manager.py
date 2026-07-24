"""
Smart Notifications for JARVIS.

Provides a notification manager with support for:
- info, success, warning, reminder, background completion
- dismissible, grouped, timestamped, non-intrusive notifications
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    REMINDER = "reminder"
    BACKGROUND = "background"


class NotificationGroup:
    def __init__(self, group_id: str, title: str):
        self.group_id = group_id
        self.title = title
        self.items: list[Notification] = []
        self._dismissed = False

    def add(self, notification: Notification):
        if not self._dismissed:
            self.items.append(notification)

    def dismiss(self):
        self._dismissed = True
        for n in self.items:
            n.dismissed = True


@dataclass
class Notification:
    id: str
    level: NotificationLevel
    title: str
    message: str
    timestamp: float = field(default_factory=time.time)
    group: str | None = None
    dismissed: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp,
            "group": self.group,
            "dismissed": self.dismissed,
            "data": self.data,
        }


class NotificationManager:
    def __init__(self, bus: EventBus | None = None, limit: int = 200):
        self.bus = bus or get_event_bus()
        self.limit = limit
        self._items: list[Notification] = []
        self._groups: dict[str, NotificationGroup] = {}
        self._subs: list[Any] = []
        self._lock = asyncio.Lock()
        self._wire()

    def _wire(self):
        self._bus = get_event_bus()
        try:
            from jarvis.events import EventType
            self._subs.append(self._bus.subscribe(EventType.STAGE, self._on_event))
            self._subs.append(self._bus.subscribe(EventType.TASK, self._on_event))
            self._subs.append(self._bus.subscribe(EventType.TOOL, self._on_event))
            self._subs.append(self._bus.subscribe(EventType.RESEARCH, self._on_event))
            self._subs.append(self._bus.subscribe(EventType.ERROR, self._on_event))
        except Exception:
            pass

    def _on_event(self, event):
        try:
            data = event.data or {}
            if event.type == EventType.TASK:
                state = data.get("state", "").lower()
                if state in {"complete", "completed", "finished", "done"}:
                    self.notify(
                        NotificationLevel.SUCCESS,
                        data.get("name", "Task"),
                        data.get("result", "completed"),
                        group="tasks",
                    )
                elif state in {"error", "failed"}:
                    self.notify(
                        NotificationLevel.WARNING,
                        data.get("name", "Task"),
                        data.get("error", "failed"),
                        group="tasks",
                    )
            elif event.type == EventType.ERROR:
                self.notify(
                    NotificationLevel.WARNING,
                    data.get("title", "Error"),
                    data.get("reason", ""),
                    group="errors",
                )
        except Exception:
            pass

    def notify(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        group: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            id=uuid.uuid4().hex[:10],
            level=level,
            title=title,
            message=message,
            group=group,
            data=data or {},
        )
        self._items.append(notification)
        if len(self._items) > self.limit:
            self._items = self._items[-self.limit :]
        if group:
            if group not in self._groups:
                self._groups[group] = NotificationGroup(group, title)
            self._groups[group].add(notification)

        with contextlib.suppress(Exception):
            self.bus.emit(
                EventType.TOAST,
                {
                    "id": notification.id,
                    "level": level.value,
                    "title": title,
                    "message": message,
                    "timestamp": notification.timestamp,
                    "group": group,
                },
            )

        return notification

    def dismiss(self, notification_id: str):
        for item in self._items:
            if item.id == notification_id:
                item.dismissed = True
                if item.group and item.group in self._groups:
                    self._groups[item.group].dismissed = True
                break

    def dismiss_group(self, group: str):
        if group in self._groups:
            self._groups[group].dismiss()

    def get_active(self, level: NotificationLevel | None = None) -> list[dict[str, Any]]:
        items = [n for n in self._items if not n.dismissed]
        if level:
            items = [n for n in items if n.level == level]
        return [n.to_dict() for n in reversed(items[-50:])]

    def get_group(self, group: str) -> list[dict[str, Any]]:
        if group not in self._groups:
            return []
        return [n.to_dict() for n in reversed(self._groups[group].items[-20:]) if not n.dismissed]

    def clear(self):
        self._items.clear()
        self._groups.clear()


_manager: NotificationManager | None = None


def get_notification_manager(bus: EventBus | None = None) -> NotificationManager:
    global _manager
    if _manager is None:
        _manager = NotificationManager(bus=bus)
    return _manager


def reset_notification_manager() -> None:
    global _manager
    _manager = None
