"""
JARVIS Phase 4 — Runtime Manager.

Unified Operating System Runtime responsible for the lifecycle of every subsystem.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jarvis.core.master_agent import create_master_agent
from jarvis.events import EventType, get_event_bus

logger = logging.getLogger(__name__)


class SubsystemState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class SubsystemRecord:
    name: str
    state: SubsystemState = SubsystemState.STOPPED
    dependencies: list[str] = field(default_factory=list)
    instance: Any = None
    last_health_check: float = 0.0
    error: str | None = None
    restart_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeSnapshot:
    running: bool = False
    uptime_seconds: float = 0.0
    subsystems: dict[str, SubsystemState] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    health: dict[str, Any] = field(default_factory=dict)


class RuntimeManager:
    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._subsystems: dict[str, SubsystemRecord] = {}
        self._running = False
        self._start_time: float = 0.0
        self._monitor_task: asyncio.Task | None = None
        self._interrupt = asyncio.Event()
        self._register_defaults()

    def _register_defaults(self) -> None:
        builtins = [
            ("master_agent", []),
            ("planner", ["master_agent"]),
            ("provider_manager", []),
            ("browser", []),
            ("desktop", []),
            ("vision", []),
            ("memory", []),
            ("knowledge_graph", ["memory"]),
            ("research", ["master_agent"]),
            ("learning", ["memory"]),
            ("skills", ["master_agent"]),
            ("plugins", ["master_agent"]),
            ("voice", ["master_agent"]),
            ("dashboard", ["memory", "browser", "desktop", "voice", "vision"]),
            ("orchestration", ["master_agent", "planner"]),
            ("background", []),
            ("scheduler", []),
            ("diagnostics", []),
        ]
        for name, deps in builtins:
            self._subsystems[name] = SubsystemRecord(name=name, dependencies=deps)

    def register_subsystem(self, name: str, dependencies: list[str] | None = None) -> None:
        deps = dependencies or []
        self._subsystems.setdefault(name, SubsystemRecord(name=name, dependencies=deps))

    def get_subsystem(self, name: str) -> SubsystemRecord | None:
        return self._subsystems.get(name)

    def set_instance(self, name: str, instance: Any) -> None:
        if name in self._subsystems:
            self._subsystems[name].instance = instance

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.perf_counter()
        self._interrupt.clear()

        self._bus.emit(EventType.STATUS, {"runtime": "starting", "phase": "initialization"})

        ordered = self._topological_sort()
        for name in ordered:
            await self._start_subsystem(name)

        self._bus.emit(EventType.STATUS, {"runtime": "running", "phase": "active"})
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._interrupt.set()

        self._bus.emit(EventType.STATUS, {"runtime": "stopping", "phase": "shutdown"})

        if self._monitor_task is not None:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None

        ordered = list(reversed(self._topological_sort()))
        for name in ordered:
            await self._stop_subsystem(name)

        self._bus.emit(EventType.STATUS, {"runtime": "stopped", "phase": "offline"})

    async def restart(self, name: str | None = None) -> None:
        if name:
            await self._restart_subsystem(name)
        else:
            await self.stop()
            await asyncio.sleep(0.5)
            await self.start()

    async def health_check(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name, record in self._subsystems.items():
            try:
                instance = record.instance
                healthy = False
                detail = "no_instance"
                if instance is None and record.state == SubsystemState.RUNNING:
                    detail = "uninitialized"
                elif instance is not None and hasattr(instance, "health_check"):
                    result = instance.health_check()
                    if asyncio.iscoroutine(result):
                        result = await result
                    if isinstance(result, dict):
                        healthy = result.get("healthy", False) or result.get("status") == "ok"
                        detail = result
                    else:
                        healthy = bool(result)
                        detail = "ok" if healthy else "unhealthy"
                elif instance is not None and hasattr(instance, "is_available"):
                    healthy = bool(instance.is_available())
                    detail = "ok" if healthy else "unavailable"
                else:
                    detail = "unknown"
                    healthy = record.state == SubsystemState.RUNNING

                record.last_health_check = time.perf_counter()
                results[name] = {
                    "state": record.state.value,
                    "healthy": healthy,
                    "detail": detail,
                    "error": record.error,
                    "restart_count": record.restart_count,
                }
            except Exception as exc:
                record.error = str(exc)
                results[name] = {
                    "state": record.state.value,
                    "healthy": False,
                    "detail": "exception",
                    "error": str(exc),
                }
        return results

    def snapshot(self) -> RuntimeSnapshot:
        snap = RuntimeSnapshot(
            running=self._running,
            uptime_seconds=time.perf_counter() - self._start_time if self._running else 0,
        )
        for name, record in self._subsystems.items():
            snap.subsystems[name] = record.state.value
            if record.error:
                snap.errors.append({"name": name, "error": record.error})
        return snap

    async def get_subsystem_instance(self, name: str) -> Any | None:
        record = self._subsystems.get(name)
        if record is None:
            return None
        if record.instance is None and record.state == SubsystemState.RUNNING:
            await self._start_subsystem(name)
            record = self._subsystems.get(name)
        return record.instance if record else None

    def _topological_sort(self) -> list[str]:
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        for name, record in self._subsystems.items():
            graph[name] = list(record.dependencies)
            in_degree[name] = len(record.dependencies)

        queue = [name for name in self._subsystems if in_degree[name] == 0]
        result: list[str] = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for name, _record in self._subsystems.items():
                if node in graph[name]:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        return result

    async def _start_subsystem(self, name: str) -> None:
        record = self._subsystems.get(name)
        if record is None:
            return

        try:
            record.state = SubsystemState.STARTING
            self._bus.emit(EventType.STATUS, {"subsystem": name, "state": "starting"})

            if record.instance is None:
                record.instance = await self._instantiate(name)

            if record.instance is not None and hasattr(record.instance, "start"):
                result = record.instance.start()
                if asyncio.iscoroutine(result):
                    await result

            record.state = SubsystemState.RUNNING
            record.last_health_check = time.perf_counter()
            record.error = None
            self._bus.emit(EventType.STATUS, {"subsystem": name, "state": "running"})
        except Exception as exc:
            record.state = SubsystemState.ERROR
            record.error = str(exc)
            self._bus.emit(EventType.ERROR, {"subsystem": name, "error": str(exc)})

    async def _stop_subsystem(self, name: str) -> None:
        record = self._subsystems.get(name)
        if record is None:
            return

        try:
            record.state = SubsystemState.STOPPING
            self._bus.emit(EventType.STATUS, {"subsystem": name, "state": "stopping"})

            instance = record.instance
            if instance is not None:
                if hasattr(instance, "shutdown"):
                    result = instance.shutdown()
                    if asyncio.iscoroutine(result):
                        await result
                elif hasattr(instance, "stop"):
                    result = instance.stop()
                    if asyncio.iscoroutine(result):
                        await result

            record.state = SubsystemState.STOPPED
            record.error = None
            record.instance = None
            self._bus.emit(EventType.STATUS, {"subsystem": name, "state": "stopped"})
        except Exception as exc:
            record.error = str(exc)
            self._bus.emit(EventType.ERROR, {"subsystem": name, "error": str(exc)})

    async def _restart_subsystem(self, name: str) -> None:
        record = self._subsystems.get(name)
        if record is None:
            return
        await self._stop_subsystem(name)
        await self._start_subsystem(name)
        record.restart_count += 1

    async def _instantiate(self, name: str) -> Any | None:
        factories = {
            "master_agent": _factory_master_agent,
            "orchestration": _factory_orchestration,
            "planner": _factory_planner,
            "provider_manager": _factory_provider_manager,
            "browser": _factory_browser,
            "desktop": _factory_desktop,
            "vision": _factory_vision,
            "memory": _factory_memory,
            "knowledge_graph": _factory_knowledge_graph,
            "research": _factory_research,
            "learning": _factory_learning,
            "skills": _factory_skills,
            "plugins": _factory_plugins,
            "voice": _factory_voice,
            "dashboard": _factory_dashboard,
            "background": _factory_background,
            "scheduler": _factory_scheduler,
            "diagnostics": _factory_diagnostics,
        }
        factory = factories.get(name)
        if factory is None:
            return None
        try:
            instance = factory()
            if asyncio.iscoroutine(instance):
                instance = await instance
            return instance
        except Exception as exc:
            logger.debug("Failed to instantiate %s: %s", name, exc)
            return None

    async def _monitor_loop(self) -> None:
        while self._running and not self._interrupt.is_set():
            try:
                await asyncio.sleep(30)
                if not self._running:
                    break
                await self._run_monitoring()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Monitor loop error: %s", exc)

    async def _run_monitoring(self) -> None:
        try:
            health = await self.health_check()
            unhealthy = [name for name, result in health.items() if not result.get("healthy", False)]
            if unhealthy:
                self._bus.emit(EventType.STATUS, {"health_warnings": unhealthy})
                for name in unhealthy:
                    record = self._subsystems.get(name)
                    if record and record.restart_count < 3:
                        await self._restart_subsystem(name)
        except Exception:
            pass

    async def shutdown(self) -> None:
        await self.stop()


def _factory_master_agent():
    return create_master_agent()


def _factory_orchestration():
    from jarvis.orchestration.engine import get_orchestration_engine
    return get_orchestration_engine()


def _factory_planner():
    from jarvis.core.planner import Planner
    return Planner()


def _factory_provider_manager():
    try:
        from jarvis.core.provider_manager import get_provider_manager
        return get_provider_manager()
    except Exception:
        return None


def _factory_browser():
    try:
        from jarvis.browser.manager import get_browser_manager
        return get_browser_manager()
    except Exception:
        try:
            from jarvis.browser.manager import PersistentBrowserManager
            return PersistentBrowserManager()
        except Exception:
            return None


def _factory_desktop():
    from jarvis.desktop.automation import get_desktop_automation
    return get_desktop_automation()


def _factory_vision():
    try:
        from jarvis.vision.production import get_vision_system
        return get_vision_system()
    except Exception:
        return None


def _factory_memory():
    from jarvis.memory.memory_manager import get_memory_manager
    return get_memory_manager()


def _factory_knowledge_graph():
    try:
        from jarvis.memory.knowledge_graph import get_knowledge_graph
        return get_knowledge_graph()
    except Exception:
        return None


def _factory_research():
    try:
        from jarvis.research.agent import get_research_agent
        return get_research_agent()
    except Exception:
        return None


def _factory_learning():
    try:
        from jarvis.learning.engine import ContinuousLearningEngine
        return ContinuousLearningEngine()
    except Exception:
        return None


def _factory_skills():
    try:
        from jarvis.skills.manager import get_skill_manager
        return get_skill_manager()
    except Exception:
        return None


def _factory_plugins():
    from jarvis.plugins.plugin_manager import get_plugin_manager
    return get_plugin_manager()


def _factory_voice():
    try:
        from jarvis.voice.engine import get_voice_engine
        return get_voice_engine()
    except Exception:
        return None


def _factory_dashboard():
    from jarvis.core.dashboard import get_dashboard
    return get_dashboard()


def _factory_background():
    from jarvis.background.tasks import BackgroundIntelligence
    return BackgroundIntelligence()


def _factory_scheduler():
    from jarvis.services.scheduler import TaskScheduler
    return TaskScheduler()


def _factory_diagnostics():
    try:
        from jarvis.diagnostics import DiagnosticRunner
        return DiagnosticRunner()
    except Exception:
        return None


_runtime_manager: RuntimeManager | None = None


def get_runtime_manager() -> RuntimeManager:
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = RuntimeManager()
    return _runtime_manager


def reset_runtime_manager() -> None:
    global _runtime_manager
    _runtime_manager = None
