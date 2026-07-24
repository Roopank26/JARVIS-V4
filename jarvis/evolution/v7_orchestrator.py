"""
JARVIS-V7 Evolution — Main Orchestrator.

V7 integration point that wires all evolution subsystems together and
exposes a single interface to the rest of JARVIS.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from jarvis.core.master_agent import MasterAgent
from jarvis.evolution.evolution_engine import get_evolution_engine
from jarvis.evolution.experience_collector import get_experience_collector
from jarvis.evolution.knowledge_graph_v2 import get_knowledge_graph
from jarvis.evolution.model_registry import get_model_registry
from jarvis.evolution.owner import get_owner_model
from jarvis.evolution.repo_watcher import get_repo_watcher
from jarvis.evolution.reports import get_executive_reports
from jarvis.evolution.research_engine import get_research_engine
from jarvis.evolution.self_review import get_self_review_engine
from jarvis.evolution.system_resource_monitor import get_resource_monitor

logger = logging.getLogger(__name__)


class V7JarvisOrchestrator:
    def __init__(self, master_agent: MasterAgent | None = None):
        self.master_agent = master_agent
        if self.master_agent is None:
            logger.debug("V7JarvisOrchestrator created without master_agent; deferring creation")
        self.owner = get_owner_model()
        self.collector = get_experience_collector()
        self.graph = get_knowledge_graph()
        self.registry = get_model_registry()
        self.review_engine = get_self_review_engine()
        self.research_engine = get_research_engine()
        self.reports = get_executive_reports()
        self.repo_watcher = get_repo_watcher()
        self.resource_monitor = get_resource_monitor()
        self.evolution = get_evolution_engine()
        self.evolution.register_subsystem("experience_collector", self.collector)
        self.evolution.register_subsystem("self_review", self.review_engine)
        self.evolution.register_subsystem("knowledge_graph", self.graph)
        self.evolution.register_subsystem("research", self.research_engine)
        self.evolution.register_subsystem("model_registry", self.registry)
        self.evolution.register_subsystem("resource_monitor", self.resource_monitor)
        self.evolution.register_subsystem("repo_watcher", self.repo_watcher)
        self.evolution.register_subsystem("reports", self.reports)
        self.evolution.register_subsystem("learners", None)
        self._background_started = False

    async def process(self, user_input: str) -> str:
        start = time.perf_counter()
        try:
            response = await self.master_agent.process(user_input)
            duration_ms = (time.perf_counter() - start) * 1000.0
            self.collector.record_task(
                task_id="",
                input_text=user_input,
                output_text=response,
                success=True,
                duration_ms=duration_ms,
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            self.collector.record_task(
                task_id="",
                input_text=user_input,
                output_text=str(exc),
                success=False,
                duration_ms=duration_ms,
            )
            raise

    async def start_background(self) -> None:
        if self._background_started:
            return
        self._background_started = True
        await self.research_engine.start()
        await self.evolution.start()
        logger.info("V7 background evolution started")

    async def stop_background(self) -> None:
        if not self._background_started:
            return
        self._background_started = False
        await self.research_engine.stop()
        await self.evolution.stop()
        logger.info("V7 background evolution stopped")

    async def reflect_on_task(self, task_id: str, description: str, result: Any, duration_ms: float, components: list[str] | None = None) -> dict[str, Any]:
        review = self.review_engine.review(task_id, description, result, duration_ms, components)
        return review.to_dict()

    def get_evolution_status(self) -> dict[str, Any]:
        return {
            "evolution_engine": self.evolution.get_state(),
            "model_registry": self.registry.get_stats(),
            "knowledge_graph": self.graph.get_stats(),
            "experience_insights": self.collector.get_insights(),
            "improvement_suggestions": self.review_engine.get_improvement_suggestions(),
            "resource_monitor": self.resource_monitor.get_latest().to_dict() if self.resource_monitor.get_latest() else {},
            "repo_watcher": {"watched_repos": len(self.repo_watcher.list_repos())},
        }

    def get_autonomous_status(self) -> dict[str, Any]:
        return {
            "running": self._background_started,
            "evolution": self.evolution.get_state(),
            "research_running": self.research_engine._running,
            "resource_monitor_running": self.resource_monitor._running,
        }


_orchestrator_instance: V7JarvisOrchestrator | None = None


def get_v7_orchestrator() -> V7JarvisOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = V7JarvisOrchestrator()
    return _orchestrator_instance


def reset_v7_orchestrator() -> None:
    global _orchestrator_instance
    _orchestrator_instance = None
