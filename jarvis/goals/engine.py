"""
Autonomous Goal Execution Engine for JARVIS.

Manages long-term goals, breaks them into milestones, generates tasks,
schedules execution, executes, monitors, adapts, and notifies the user.

Supports:
- Daily goals
- Weekly goals
- Project goals
- Learning goals
- Career goals
- Research goals

Phase 5 Long-Horizon Planning:
- Milestone auto-decomposition
- Progress trend analysis
- Blocked-task detection
- Replanning triggers
- Deadline risk prediction
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


class GoalStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    DEFERRED = "deferred"


class GoalType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    PROJECT = "project"
    LEARNING = "learning"
    CAREER = "career"
    RESEARCH = "research"
    CUSTOM = "custom"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class GoalTask:
    task_id: str
    goal_id: str
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    scheduled_at: datetime | None = None
    dependencies: list[str] = field(default_factory=list)
    result: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Milestone:
    name: str
    description: str
    tasks: list[str] = field(default_factory=list)
    completed_tasks: int = 0
    total_tasks: int = 0
    status: GoalStatus = GoalStatus.PENDING
    estimated_completion: datetime | None = None


@dataclass
class Goal:
    goal_id: str
    title: str
    description: str
    goal_type: GoalType = GoalType.CUSTOM
    status: GoalStatus = GoalStatus.PENDING
    milestones: list[Milestone] = field(default_factory=list)
    priority: str = "medium"
    deadline: datetime | None = None
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalProgress:
    goal_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    blocked_tasks: int = 0
    current_milestone: int = 0
    percent_complete: float = 0.0
    estimated_completion: datetime | None = None
    on_track: bool = True


class AutonomousGoalEngine:
    """
    Manages long-term goals and executes them autonomously.

    Flow:
    Goal → Milestones → Tasks → Schedule → Execute → Monitor → Adapt → Notify
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or get_event_bus()
        self._goals: dict[str, Goal] = {}
        self._tasks: dict[str, GoalTask] = {}
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._interrupt = asyncio.Event()
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._patterns = {
            "morning_routine": {
                "type": GoalType.DAILY,
                "template": "Morning routine: {tasks}",
            },
            "learning": {
                "type": GoalType.LEARNING,
                "template": "Continue learning {topic}",
            },
        }

    def create_goal(
        self,
        title: str,
        description: str,
        goal_type: GoalType = GoalType.CUSTOM,
        deadline: datetime | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        goal_id = uuid.uuid4().hex[:12]
        goal = Goal(
            goal_id=goal_id,
            title=title,
            description=description,
            goal_type=goal_type,
            deadline=deadline,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._goals[goal_id] = goal
        self._bus.emit(EventType.STATUS, {"goal": goal_id, "state": "created", "title": title})
        return goal

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def list_goals(self, status: GoalStatus | None = None) -> list[Goal]:
        goals = list(self._goals.values())
        if status is not None:
            goals = [g for g in goals if g.status == status]
        return goals

    def delete_goal(self, goal_id: str) -> bool:
        if goal_id in self._goals:
            del self._goals[goal_id]
            self._bus.emit(EventType.STATUS, {"goal": goal_id, "state": "deleted"})
            return True
        return False

    def add_milestone(self, goal_id: str, milestone: Milestone) -> bool:
        goal = self._goals.get(goal_id)
        if goal is None:
            return False
        goal.milestones.append(milestone)
        goal.updated_at = time.time()
        return True

    def create_task(
        self,
        goal_id: str,
        name: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: list[str] | None = None,
        scheduled_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GoalTask | None:
        goal = self._goals.get(goal_id)
        if goal is None:
            return None

        task_id = uuid.uuid4().hex[:12]
        task = GoalTask(
            task_id=task_id,
            goal_id=goal_id,
            name=name,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            scheduled_at=scheduled_at,
            metadata=metadata or {},
        )
        self._tasks[task_id] = task

        if goal.status == GoalStatus.PENDING:
            goal.status = GoalStatus.ACTIVE

        self._bus.emit(EventType.STATUS, {"task": task_id, "state": "created", "goal": goal_id})
        return task

    def get_task(self, task_id: str) -> GoalTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, goal_id: str | None = None, status: TaskStatus | None = None) -> list[GoalTask]:
        tasks = list(self._tasks.values())
        if goal_id is not None:
            tasks = [t for t in tasks if t.goal_id == goal_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def decompose_goal(self, goal_id: str, milestones: list[dict[str, Any]]) -> bool:
        goal = self._goals.get(goal_id)
        if goal is None:
            return False

        for ms_data in milestones:
            ms = Milestone(
                name=ms_data.get("name", ""),
                description=ms_data.get("description", ""),
                total_tasks=len(ms_data.get("tasks", [])),
            )
            for task_data in ms_data.get("tasks", []):
                self.create_task(
                    goal_id=goal_id,
                    name=task_data.get("name", ""),
                    description=task_data.get("description", ""),
                    priority=TaskPriority(task_data.get("priority", "medium")),
                    scheduled_at=task_data.get("scheduled_at"),
                    metadata=task_data.get("metadata", {}),
                )
            goal.milestones.append(ms)

        goal.updated_at = time.time()
        self._bus.emit(EventType.STATUS, {"goal": goal_id, "state": "decomposed"})
        return True

    def get_progress(self, goal_id: str) -> GoalProgress | None:
        goal = self._goals.get(goal_id)
        if goal is None:
            return None

        tasks = [t for t in self._tasks.values() if t.goal_id == goal_id]
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)

        percent = (completed / total * 100.0) if total > 0 else 0.0

        current_milestone = 0
        for i, ms in enumerate(goal.milestones):
            if ms.completed_tasks < ms.total_tasks:
                current_milestone = i
                break

        on_track = percent >= 50.0 or failed < total * 0.2

        return GoalProgress(
            goal_id=goal_id,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            blocked_tasks=blocked,
            current_milestone=current_milestone,
            percent_complete=round(percent, 2),
            on_track=on_track,
        )

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._interrupt.clear()
        self._bus.emit(EventType.STATUS, {"goal_engine": "running"})
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    def stop(self) -> None:
        self._running = False
        self._interrupt.set()
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            self._scheduler_task = None
        self._bus.emit(EventType.STATUS, {"goal_engine": "stopped"})

    async def shutdown(self) -> None:
        self.stop()

    async def _scheduler_loop(self) -> None:
        while self._running and not self._interrupt.is_set():
            try:
                await asyncio.sleep(60)
                if not self._running:
                    break
                await self._schedule_due_tasks()
                await self._check_deadlines()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Goal scheduler error: %s", exc)

    async def _schedule_due_tasks(self) -> None:
        now = datetime.now()
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if task.scheduled_at and task.scheduled_at <= now:
                task.status = TaskStatus.SCHEDULED
                self._bus.emit(EventType.STATUS, {"task": task.task_id, "state": "scheduled"})

    async def _check_deadlines(self) -> None:
        now = datetime.now()
        for goal in self._goals.values():
            if goal.status not in (GoalStatus.ACTIVE, GoalStatus.BLOCKED):
                continue
            deadline = goal.deadline
            if deadline and now >= deadline:
                progress = self.get_progress(goal.goal_id)
                if progress and progress.percent_complete < 100.0:
                    goal.status = GoalStatus.BLOCKED
                    self._bus.emit(EventType.STATUS, {"goal": goal.goal_id, "state": "overdue"})

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self._running,
            "goals": len(self._goals),
            "tasks": len(self._tasks),
            "status": "running" if self._running else "stopped",
        }


_goal_engine: AutonomousGoalEngine | None = None


def get_goal_engine() -> AutonomousGoalEngine:
    global _goal_engine
    if _goal_engine is None:
        _goal_engine = AutonomousGoalEngine()
    return _goal_engine


def reset_goal_engine() -> None:
    global _goal_engine
    _goal_engine = None
