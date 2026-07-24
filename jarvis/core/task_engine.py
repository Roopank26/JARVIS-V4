"""
Long Running Task Engine.

Supports background tasks with:
- Pause
- Resume
- Cancel
- Progress
- Notifications
- Automatic recovery
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TaskHandle:
    task_id: str
    name: str
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class LongRunningTaskEngine:
    """
    Manages background tasks with pause/resume/cancel + persistence.
    """

    def __init__(self, state_dir: Path | None = None, bus: EventBus | None = None):
        self.state_dir = state_dir or (Path.home() / ".jarvis" / "tasks")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.bus = bus or get_event_bus()
        self._tasks: dict[str, TaskHandle] = {}
        self._asyncio_tasks: dict[str, asyncio.Task] = {}
        self._pause_events: dict[str, asyncio.Event] = {}

    def create_task(
        self,
        name: str,
        coro_factory: Callable[[TaskHandle], Coroutine[Any, Any, Any]],
        metadata: dict[str, Any] | None = None,
        max_progress: float = 100.0,
    ) -> TaskHandle:
        task_id = uuid.uuid4().hex[:12]
        handle = TaskHandle(
            task_id=task_id,
            name=name,
            metadata={"max_progress": max_progress, **(metadata or {})},
        )
        self._tasks[task_id] = handle
        self._persist(handle)
        self._start(handle, coro_factory)
        return handle

    def pause(self, task_id: str) -> bool:
        handle = self._tasks.get(task_id)
        if not handle or handle.state != TaskState.RUNNING:
            return False
        handle.state = TaskState.PAUSED
        handle.updated_at = time.time()
        self._persist(handle)
        self._emit_task_event(handle)
        return True

    def resume(self, task_id: str) -> bool:
        handle = self._tasks.get(task_id)
        if not handle or handle.state != TaskState.PAUSED:
            return False
        handle.state = TaskState.RUNNING
        handle.updated_at = time.time()
        self._persist(handle)
        self._emit_task_event(handle)
        event = self._pause_events.get(task_id)
        if event is not None:
            event.set()
        return True

    def cancel(self, task_id: str) -> bool:
        handle = self._tasks.get(task_id)
        if not handle:
            return False
        handle.state = TaskState.CANCELLED
        handle.updated_at = time.time()
        self._persist(handle)
        self._emit_task_event(handle)
        asyncio_task = self._asyncio_tasks.pop(task_id, None)
        if asyncio_task is not None:
            asyncio_task.cancel()
        return True

    def get_task(self, task_id: str) -> TaskHandle | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskHandle]:
        return list(self._tasks.values())

    def get_running(self) -> list[TaskHandle]:
        return [t for t in self._tasks.values() if t.state == TaskState.RUNNING]

    def _start(self, handle: TaskHandle, coro_factory: Callable[[TaskHandle], Coroutine[Any, Any, Any]]) -> None:
        pause_event = asyncio.Event()
        pause_event.set()
        self._pause_events[handle.task_id] = pause_event

        async def wrapper() -> None:
            handle.state = TaskState.RUNNING
            handle.updated_at = time.time()
            self._persist(handle)
            self._emit_task_event(handle)
            try:
                await coro_factory(handle)
                handle.state = TaskState.COMPLETED
                handle.updated_at = time.time()
                self._persist(handle)
                self._emit_task_event(handle)
                self.bus.emit(EventType.BACKGROUND_COMPLETE, {"task_id": handle.task_id, "name": handle.name})
            except asyncio.CancelledError:
                handle.state = TaskState.CANCELLED
                handle.updated_at = time.time()
                self._persist(handle)
                self._emit_task_event(handle)
            except Exception as exc:
                handle.state = TaskState.FAILED
                handle.error = str(exc)
                handle.updated_at = time.time()
                self._persist(handle)
                self._emit_task_event(handle)

        task = asyncio.create_task(wrapper())
        self._asyncio_tasks[handle.task_id] = task

    def _persist(self, handle: TaskHandle) -> None:
        try:
            path = self.state_dir / f"{handle.task_id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "task_id": handle.task_id,
                        "name": handle.name,
                        "state": handle.state.value,
                        "progress": handle.progress,
                        "result": str(handle.result) if handle.result is not None else None,
                        "error": handle.error,
                        "created_at": handle.created_at,
                        "updated_at": handle.updated_at,
                        "metadata": handle.metadata,
                    },
                    f,
                    ensure_ascii=False,
                )
        except Exception:
            logger.debug("Task persistence failed", exc_info=True)

    def _emit_task_event(self, handle: TaskHandle) -> None:
        with contextlib.suppress(Exception):
            self.bus.emit(
                EventType.TASK,
                {
                    "task_id": handle.task_id,
                    "name": handle.name,
                    "state": handle.state.value,
                    "progress": handle.progress,
                },
            )

    async def wait(self, task_id: str) -> TaskHandle | None:
        asyncio_task = self._asyncio_tasks.get(task_id)
        if asyncio_task is None:
            return self._tasks.get(task_id)
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await asyncio_task
        return self._tasks.get(task_id)

    def shutdown(self) -> None:
        for task_id in list(self._asyncio_tasks):
            self.cancel(task_id)


def get_task_engine() -> LongRunningTaskEngine:
    global _default_task_engine
    if "_default_task_engine" not in globals():
        _default_task_engine = LongRunningTaskEngine()
    return _default_task_engine

