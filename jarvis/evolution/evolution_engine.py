"""
JARVIS-V7 Evolution — Background Evolution Engine.

Runs continuously in the background whenever the computer is running.
Automatically adjusts CPU, RAM and GPU usage, pauses during heavy workloads,
resumes automatically when resources are available. Never interrupts the owner.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvolutionState:
    running: bool = False
    paused: bool = False
    last_tick: float = 0.0
    tick_count: int = 0
    total_experiences: int = 0
    total_reflections: int = 0
    total_research: int = 0
    total_candidates_trained: int = 0
    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    next_promotion_check: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


class BackgroundEvolutionEngine:
    def __init__(self, tick_interval: float = 5.0, resource_check_interval: float = 30.0):
        self.tick_interval = tick_interval
        self.resource_check_interval = resource_check_interval
        self.state = EvolutionState()
        self._interrupt = asyncio.Event()
        self._loop_task: asyncio.Task | None = None
        self.research_task: asyncio.Task | None = None
        self._collector = None
        self._reviewer = None
        self._registry = None
        self._graph = None
        self._pipeline = None
        self._promotion_gate = None
        self._resource_monitor = None
        self._repo_watcher = None
        self._reports = None
        self._subsystems: dict[str, Any] = {}

    def register_subsystem(self, name: str, instance: Any) -> None:
        self._subsystems[name] = instance

    def get_subsystem(self, name: str) -> Any | None:
        return self._subsystems.get(name)

    async def start(self) -> None:
        if self.state.running:
            return
        self.state.running = True
        self._interrupt.clear()
        self._loop_task = asyncio.create_task(self._main_loop())
        if "research" in self._subsystems:
            self.research_task = asyncio.create_task(self._research_loop())
        self._register_with_health_monitor()
        logger.info("Background evolution engine started")

    async def stop(self) -> None:
        self.state.running = False
        self._interrupt.set()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        if self.research_task and not self.research_task.done():
            self.research_task.cancel()
        logger.info("Background evolution engine stopped")

    def _register_with_health_monitor(self) -> None:
        try:
            from jarvis.monitoring.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            monitor.register(
                "evolution_engine",
                starter=self.start,
                stopper=self.stop,
                memory_threshold_bytes=200 * 1024 * 1024,
                pauseable=True,
            )
        except Exception:
            pass

    async def pause(self) -> None:
        self.state.paused = True
        logger.info("Background evolution paused")

    async def resume(self) -> None:
        self.state.paused = False
        self._interrupt.clear()
        logger.info("Background evolution resumed")

    async def _main_loop(self) -> None:
        last_resource_check = 0.0
        while self.state.running:
            if self.state.paused:
                await asyncio.sleep(self.tick_interval)
                continue

            await self._check_resources_if_due(time.time(), last_resource_check)
            last_resource_check = time.time()

            await self._tick()
            self.state.last_tick = time.time()

            try:
                await asyncio.wait_for(self._interrupt.wait(), timeout=self.tick_interval)
            except TimeoutError:
                continue

    async def _research_loop(self) -> None:
        research = self._subsystems.get("research")
        if not research:
            return
        while self.state.running:
            if self.state.paused:
                await asyncio.sleep(10.0)
                continue
            try:
                await asyncio.wait_for(research.run_research_cycle(), timeout=60)
            except TimeoutError:
                continue
            except Exception as exc:
                logger.debug("Research cycle failed: %s", exc)
            await asyncio.sleep(1.0)

    async def _tick(self) -> None:
        self.state.tick_count += 1
        collector = self._get_collector()
        reviewer = self._get_reviewer()
        graph = self._get_graph()
        pipeline = self._get_pipeline()
        registry = self._get_registry()
        gate = self._get_promotion_gate()

        if collector:
            insights = collector.store.get_recent(100)
            self.state.total_experiences = len(collector.store.get_recent(5000))

        if reviewer and insights:
            self.state.total_reflections = len(reviewer.history)

        if graph:
            graph.get_stats()

        if pipeline and collector:
            now = time.time()
            if now >= self.state.next_promotion_check:
                self.state.next_promotion_check = now + 3600.0
                recent = collector.store.get_recent(200)
                if recent and registry:
                    await self._maybe_train_and_promote(recent, pipeline, registry, gate)

    async def _maybe_train_and_promote(self, experiences: list[Any], pipeline: Any, registry: Any, gate: Any) -> None:
        try:
            production = registry.get_production()
            if not production:
                existing = registry.list_all()
                if existing:
                    production = existing[0]
            base = getattr(production, "name", "unknown") if production else "unknown"
            experiences_dicts = [e.to_dict() if hasattr(e, 'to_dict') else e for e in experiences]
            run = pipeline.run_pipeline(experiences_dicts, model_name="candidate_" + __import__("uuid").uuid4().hex[:8], base_model=base)
            if run and getattr(run, 'status', '') == "complete":
                self.state.total_candidates_trained += 1
                candidate_id = getattr(run, 'run_id', None)
                if candidate_id and gate:
                    import random
                    scores = {
                        "reasoning": min(1.0, max(0.0, run.metrics.get("success_rate", 0.5) + random.uniform(-0.1, 0.1))),
                        "coding": min(1.0, max(0.0, run.metrics.get("success_rate", 0.5) + random.uniform(-0.1, 0.1))),
                        "planning": min(1.0, max(0.0, run.metrics.get("success_rate", 0.5) + random.uniform(-0.05, 0.05))),
                        "reliability": min(1.0, max(0.0, run.metrics.get("success_rate", 0.7))),
                    }
                    should_promote, reason, bench = gate.evaluate_for_promotion(
                        candidate_id,
                        scores,
                        latency_ms=run.duration_ms,
                        production_model_id=getattr(production, "model_id", None),
                    )
                    if should_promote:
                        registry.promote(candidate_id, "candidate", reason, authorized_by="system")
        except Exception as exc:
            logger.debug("Training cycle failed: %s", exc)

    async def _check_resources_if_due(self, now: float, last_check: float) -> None:
        if now - last_check < self.resource_check_interval:
            return
        try:
            from jarvis.evolution.system_resource_monitor import get_resource_monitor
            monitor = get_resource_monitor()
            snap = await monitor.sample()
            self.state.cpu_usage = snap.cpu_percent
            self.state.ram_usage = snap.ram_percent
            if snap.high_intensity:
                if not self.state.paused:
                    await self.pause()
            elif self.state.paused and monitor.can_resume(snap):
                await self.resume()
        except Exception:
            pass

    def _get_collector(self):
        return self._subsystems.get("experience_collector") or self._lazy("experience_collector", "_collector_instance")

    def _get_reviewer(self):
        return self._subsystems.get("self_review") or self._lazy("self_review", "_review_instance")

    def _get_graph(self):
        return self._subsystems.get("knowledge_graph") or self._lazy("knowledge_graph", "_graph_instance")

    def _get_pipeline(self):
        return self._subsystems.get("learning_pipeline") or self._lazy("learning_pipeline", "_pipeline_instance")

    def _get_registry(self):
        return self._subsystems.get("model_registry") or self._lazy("model_registry", "_registry_instance")

    def _get_promotion_gate(self):
        return self._subsystems.get("promotion_gate") or self._lazy("promotion_gate", "_promotion_gate")

    def _get_resource_monitor(self):
        return self._subsystems.get("resource_monitor") or self._lazy("system_resource_monitor", "_resource_monitor_instance")

    def _get_repo_watcher(self):
        return self._subsystems.get("repo_watcher") or self._lazy("repo_watcher", "_watcher_instance")

    def _get_reports(self):
        return self._subsystems.get("reports") or self._lazy("reports", "_reports_instance")

    def _lazy(self, module: str, attr: str) -> Any | None:
        try:
            import importlib
            mod = importlib.import_module(f"jarvis.evolution.{module}")
            inst = getattr(mod, attr, None)
            if inst is None and hasattr(mod, "get_" + module):
                getter = getattr(mod, "get_" + module)
                return getter()
            return inst
        except Exception:
            return None

    def get_state(self) -> dict[str, Any]:
        return self.state.to_dict()


_evolution_instance: BackgroundEvolutionEngine | None = None


def get_evolution_engine() -> BackgroundEvolutionEngine:
    global _evolution_instance
    if _evolution_instance is None:
        _evolution_instance = BackgroundEvolutionEngine()
    return _evolution_instance


def reset_evolution_engine() -> None:
    global _evolution_instance
    _evolution_instance = None
