"""
JARVIS Phase 3 — Orchestration Engine consolidation shim.

Wraps MasterAgent to provide the same public surface expected by dashboard
and runtime callers, without duplicating orchestration logic.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.master_agent import MasterAgent, create_master_agent
from jarvis.events import EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    task_id: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    strategy_used: str = "unknown"
    provider: str | None = None
    model: str | None = None
    steps_completed: int = 0
    steps_total: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapabilities:
    name: str
    capabilities: list[str] = field(default_factory=list)
    healthy: bool = False
    latency_ms: float = 0.0
    last_check: float = field(default_factory=time.time)


class OrchestrationEngine:
    def __init__(self, master_agent: MasterAgent | None = None) -> None:
        self._master = master_agent or create_master_agent()
        self.bus = get_event_bus()
        self._history: deque[TaskResult] = deque(maxlen=1000)
        self._subsystems: dict[str, Any] = {}
        self._running = False

    async def process(self, user_input: str, goal: str | None = None) -> str:
        task_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        self.bus.emit(EventType.STAGE, {"stage": "thinking", "task_id": task_id})
        try:
            result = await self._master.process(user_input, goal=goal)
            duration_ms = (time.perf_counter() - start) * 1000.0
            self._history.append(TaskResult(
                task_id=task_id, success=True, output=result, duration_ms=duration_ms
            ))
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            self._history.append(TaskResult(
                task_id=task_id, success=False, error=str(exc), duration_ms=duration_ms
            ))
            logger.error("Orchestration failed for task %s: %s", task_id, exc)
            raise

    def register_subsystem(self, name: str, instance: Any) -> None:
        self._subsystems[name] = instance

    def get_subsystem(self, name: str) -> Any | None:
        return self._subsystems.get(name)

    async def delegate(self, agent_name: str, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from jarvis.agents.collaboration import AgentCollaboration
            collab = AgentCollaboration()
            result = await collab.delegate(agent_name, capability, payload)
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_checkpoint(self, task_id: str, state: dict[str, Any]) -> None:
        pass

    def get_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        return None

    def clear_checkpoint(self, task_id: str) -> None:
        pass

    async def health_check(self) -> dict[str, AgentCapabilities]:
        return {}

    def get_recent_history(self, limit: int = 20) -> list[TaskResult]:
        return list(self._history)[-limit:]

    async def start(self) -> None:
        self._running = True

    async def shutdown(self) -> None:
        self._running = False


def get_orchestration_engine(engine: OrchestrationEngine | None = None) -> OrchestrationEngine:
    global _default_engine
    if "_default_engine" not in globals() or _default_engine is None:
        _default_engine = OrchestrationEngine()
    return _default_engine


def reset_orchestration_engine() -> None:
    global _default_engine
    _default_engine = None
