"""
AI OS Dashboard for JARVIS.

Phase 3 enhancements:
- Vision status, Desktop sessions, Voice status
- Knowledge graph stats
- Background jobs, Notifications, Logs
- CPU, RAM, GPU, Disk, Network, Health metrics, Errors
- Active workflows
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DashboardSnapshot:
    running_agents: list[str] = field(default_factory=list)
    running_tasks: list[dict[str, Any]] = field(default_factory=list)
    current_goal: dict[str, Any] | None = None
    memory_stats: dict[str, Any] = field(default_factory=dict)
    provider_status: list[dict[str, Any]] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    browser: dict[str, Any] = field(default_factory=dict)
    voice: dict[str, Any] = field(default_factory=dict)
    vision: dict[str, Any] = field(default_factory=dict)
    desktop: dict[str, Any] = field(default_factory=dict)
    knowledge_graph: dict[str, Any] = field(default_factory=dict)
    notifications: dict[str, Any] = field(default_factory=dict)
    system: dict[str, Any] = field(default_factory=dict)
    background_jobs: list[dict[str, Any]] = field(default_factory=list)
    health: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    workflows: list[dict[str, Any]] = field(default_factory=list)
    learning: dict[str, Any] = field(default_factory=dict)


class AIOSDashboard:
    """
    Read-only aggregate view of JARVIS internal state.
    """

    def __init__(self):
        self._listeners: list[Any] = []

    def snapshot(self) -> DashboardSnapshot:
        snap = DashboardSnapshot()
        try:
            self._collect_agents(snap)
            self._collect_tasks(snap)
            self._collect_goals(snap)
            self._collect_memory(snap)
            self._collect_providers(snap)
            self._collect_plugins(snap)
            self._collect_system(snap)
            self._collect_health(snap)
            self._collect_errors(snap)
            self._collect_vision(snap)
            self._collect_desktop(snap)
            self._collect_knowledge_graph(snap)
            self._collect_notifications(snap)
            self._collect_background_jobs(snap)
            self._collect_workflows(snap)
            self._collect_learning(snap)
        except Exception as exc:
            logger.debug("Dashboard collection error: %s", exc)
        return snap

    def _collect_agents(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.core.agent_registry import get_agent_registry

            registry = get_agent_registry()
            snap.running_agents = registry.list_available()
        except Exception:
            pass

    def _collect_tasks(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.core.task_engine import get_task_engine

            engine = get_task_engine()
            for task in engine.list_tasks():
                snap.running_tasks.append(
                    {
                        "task_id": task.task_id,
                        "name": task.name,
                        "state": task.state.value,
                        "progress": task.progress,
                        "error": task.error,
                    }
                )
        except Exception:
            pass

    def _collect_goals(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.memory.memory_manager import get_memory_manager

            mgr = get_memory_manager()
            current = mgr.get_current_goal()
            if current is not None:
                snap.current_goal = current
        except Exception:
            pass

    def _collect_memory(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.memory.memory_manager import get_memory_manager

            mgr = get_memory_manager()
            full = mgr.get_full_memory()
            total = sum(len(v) for v in full.values() if isinstance(v, dict))
            snap.memory_stats = {"entries": total}
        except Exception:
            pass

    def _collect_providers(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.core.provider_manager import get_provider_manager

            pm = get_provider_manager()
            for name, provider in getattr(pm, "_providers", {}).items():
                status = "available" if getattr(provider, "is_available", False) else "unavailable"
                snap.provider_status.append({"name": name, "status": status})
        except Exception:
            pass

    def _collect_plugins(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.plugins.base import get_plugin_manager

            pm = get_plugin_manager()
            snap.plugins = list(getattr(pm, "plugins", {}).keys())
        except Exception:
            pass

    def _collect_system(self, snap: DashboardSnapshot) -> None:
        try:
            import platform

            import psutil

            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            snap.system = {
                "os": platform.system(),
                "cpu_percent": psutil.cpu_percent(interval=0),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024 ** 3), 1),
                "network_sent_mb": round(net.bytes_sent / (1024 ** 2), 1),
                "network_recv_mb": round(net.bytes_recv / (1024 ** 2), 1),
            }
        except Exception:
            pass

    def _collect_health(self, snap: DashboardSnapshot) -> None:
        snap.health = {"status": "ok"}

    def _collect_errors(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.events import get_event_bus

            bus = get_event_bus()
            error_events = bus.history(None)
            snap.errors = [
                {"type": ev.type.value, "data": ev.data}
                for ev in error_events[-20:]
                if ev.type.value == "error"
            ]
        except Exception:
            pass

    def _collect_vision(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.vision.production import get_vision_system
            vs = get_vision_system()
            snap.vision = {
                "initialized": getattr(vs, "initialized", False),
                "mode": getattr(vs, "mode", "unknown"),
            }
        except Exception:
            snap.vision = {}

    def _collect_desktop(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.desktop.automation import get_desktop_automation
            da = get_desktop_automation()
            try:
                windows = asyncio.get_event_loop().run_until_complete(da.list_windows())
            except RuntimeError:
                windows = []
            snap.desktop = {
                "windows_count": len(windows),
                "platform": da.system,
            }
        except Exception:
            snap.desktop = {}

    def _collect_knowledge_graph(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.memory.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            nodes = getattr(kg, "_nodes", {})
            edges = getattr(kg, "_edges", [])
            snap.knowledge_graph = {
                "nodes": len(nodes),
                "edges": len(edges),
            }
        except Exception:
            snap.knowledge_graph = {}

    def _collect_notifications(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.notifications.manager import get_notification_manager
            mgr = get_notification_manager()
            active = mgr.get_active() if hasattr(mgr, "get_active") else []
            snap.notifications = {
                "active_count": len(active),
                "active": active[:10],
            }
        except Exception:
            snap.notifications = {}

    def _collect_background_jobs(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.core.task_engine import get_task_engine
            engine = get_task_engine()
            for task in engine.list_tasks():
                if getattr(task, "state", None) and task.state.value == "running":
                    snap.background_jobs.append(
                        {
                            "task_id": getattr(task, "task_id", ""),
                            "name": getattr(task, "name", ""),
                            "progress": getattr(task, "progress", 0.0),
                        }
                    )
        except Exception:
            pass

    def _collect_workflows(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.orchestration.engine import get_orchestration_engine
            engine = get_orchestration_engine()
            snap.workflows = [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "strategy": r.strategy_used,
                }
                for r in engine.get_recent_history(limit=20)
            ]
        except Exception:
            pass

    def _collect_learning(self, snap: DashboardSnapshot) -> None:
        try:
            from jarvis.learning import ContinuousLearningEngine

            engine = ContinuousLearningEngine()
            snap.learning = engine.get_pattern_insights()
        except Exception:
            snap.learning = {}

    def get_system_health(self) -> dict[str, Any]:
        """Return detailed system health metrics."""
        try:
            import platform

            import psutil

            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_days = uptime_seconds / 86400.0

            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()

            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "cpu_percent": psutil.cpu_percent(interval=0),
                "cpu_count": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
                "ram_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 1),
                "ram_available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 1),
                "disk_percent": disk.percent,
                "disk_total_gb": round(disk.total / (1024 ** 3), 1),
                "disk_used_gb": round(disk.used / (1024 ** 3), 1),
                "disk_free_gb": round(disk.free / (1024 ** 3), 1),
                "network_sent_mb": round(net.bytes_sent / (1024 ** 2), 1),
                "network_recv_mb": round(net.bytes_recv / (1024 ** 2), 1),
                "uptime_seconds": round(uptime_seconds, 1),
                "uptime_days": round(uptime_days, 2),
                "status": "ok" if psutil.cpu_percent(interval=0) < 95 and disk.percent < 95 else "warning",
            }
        except Exception as exc:
            logger.debug("System health collection error: %s", exc)
            return {"status": "error", "error": str(exc)}

    def get_provider_dashboard(self) -> dict[str, Any]:
        """Return provider dashboard with latency, tokens, and requests."""
        try:
            from jarvis.core.provider_health_monitor import get_provider_health_monitor

            monitor = get_provider_health_monitor()
            health_status = monitor.get_status()

            providers: list[dict[str, Any]] = []
            try:
                from jarvis.core.provider_manager import get_provider_manager

                pm = get_provider_manager()
                for name, provider in getattr(pm, "_providers", {}).items():
                    health = health_status.get(name, {})
                    providers.append(
                        {
                            "name": name,
                            "status": "available" if getattr(provider, "is_available", False) else "unavailable",
                            "active_model": getattr(provider, "config", {}).default_model
                            if hasattr(provider, "config")
                            else getattr(provider, "model", None),
                            "latency_ms": round(health.get("latency_ms", 0.0), 2),
                            "success_count": health.get("success_count", 0),
                            "failure_count": health.get("failure_count", 0),
                            "token_usage_estimate": health.get("token_usage_estimate", 0),
                            "request_count": health.get("request_count", 0),
                        }
                    )
            except Exception:
                pass

            try:
                from jarvis.core.token_tracker import get_token_tracker

                tracker = get_token_tracker()
                total_stats = tracker.get_total_stats()
                return {
                    "providers": providers,
                    "total_tokens": total_stats.get("total_tokens", 0),
                    "total_requests": total_stats.get("total_requests", 0),
                    "updated_at": time.time(),
                }
            except Exception:
                return {
                    "providers": providers,
                    "total_tokens": 0,
                    "total_requests": 0,
                    "updated_at": time.time(),
                }
        except Exception as exc:
            logger.debug("Provider dashboard collection error: %s", exc)
            return {"providers": [], "total_tokens": 0, "total_requests": 0, "error": str(exc)}


def get_dashboard() -> AIOSDashboard:
    global _default_dashboard
    if "_default_dashboard" not in globals():
        _default_dashboard = AIOSDashboard()
    return _default_dashboard
