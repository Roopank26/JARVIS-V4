"""
JARVIS Capability Discovery Engine
===================================
Single responsibility: Event-driven discovery of capabilities across
ToolRegistry, PluginManager, MCPRegistry, and ProviderManager.

Event-Driven Architecture:
- Subscribes to EventBus for:
    • EventType.PLUGIN (plugin installed/removed/enabled/disabled)
    • EventType.TOOL (tool registered/removed)
    • EventType.PROVIDER_AVAILABLE / PROVIDER_UNAVAILABLE
    • EventType.TASK / EventType.STATUS
- Automatically refreshes CapabilityCatalog when events fire. Zero restart required.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventType, JarvisEvent, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class CapabilityInfo:
    """
    Complete metadata describing a single capability.
    Enables versioning, compatibility checks, and plugin upgrades.
    """

    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    permissions: str = "automatic"  # "automatic" | "ask_once" | "ask_always"
    dependencies: list[str] = field(default_factory=list)
    provider_requirements: list[str] = field(default_factory=list)
    priority: int = 50  # 0-100 score
    category: str = "general"
    status: str = "ready"
    availability: bool = True
    tags: list[str] = field(default_factory=list)
    compatibility: str = ">=4.0.0"
    minimum_compatibility: str = "4.0.0"
    breaking_changes: list[str] = field(default_factory=list)
    source: str = "tool_registry"  # "tool_registry" | "plugin" | "mcp" | "provider"
    keywords: list[str] = field(default_factory=list)

    def matches_text(self, text: str) -> bool:
        """Check if capability matches text based on metadata."""
        text_lower = text.lower()
        if any(alias.lower() in text_lower for alias in self.aliases):
            return True
        return any(kw.lower() in text_lower for kw in self.keywords)

    def to_prompt_line(self) -> str:
        status_tag = "[+]" if self.availability else "[-]"
        reqs = f" (requires: {', '.join(self.provider_requirements)})" if self.provider_requirements else ""
        return f"  {status_tag} {self.name} (v{self.version}): {self.description}{reqs}"


@dataclass
class CapabilityCatalog:
    """
    Single source of truth for all discovered capabilities.
    """

    capabilities: list[CapabilityInfo] = field(default_factory=list)

    def get_available(self) -> list[CapabilityInfo]:
        return [c for c in self.capabilities if c.availability]

    def find_by_id(self, cap_id: str) -> CapabilityInfo | None:
        for c in self.capabilities:
            if c.id == cap_id or c.name == cap_id:
                return c
        return None

    def find_by_name(self, name: str) -> CapabilityInfo | None:
        return self.find_by_id(name)


class CapabilityDiscovery:
    """
    Event-driven capability discovery engine.
    """

    def __init__(self) -> None:
        self._tool_registry = None
        self._plugin_manager = None
        self._provider_manager = None
        self._catalog = CapabilityCatalog()
        self._bus = get_event_bus()
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Subscribe to EventBus for dynamic catalog auto-refresh."""
        for etype in [
            EventType.PLUGIN,
            EventType.TOOL,
            EventType.PROVIDER_AVAILABLE,
            EventType.PROVIDER_UNAVAILABLE,
            EventType.STATUS,
        ]:
            self._bus.subscribe(etype, self._on_system_event)

    def _on_system_event(self, event: JarvisEvent) -> None:
        """Auto-refresh catalog on subsystem changes."""
        logger.debug("[CapabilityDiscovery] Auto-refreshing catalog due to event: %s", event.type.value)
        self.refresh_catalog()

    def set_tool_registry(self, registry) -> None:
        self._tool_registry = registry

    def set_plugin_manager(self, manager) -> None:
        self._plugin_manager = manager

    def set_provider_manager(self, manager) -> None:
        self._provider_manager = manager

    def refresh_catalog(self) -> CapabilityCatalog:
        """Re-scan all subsystems and update the CapabilityCatalog."""
        catalog = CapabilityCatalog()
        catalog.capabilities.extend(self._discover_from_tools())
        catalog.capabilities.extend(self._discover_from_plugins())
        catalog.capabilities.extend(self._discover_from_mcp())
        catalog.capabilities.extend(self._discover_from_providers())
        self._catalog = catalog
        return self._catalog

    def discover_catalog(self) -> CapabilityCatalog:
        """Return the current CapabilityCatalog (refreshing if empty)."""
        if not self._catalog.capabilities:
            return self.refresh_catalog()
        return self._catalog

    def _discover_from_tools(self) -> list[CapabilityInfo]:
        caps: list[CapabilityInfo] = []
        if self._tool_registry is None:
            try:
                from jarvis.tools.registry import get_registry
                self._tool_registry = get_registry()
            except Exception:
                return caps

        for tool in self._tool_registry.get_all():
            name_words = tool.name.replace("_", " ").split()
            desc_words = [
                w.lower().strip(".,!?") for w in tool.description.split()
                if len(w) > 3
            ]
            keywords = list({*name_words, *desc_words, tool.name})

            tool_kws = getattr(tool, "KEYWORDS", [])
            if tool_kws:
                keywords.extend(tool_kws)

            perm = getattr(tool, "permission_level", None)
            perm_str = perm.value if perm else "automatic"
            reqs = getattr(tool, "provider_requirements", [])
            version = getattr(tool, "version", "1.0.0")

            caps.append(CapabilityInfo(
                id=tool.name,
                name=tool.name,
                version=version,
                description=tool.description,
                aliases=[tool.name.replace("_", " ")],
                examples=[f"Execute {tool.name}"],
                parameters=getattr(tool, "parameters", {}),
                permissions=perm_str,
                dependencies=[],
                provider_requirements=reqs,
                priority=60,
                category=getattr(tool, "category", "system"),
                status="ready",
                availability=True,
                tags=[tool.category] if hasattr(tool, "category") else ["tool"],
                compatibility=">=4.0.0",
                minimum_compatibility="4.0.0",
                breaking_changes=[],
                source="tool_registry",
                keywords=keywords,
            ))
        return caps

    def _discover_from_plugins(self) -> list[CapabilityInfo]:
        caps: list[CapabilityInfo] = []
        if self._plugin_manager is None:
            try:
                from jarvis.plugins.plugin_manager import get_plugin_manager
                self._plugin_manager = get_plugin_manager()
            except Exception:
                return caps

        for plugin_rec in self._plugin_manager.plugins.values():
            info = plugin_rec.info
            from jarvis.plugins.plugin_manager import PluginState
            avail = plugin_rec.state in (PluginState.LOADED, PluginState.INITIALIZED)
            caps.append(CapabilityInfo(
                id=info.id,
                name=info.id,
                version=getattr(info, "version", "1.0.0"),
                description=info.description,
                aliases=[info.name],
                examples=[f"Use plugin {info.name}"],
                permissions="automatic",
                priority=50,
                category="plugin",
                status=plugin_rec.state.value,
                availability=avail,
                tags=info.tags,
                compatibility=">=4.0.0",
                minimum_compatibility="4.0.0",
                source="plugin",
                keywords=info.tags + info.name.split(),
            ))
        return caps

    def _discover_from_mcp(self) -> list[CapabilityInfo]:
        caps: list[CapabilityInfo] = []
        try:
            from jarvis.integrations.mcp import get_mcp_registry  # type: ignore[import]
            registry = get_mcp_registry()
            for server_name, tools in registry.list_tools().items():
                for tool in tools:
                    mcp_id = f"mcp:{server_name}:{tool['name']}"
                    caps.append(CapabilityInfo(
                        id=mcp_id,
                        name=mcp_id,
                        version="1.0.0",
                        description=tool.get("description", ""),
                        aliases=[tool['name']],
                        category="mcp",
                        provider_requirements=[server_name],
                        availability=True,
                        source="mcp",
                        keywords=tool.get("name", "").replace("_", " ").split(),
                    ))
        except Exception:
            pass
        return caps

    def _discover_from_providers(self) -> list[CapabilityInfo]:
        caps: list[CapabilityInfo] = []
        if self._provider_manager is None:
            try:
                from jarvis.api.providers import get_provider_manager
                self._provider_manager = get_provider_manager()
            except Exception:
                return caps

        try:
            status_dict = self._provider_manager.get_status()
            for ptype, pinfo in status_dict.get("providers", {}).items():
                is_avail = pinfo.get("available", False)
                pid = f"provider:{ptype}"
                caps.append(CapabilityInfo(
                    id=pid,
                    name=pid,
                    version="1.0.0",
                    description=f"AI Provider ({ptype}) supporting completion and reasoning",
                    category="provider",
                    provider_requirements=[ptype],
                    availability=is_avail,
                    status="available" if is_avail else "unavailable",
                    source="provider",
                    keywords=[ptype, "llm", "ai", "model"],
                ))
        except Exception:
            pass
        return caps
