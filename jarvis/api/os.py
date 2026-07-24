"""
Unified API Layer for JARVIS.

One internal API for every subsystem.

Every module exposes:
- Capabilities
- Health
- Configuration
- Metrics
- Events
- Lifecycle

This becomes the internal operating system interface.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.runtime.manager import get_runtime_manager

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    name: str
    capabilities: list[str] = field(default_factory=list)
    health: str = "unknown"
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    lifecycle_state: str = "unknown"


class UnifiedAPI:
    """
    Single internal API for all JARVIS subsystems.
    """

    def __init__(self) -> None:
        self._modules: dict[str, ModuleInfo] = {}
        self._runtime = get_runtime_manager()

    def get_module_info(self, name: str) -> ModuleInfo | None:
        return self._modules.get(name)

    def list_modules(self) -> list[ModuleInfo]:
        return list(self._modules.values())

    async def capability(self, name: str) -> dict[str, Any]:
        info = self._modules.get(name)
        if info is None:
            return {"error": "module not found"}
        return {
            "name": info.name,
            "capabilities": info.capabilities,
            "health": info.health,
        }

    async def health(self, name: str | None = None) -> dict[str, Any]:
        if name:
            info = self._modules.get(name)
            if info is None:
                return {"error": "module not found"}
            return {"name": info.name, "health": info.health, "metrics": info.metrics}
        return {m.name: m.health for m in self._modules.values()}

    async def configure(self, name: str, config: dict[str, Any]) -> dict[str, Any]:
        info = self._modules.get(name)
        if info is None:
            return {"error": "module not found"}
        instance = await self._runtime.get_subsystem_instance(name)
        if instance is None:
            return {"error": "module not running"}
        if hasattr(instance, "configure"):
            try:
                result = instance.configure(config)
                if asyncio.iscoroutine(result):
                    result = await result
                info.config.update(config)
                return result if isinstance(result, dict) else {"status": "configured"}
            except Exception as exc:
                return {"error": str(exc)}
        info.config.update(config)
        return {"status": "configured"}

    async def metrics(self, name: str) -> dict[str, Any]:
        info = self._modules.get(name)
        if info is None:
            return {"error": "module not found"}
        return {"name": info.name, "metrics": info.metrics, "events": info.events}

    async def lifecycle(self, name: str, action: str) -> dict[str, Any]:
        instance = await self._runtime.get_subsystem_instance(name)
        if instance is None:
            return {"error": "module not running"}
        if action == "start":
            await self._runtime.start()
            return {"status": "started"}
        if action == "stop":
            await self._runtime.stop()
            return {"status": "stopped"}
        if action == "restart":
            await self._runtime.restart(name)
            return {"status": "restarted"}
        return {"error": f"Unknown action: {action}"}

    def register(self, name: str, instance: Any, capabilities: list[str] | None = None) -> None:
        caps = []
        health = "unknown"
        config: dict[str, Any] = {}
        metrics: dict[str, Any] = {}
        events: list[str] = []

        if capabilities:
            caps = capabilities
        elif hasattr(instance, "capabilities"):
            caps = instance.capabilities

        if hasattr(instance, "health_check"):
            try:
                hc = instance.health_check()
                if isinstance(hc, dict):
                    health = "ok" if hc.get("healthy", True) else "degraded"
                else:
                    health = "ok" if hc else "degraded"
            except Exception:
                health = "error"

        if hasattr(instance, "metrics"):
            metrics = instance.metrics

        if hasattr(instance, "get_events"):
            events = instance.get_events()

        info = ModuleInfo(
            name=name,
            capabilities=caps,
            health=health,
            config=config,
            metrics=metrics,
            events=events,
            lifecycle_state="active" if instance else "inactive",
        )
        self._modules[name] = info
        self._runtime.set_instance(name, instance)

    def snapshot(self) -> dict[str, Any]:
        return {
            "modules": {m.name: {
                "capabilities": m.capabilities,
                "health": m.health,
                "config": m.config,
                "metrics": m.metrics,
                "lifecycle_state": m.lifecycle_state,
            } for m in self._modules.values()},
            "runtime": self._runtime.snapshot().__dict__ if hasattr(self._runtime.snapshot(), "__dict__") else {},
        }

    async def dispatch(self, module: str, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        instance = await self._runtime.get_subsystem_instance(module)
        if instance is None:
            return {"error": "module not running"}
        fn = getattr(instance, method, None)
        if fn is None:
            return {"error": f"method {method} not found"}
        try:
            result = fn(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return {"result": result}
        except Exception as exc:
            return {"error": str(exc)}


_unified_api: UnifiedAPI | None = None


def get_unified_api() -> UnifiedAPI:
    global _unified_api
    if _unified_api is None:
        _unified_api = UnifiedAPI()
    return _unified_api


def reset_unified_api() -> None:
    global _unified_api
    _unified_api = None
