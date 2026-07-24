"""
Background Intelligence for JARVIS.
Low-priority background tasks for memory optimization, index maintenance,
and housekeeping.
"""

from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from jarvis.memory.long_term import LongTermMemory
from jarvis.suggestions import SuggestionEngine

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class BackgroundTask:
    name: str
    priority: TaskPriority
    last_run: float = 0.0
    interval_seconds: float = 3600.0
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class BackgroundIntelligence:
    def __init__(self):
        self._tasks: list[BackgroundTask] = []
        self._memory: LongTermMemory | None = None
        self._suggestion_engine: SuggestionEngine | None = None
        self._initialized = False
        self._register_defaults()

    def _register_defaults(self):
        self._tasks.extend([
            BackgroundTask(
                name="memory_cleanup",
                priority=TaskPriority.LOW,
                interval_seconds=7200.0,
                metadata={"action": "trim"},
            ),
            BackgroundTask(
                name="refresh_workspace",
                priority=TaskPriority.LOW,
                interval_seconds=3600.0,
                metadata={"action": "refresh"},
            ),
            BackgroundTask(
                name="dismiss_stale_notifications",
                priority=TaskPriority.LOW,
                interval_seconds=1800.0,
                metadata={"action": "dismiss"},
            ),
        ])

    def initialize(self) -> bool:
        if self._initialized:
            return True
        try:
            try:
                from jarvis.memory.long_term import LongTermMemory
                self._memory = LongTermMemory()
            except Exception:
                pass
            with contextlib.suppress(Exception):
                self._suggestion_engine = SuggestionEngine()
            self._initialized = True
            self._register_with_health_monitor()
            return True
        except Exception as e:
            logger.debug("Background intelligence init failed: %s", e)
            return False

    def _register_with_health_monitor(self) -> None:
        try:
            from jarvis.monitoring.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            monitor.register(
                "background_intelligence",
                starter=self.start if hasattr(self, "start") else self._noop_start,
                stopper=self.stop if hasattr(self, "stop") else self._noop_stop,
                memory_threshold_bytes=150 * 1024 * 1024,
                pauseable=True,
            )
        except Exception:
            pass

    async def _noop_start(self) -> None:
        pass

    async def _noop_stop(self) -> None:
        pass

    def get_due_tasks(self) -> list[BackgroundTask]:
        now = time.time()
        return [t for t in self._tasks if t.enabled and (now - t.last_run) >= t.interval_seconds]

    async def run_due(self) -> list[str]:
        if not self._initialized:
            self.initialize()
        completed: list[str] = []
        for task in self.get_due_tasks():
            try:
                await self._execute_task(task)
                task.last_run = time.time()
                completed.append(task.name)
            except Exception as e:
                logger.debug("Background task %s failed: %s", task.name, e)
        return completed

    async def _execute_task(self, task: BackgroundTask):
        action = task.metadata.get("action")
        if action == "trim" and self._memory:
            with contextlib.suppress(Exception):
                self._memory._trim_to_limit(self._memory._memory)
        elif action == "refresh":
            try:
                from jarvis.workspace.awareness import WorkspaceAwareness
                WorkspaceAwareness()._refresh()
            except Exception:
                pass
        elif action == "dismiss":
            try:
                from jarvis.notifications.manager import get_notification_manager
                mgr = get_notification_manager()
                for n in mgr.get_active():
                    age = datetime.now().timestamp() - n.get("timestamp", datetime.now().timestamp())
                    if age > 86400:
                        mgr.dismiss(n["id"])
            except Exception:
                pass
        else:
            logger.debug("Background task: %s", task.name)

    def add_task(self, task: BackgroundTask):
        self._tasks.append(task)

    def list_tasks(self) -> list[BackgroundTask]:
        return list(self._tasks)
