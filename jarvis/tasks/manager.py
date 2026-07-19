"""
Background task manager for JARVIS.

Long-running jobs (repository indexing, PDF embedding, research, downloads,
model loading, dataset processing) run here instead of blocking the
conversation. Each task has progress, ETA, logs, and supports pause/resume/
cancel (Feature 8, Feature 11).

This is a standalone module that the backend tasks can be wrapped into; it does
not replace any existing service logic.
"""

from __future__ import annotations

import asyncio
import builtins
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class TaskState(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskLog:
    ts: float
    level: str
    message: str


@dataclass
class BackgroundTask:
    id: str
    name: str
    state: TaskState
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    progress: float = 0.0
    total: int | None = None
    done: int = 0
    eta_seconds: float | None = None
    logs: list[TaskLog] = field(default_factory=list)
    result: str | None = None
    error: str | None = None
    category: str = "general"
    _coro: Any = field(default=None, repr=False)
    _cancel: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _pause: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    retries: int = 0
    max_retries: int = 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        d.pop("_coro", None)
        return d


ProgressFn = Callable[[float, int | None, int | None], None]


class BackgroundTaskManager:
    """Manages background tasks with queue, progress, pause/resume/cancel."""

    def __init__(self, bus: EventBus | None = None, max_concurrent: int = 3) -> None:
        self.bus = bus or get_event_bus()
        self.max_concurrent = max_concurrent
        self._tasks: dict[str, BackgroundTask] = {}
        self._order: list[str] = []
        self._running = 0
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._scheduler())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    def submit(
        self,
        name: str,
        coro_factory: Callable[[], Awaitable[str]],
        category: str = "general",
        total: int | None = None,
    ) -> str:
        """
        Submit a background task.

        Args:
            name: Human-readable task name.
            coro_factory: Zero-arg callable returning the coroutine to run.
            category: Grouping label (e.g. 'rag', 'research', 'indexing').
            total: Optional total units for progress.

        Returns:
            Task id.
        """
        task_id = uuid.uuid4().hex[:10]
        task = BackgroundTask(
            id=task_id,
            name=name,
            state=TaskState.QUEUED,
            created_at=time.time(),
            category=category,
            total=total,
            _coro=coro_factory,
        )
        self._tasks[task_id] = task
        self._order.append(task_id)
        self._emit(task)
        logger.info(f"Task queued: {name} ({task_id})")
        return task_id

    def get(self, task_id: str) -> BackgroundTask | None:
        return self._tasks.get(task_id)

    def list(self) -> builtins.list[BackgroundTask]:
        return [self._tasks[i] for i in self._order]

    def list_active(self) -> builtins.list[BackgroundTask]:
        return [t for t in self.list() if t.state in (TaskState.QUEUED, TaskState.RUNNING, TaskState.PAUSED)]

    async def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            return False
        task._cancel.set()
        task.state = TaskState.CANCELLED
        task.finished_at = time.time()
        self._log(task, "info", "Cancelled by user")
        self._emit(task)
        return True

    async def pause(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.state != TaskState.RUNNING:
            return False
        task._pause.set()
        task.state = TaskState.PAUSED
        self._emit(task)
        return True

    async def resume(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.state != TaskState.PAUSED:
            return False
        task._pause.clear()
        task.state = TaskState.RUNNING
        self._emit(task)
        return True

    def make_progress(self, task_id: str) -> ProgressFn:
        """Return a progress callback bound to a task (call from within task)."""

        def _progress(progress: float, done: int | None = None, total: int | None = None) -> None:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.progress = max(0.0, min(1.0, float(progress)))
            if done is not None:
                task.done = done
            if total is not None:
                task.total = total
            self._update_eta(task)
            self._emit(task)

        return _progress

    def log(self, task_id: str, message: str, level: str = "info") -> None:
        task = self._tasks.get(task_id)
        if task:
            self._log(task, level, message)
            self._emit(task)

    def _log(self, task: BackgroundTask, level: str, message: str) -> None:
        task.logs.append(TaskLog(time.time(), level, message))
        if len(task.logs) > 200:
            task.logs = task.logs[-200:]

    def _update_eta(self, task: BackgroundTask) -> None:
        if task.started_at and task.progress > 0:
            elapsed = time.time() - task.started_at
            task.eta_seconds = (elapsed / task.progress) * (1 - task.progress)

    async def _scheduler(self) -> None:
        while True:
            queued = [
                self._tasks[i]
                for i in self._order
                if self._tasks[i].state == TaskState.QUEUED
            ]
            while self._running < self.max_concurrent and queued:
                task = queued.pop(0)
                task.state = TaskState.RUNNING
                task.started_at = time.time()
                self._running += 1
                asyncio.create_task(self._run(task))
            await asyncio.sleep(0.2)

    async def _run(self, task: BackgroundTask) -> None:
        try:
            while True:
                try:
                    if task._pause.is_set():
                        await task._pause.wait()
                    if task._cancel.is_set():
                        raise asyncio.CancelledError()

                    coro = task._coro()
                    result = await asyncio.wait_for(coro, timeout=None)
                    task.result = str(result) if result is not None else ""
                    task.progress = 1.0
                    task.state = TaskState.COMPLETED
                    task.finished_at = time.time()
                    self._log(task, "info", "Completed")
                    break
                except asyncio.CancelledError:
                    task.state = TaskState.CANCELLED
                    task.finished_at = time.time()
                    self._log(task, "info", "Cancelled")
                    break
                except Exception as e:
                    task.retries += 1
                    if task.retries <= task.max_retries:
                        self._log(task, "warning", f"Retry {task.retries}: {e}")
                        await asyncio.sleep(1.0)
                        continue
                    task.error = str(e)
                    task.state = TaskState.FAILED
                    task.finished_at = time.time()
                    self._log(task, "error", f"Failed: {e}")
                    break
        finally:
            self._running = max(0, self._running - 1)
            self._emit(task)

    def _emit(self, task: BackgroundTask) -> None:
        self.bus.emit(EventType.TASK, task.to_dict())


# Global default manager
_default_manager: BackgroundTaskManager | None = None


def get_task_manager() -> BackgroundTaskManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = BackgroundTaskManager()
    return _default_manager


def reset_task_manager() -> None:
    global _default_manager
    _default_manager = None
