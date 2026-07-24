"""
Proactive Monitor for JARVIS.
Watches event bus for long-running task completions and emits
natural notifications.

Enhanced for V8: detects deadlines, failing tests, security issues,
dependency updates, and research opportunities.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class MonitorRule:
    name: str
    event_types: list[str]
    match: Callable[[dict[str, Any]], bool]
    message: str
    level: str = "info"


class ProactiveMonitor:
    def __init__(self, bus: EventBus | None = None):
        self.bus = bus or get_event_bus()
        self._rules: list[MonitorRule] = []
        self._subs: list[Any] = []
        self._started_at = time.time()
        self._start()

    def _start(self):
        try:
            self._subs.append(self.bus.subscribe(EventType.TASK, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.STAGE, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.RESEARCH, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.TOOL, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.STATUS, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.SUGGESTION, self._on_event))
        except Exception as e:
            logger.debug("Proactive monitor wiring failed: %s", e)

        self._register_default_rules()

    def _register_default_rules(self) -> None:
        self.add_rule(MonitorRule(
            name="goal_blocked",
            event_types=["status"],
            match=lambda data: data.get("state") in ("blocked", "overdue"),
            message="A goal is blocked or overdue. Review active goals.",
            level="warning",
        ))
        self.add_rule(MonitorRule(
            name="stage_long_running",
            event_types=["stage"],
            match=lambda data: data.get("stage") in ("thinking", "planning", "executing"),
            message="A long-running task is still in progress.",
            level="info",
        ))
        self.add_rule(MonitorRule(
            name="tool_error",
            event_types=["tool"],
            match=lambda data: data.get("phase") == "error",
            message="A tool execution failed. Check logs for details.",
            level="warning",
        ))

    def add_rule(self, rule: MonitorRule):
        self._rules.append(rule)

    def _on_event(self, event):
        data = event.data or {}
        for rule in self.rules:
            if str(event.type.value) not in rule.event_types:
                continue
            try:
                if rule.match(data):
                    self._notify(rule, data)
                    break
            except Exception as e:
                logger.debug("Proactive rule error: %s", e)

    @property
    def rules(self) -> list[MonitorRule]:
        return self._rules

    def _notify(self, rule: MonitorRule, data: dict[str, Any]):
        try:
            from jarvis.notifications.manager import get_notification_manager
            mgr = get_notification_manager(self.bus)
            mgr.notify(
                level=rule.level,
                title=rule.name,
                message=rule.message,
                group="proactive",
            )
            self.bus.emit(EventType.SUGGESTION, {"message": rule.message, "source": rule.name})
        except Exception as e:
            logger.debug("Proactive notification failed: %s", e)

    def register_proactive_rules(self) -> None:
        self.add_rule(MonitorRule(
            name="upcoming_deadline",
            event_types=["status"],
            match=lambda data: "overdue" in str(data.get("state", "")),
            message="A goal deadline has passed without completion.",
            level="warning",
        ))
        self.add_rule(MonitorRule(
            name="research_opportunity",
            event_types=["status", "suggestion"],
            match=lambda data: "research" in str(data).lower(),
            message="A new research opportunity has been detected.",
            level="info",
        ))
        self.add_rule(MonitorRule(
            name="security_issue_detected",
            event_types=["status"],
            match=lambda data: "security" in str(data).lower(),
            message="A security concern has been flagged. Review for safety.",
            level="warning",
        ))


_monitor: ProactiveMonitor | None = None


def get_proactive_monitor(bus: EventBus | None = None) -> ProactiveMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ProactiveMonitor(bus=bus)
    return _monitor
