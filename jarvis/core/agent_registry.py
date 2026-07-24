"""
Agent Registry for JARVIS.

Mirrors the ToolRegistry pattern but for specialist agents:
- Dynamic registration
- Lazy loading
- Metadata (capabilities, dependencies, version)
- Health monitoring
- Automatic discovery
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentMetadata:
    """Metadata for a registered agent."""

    name: str
    description: str
    module_path: str
    factory: str
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    enabled: bool = True
    health: str = "unknown"


class AgentRegistry:
    """
    Central registry for JARVIS specialist agents.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentMetadata] = {}
        self._instances: dict[str, Any] = {}
        self._callbacks: list[Callable[[str, str], None]] = []

    def register(
        self,
        name: str,
        description: str,
        module_path: str,
        factory: str,
        capabilities: list[str] | None = None,
        dependencies: list[str] | None = None,
        version: str = "1.0.0",
        enabled: bool = True,
    ) -> None:
        """Register an agent by metadata."""
        self._agents[name] = AgentMetadata(
            name=name,
            description=description,
            module_path=module_path,
            factory=factory,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            version=version,
            enabled=enabled,
        )
        self._notify(name, "registered")

    def register_function(self, name: str, fn: Callable, metadata: dict[str, Any]) -> None:
        self._agents[name] = AgentMetadata(
            name=name,
            description=metadata.get("description", ""),
            module_path=metadata.get("module_path", ""),
            factory=metadata.get("factory", ""),
            capabilities=metadata.get("capabilities", []),
            dependencies=metadata.get("dependencies", []),
            version=metadata.get("version", "1.0.0"),
            enabled=metadata.get("enabled", True),
        )
        self._instances[name] = fn
        self._notify(name, "registered_function")

    def get(self, name: str) -> Any:
        """Get an agent instance by name."""
        if name not in self._agents:
            return None
        if name in self._instances:
            return self._instances[name]
        return self._load(name)

    def get_metadata(self, name: str) -> AgentMetadata | None:
        """Get agent metadata without instantiating."""
        return self._agents.get(name)

    def list_names(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def list_available(self) -> list[str]:
        """List enabled agents."""
        return [name for name, meta in self._agents.items() if meta.enabled]

    def search(self, query: str) -> list[AgentMetadata]:
        """Search agents by name or description."""
        q = query.lower()
        return [
            meta
            for meta in self._agents.values()
            if q in meta.name.lower() or q in meta.description.lower()
        ]

    def unregister(self, name: str) -> bool:
        if name not in self._agents:
            return False
        self._agents.pop(name, None)
        self._instances.pop(name, None)
        self._notify(name, "unregistered")
        return True

    def set_health(self, name: str, health: str) -> None:
        if name in self._agents:
            self._agents[name].health = health

    def add_callback(self, callback: Callable[[str, str], None]) -> None:
        self._callbacks.append(callback)

    def _load(self, name: str) -> Any:
        meta = self._agents[name]
        try:
            module = importlib.import_module(meta.module_path)
            factory = getattr(module, meta.factory, None)
            if factory is None:
                logger.warning("Agent factory %s not found in %s", meta.factory, meta.module_path)
                return None
            instance = factory() if callable(factory) else factory
            self._instances[name] = instance
            meta.health = "ok"
            self._notify(name, "loaded")
            return instance
        except Exception as exc:
            logger.warning("Failed to load agent %s: %s", name, exc)
            meta.health = f"error: {exc}"
            return None

    def _notify(self, name: str, event: str) -> None:
        for callback in self._callbacks:
            try:
                callback(name, event)
            except Exception as exc:
                logger.debug("Agent registry callback error: %s", exc)

    def auto_discover(self) -> int:
        discovered = 0
        for name in list(self._agents.keys()):
            if self._agents[name].health == "unknown":
                self.get(name)
                discovered += 1
        return discovered


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _default_registry
    if "_default_registry" not in globals():
        _default_registry = AgentRegistry()
    return _default_registry


def register_builtin_agents(registry: AgentRegistry | None = None) -> None:
    """Register built-in agents."""
    reg = registry or get_agent_registry()
    try:
        reg.register(
            name="research",
            description="Web research and multi-source monitoring",
            module_path="jarvis.research.research_agent",
            factory="get_research_agent",
            capabilities=["web_search", "citation", "monitoring"],
            dependencies=["requests"],
        )
    except Exception:
        logger.debug("Research agent registration skipped", exc_info=True)

    try:
        reg.register(
            name="vscode",
            description="VS Code bridge for editor integration",
            module_path="jarvis.coding.vscode_bridge",
            factory="get_vscode_bridge",
            capabilities=["editor", "workspace"],
            dependencies=[],
        )
    except Exception:
        logger.debug("VS Code bridge registration skipped", exc_info=True)

    try:
        reg.register(
            name="coding",
            description="Coding agent for repository analysis",
            module_path="jarvis.coding.coding_agent",
            factory="get_coding_agent",
            capabilities=["repo_analysis", "ast", "security_scan"],
            dependencies=["astroid"],
        )
    except Exception:
        logger.debug("Coding agent registration skipped", exc_info=True)
