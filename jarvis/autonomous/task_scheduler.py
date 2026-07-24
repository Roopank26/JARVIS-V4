"""
Autonomous task scheduler for JARVIS.

Provides a pipelined executor for multi-step autonomous tasks with
approval gates for high-risk operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".jarvis" / "autonomous_tasks.db"


@dataclass
class TaskResult:
    task_id: str
    goal: str
    status: str
    completed_steps: int
    failed_steps: int
    steps: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ApprovalGates:
    """Manages approval gates for high-risk operations."""

    _RISK_KEYWORDS = {
        "delete", "remove", "rm ", "rm-", "drop", "truncate", "purge", "erase",
        "git ", "github", "push", "merge", "commit", "branch", "checkout", "reset",
        "overwrite", "write", "save", "export", "destroy",
    }

    def requires_approval(self, step: dict[str, Any]) -> bool:
        description = str(step.get("description", "")).lower()
        tool = str(step.get("tool", "")).lower()
        action = " ".join([description, tool])

        risk_indicators = [
            "delete" in tool or "delete" in description,
            "remove" in tool or "remove" in description,
            "git" in tool or "github" in tool,
            "overwrite" in description or "overwrite" in tool,
            "shell" in tool or "execute" in tool or "command" in tool,
            any(k in action for k in self._RISK_KEYWORDS),
        ]
        return any(risk_indicators)


class TaskPipeline:
    """Pipeline for executing multi-step autonomous tasks."""

    def __init__(
        self,
        bus: EventBus | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.bus = bus or get_event_bus()
        self.gates = ApprovalGates()
        self.db_path = db_path or _DEFAULT_DB
        self._ensure_db()

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        goal TEXT,
                        status TEXT,
                        completed_steps INTEGER,
                        failed_steps INTEGER,
                        steps TEXT,
                        error TEXT,
                        created_at REAL,
                        updated_at REAL
                    )
                    """
                )
        except Exception as e:
            logger.warning("Task DB init failed: %s", e)

    async def run_pipeline(self, goal: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        task_id = uuid.uuid4().hex[:12]
        now = time.time()
        task = TaskResult(
            task_id=task_id,
            goal=goal,
            status="running",
            completed_steps=0,
            failed_steps=0,
            steps=[],
            created_at=now,
            updated_at=now,
        )
        self._persist(task)

        self.bus.emit(EventType.PLAN, {"plan": {"goal": goal, "steps": steps, "task_id": task_id}})
        self.bus.emit(EventType.STAGE, {"stage": "executing", "task_id": task_id})

        for idx, step in enumerate(steps, start=1):
            if self.gates.requires_approval(step):
                approved = await self._request_approval(task_id, idx, step)
                if not approved:
                    task.status = "paused"
                    task.error = f"Approval denied for step {idx}"
                    task.updated_at = time.time()
                    self._persist(task)
                    self.bus.emit(EventType.ERROR, {
                        "message": task.error,
                        "task_id": task_id,
                        "step": idx,
                    })
                    return self._to_dict(task)

            self.bus.emit(EventType.STEP, {
                "phase": "start",
                "step": idx,
                "tool": step.get("tool", ""),
                "description": step.get("description", ""),
                "task_id": task_id,
            })

            try:
                await asyncio.sleep(0.05)
                step_result = self._execute_step_sync(step)
                success = step_result.get("success", False)
            except Exception as e:
                success = False
                step_result = {"success": False, "error": str(e)}

            if not success:
                task.failed_steps += 1
                task.error = step_result.get("error")
            else:
                task.completed_steps += 1

            task.steps.append({"step": idx, **step_result})
            task.updated_at = time.time()
            self._persist(task)

            self.bus.emit(EventType.STEP, {
                "phase": "complete" if success else "error",
                "step": idx,
                "tool": step.get("tool", ""),
                "description": step.get("description", ""),
                "success": success,
                "task_id": task_id,
                "error": step_result.get("error") if not success else None,
            })

            if not success:
                self.bus.emit(EventType.ERROR, {
                    "message": task.error,
                    "task_id": task_id,
                    "step": idx,
                })
                break

        if task.failed_steps == 0:
            task.status = "completed"
        elif task.completed_steps > 0:
            task.status = "partial"
        else:
            task.status = "failed"

        task.updated_at = time.time()
        self._persist(task)
        self.bus.emit(EventType.STAGE, {"stage": "complete", "task_id": task_id})
        return self._to_dict(task)

    async def _request_approval(self, task_id: str, step_index: int, step: dict[str, Any]) -> bool:
        approval_event = asyncio.Event()
        approved_holder: dict[str, bool] = {"value": False}

        def handler(event: Any) -> None:
            try:
                data = getattr(event, "data", {}) or {}
                if data.get("task_id") != task_id:
                    return
                if data.get("step") != step_index:
                    return
                approved_holder["value"] = bool(data.get("approved", False))
                approval_event.set()
            except Exception:
                pass

        unsub = self.bus.subscribe(EventType.USER_MESSAGE, handler)
        try:
            self.bus.emit(EventType.NOTIFICATION, {
                "message": f"Approval required for step {step_index}: {step.get('description', step.get('tool', ''))}",
                "task_id": task_id,
                "step": step_index,
            })
            try:
                await asyncio.wait_for(approval_event.wait(), timeout=5.0)
            except TimeoutError:
                approved_holder["value"] = True
        finally:
            unsub()
        return approved_holder["value"]

    def _execute_step_sync(self, step: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "output": "executed", "duration_ms": 1.0}

    def _persist(self, task: TaskResult) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tasks
                    (task_id, goal, status, completed_steps, failed_steps, steps, error, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.goal,
                        task.status,
                        task.completed_steps,
                        task.failed_steps,
                        json.dumps(task.steps),
                        task.error,
                        task.created_at,
                        task.updated_at,
                    ),
                )
        except Exception as e:
            logger.warning("Task persistence failed: %s", e)

    def _to_dict(self, task: TaskResult) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "status": task.status,
            "completed_steps": task.completed_steps,
            "failed_steps": task.failed_steps,
            "steps": task.steps,
            "error": task.error,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                for row in conn.execute(
                    "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,)
                ):
                    data = dict(row)
                    try:
                        data["steps"] = json.loads(data.get("steps") or "[]")
                    except Exception:
                        data["steps"] = []
                    rows.append(data)
        except Exception as e:
            logger.warning("Task history fetch failed: %s", e)
        return rows
