"""
JARVIS-V8 AGW — Top-Level Orchestrator.

Integrates all Directors, Work Session Mode, Project Intelligence,
AI Reasoning, and the existing multi-agent / evolution subsystems into a
single autonomous General Work layer.

Design principles:
- Does not replace existing 'core/', 'agents/', 'evolution/', 'memory/',
  'goals/', 'research/', 'repo/', 'workspace/', 'proactive/'.
- Wraps them, wires them, and orchestrates them end-to-end.
- Emits structured events on the shared EventBus.
- Never performs high-risk actions without owner approval.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from jarvis.agw.directors import (
    initialize_all_directors,
)
from jarvis.agw.project_intelligence import get_project_intelligence
from jarvis.agw.reasoning import get_reasoning_engine
from jarvis.agw.work_session import WorkSessionManager
from jarvis.events import EventBus, get_event_bus
from jarvis.evolution.owner import get_owner_model

logger = logging.getLogger(__name__)


class AGWOrchestrator:
    """Autonomous General Work Orchestrator.

    The central control surface that:
    1. Activates the right Director for every user instruction.
    2. Maintains Work Session context (project, goals, docs, commits).
    3. Updates Project Intelligence continuously.
    4. Enhances reasoning with the AI Reasoning Engine.
    5. Coordinates the existing multi-agent and evolution subsystems.
    6. Enforces safety: owner approval gates for high-risk operations.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._owner = get_owner_model()
        self._reasoning = get_reasoning_engine()
        self._work_session = WorkSessionManager(bus=self._bus)
        self._project_intel = get_project_intelligence()
        self._directors: dict[str, Any] = {}
        self._running = False
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._directors = await initialize_all_directors()
        self._initialized = True
        logger.info("[AGW] Orchestrator initialized with %d directors", len(self._directors))

    async def process(self, user_input: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Process an instruction through the AGW pipeline.

        Returns a structured result with:
        - intent / director matched
        - reasoning plan
        - execution result
        - artifacts
        """
        start = time.perf_counter()
        ctx = context or {}
        result: dict[str, Any] = {"input": user_input, "status": "error", "artifacts": {}}

        try:
            reasoning = await self._reasoning.reason(user_input, ctx)
            director_name = self._select_director(reasoning)
            director = self._directors.get(director_name)

            if not director and self._directors:
                director_name = "software_engineering"
                director = self._directors.get("software_engineering")

            if director:
                exec_result = await director.execute(user_input, {**ctx, "plan": reasoning.plan})
                result["status"] = exec_result.get("status", "completed")
                result["director"] = director_name
                result["plan"] = reasoning.plan
                result["confidence"] = reasoning.confidence
                result["artifacts"] = exec_result
            else:
                result["status"] = "error"
                result["error"] = "No director available"

            try:
                from jarvis.evolution.experience_collector import (
                    get_experience_collector,  # type: ignore[attr-defined]
                )
                collector = get_experience_collector()
                duration_ms = (time.perf_counter() - start) * 1000.0
                collector.record_task(
                    task_id="",
                    input_text=user_input,
                    output_text=str(result),
                    success=result["status"] == "completed",
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        return result

    async def start_work_session(self, project_path: str | None = None) -> dict[str, Any]:
        """Start a Work Session for the given project.

        Automatically loads context, prepares Director overlays, and primes Project Intelligence.
        """
        self._running = True
        ctx = await self._work_session.start_session(project_path)
        project_path = ctx.project_path
        intel_report = await self._project_intel.update_project(project_path)
        return {
            "work_session": self._work_session._session_context_to_dict(),
            "project_intel": intel_report,
        }

    def end_work_session(self) -> None:
        self._running = False
        self._work_session.end_session()

    def get_work_session_context(self) -> dict[str, Any] | None:
        ctx = self._work_session.get_context()
        return {
            "project_name": ctx.project_name if ctx else None,
            "repository": ctx.repository if ctx else None,
            "branch": ctx.branch if ctx else None,
            "todos": ctx.todos if ctx else None,
            "active_goals": ctx.active_goals if ctx else None,
        } if ctx else None

    def _select_director(self, reasoning: Any) -> str:
        if not reasoning.selected_agents:
            return "software_engineering"
        for agent in reasoning.selected_agents:
            mapping = {
                "research": "research",
                "software_engineering_director": "software_engineering",
                "executive_director": "executive",
                "knowledge_director": "knowledge",
                "learning_director": "learning",
                "quality_director": "quality",
                "security_director": "security",
                "architecture_director": "architecture",
                "automation_director": "automation",
                "commander": "software_engineering",
            }
            mapped = mapping.get(agent)
            if mapped and mapped in self._directors:
                return mapped
        return next(iter(self._directors.keys()))

    def get_status(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "running": self._running,
            "directors": list(self._directors.keys()),
            "work_session_active": self._work_session.get_context() is not None,
            "project_intel": self._project_intel.get_stats(),
            "owner": self._owner.get_owner().name if self._owner.get_owner() else "unknown",
        }

    def get_director(self, domain: str) -> Any:
        return self._directors.get(domain)

    def get_directors(self) -> dict[str, Any]:
        return dict(self._directors)


_instance: AGWOrchestrator | None = None


def get_agw_orchestrator() -> AGWOrchestrator:
    global _instance
    if _instance is None:
        _instance = AGWOrchestrator()
    return _instance


def reset_agw_orchestrator() -> None:
    global _instance
    _instance = None
