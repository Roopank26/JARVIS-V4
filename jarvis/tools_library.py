"""
Dynamic Tool Discovery / Tool Library for JARVIS (Feature 4).

Wraps the existing :class:`jarvis.tools.registry.ToolRegistry` and the plugin
manager to present a unified, auto-discovered Tool Library with search,
filter by category, favorites, and recently-used tracking. No backend changes —
it only reads from the registry and plugins that already exist.
"""

from __future__ import annotations

import builtins
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    name: str
    description: str
    category: str
    permission: str = "ask_once"
    source: str = "registry"  # "registry" or "plugin"
    plugin_id: str | None = None
    read_only: bool = False
    dangerous: bool = False
    used_at: float = 0.0
    favorite: bool = False


class ToolLibrary:
    """Auto-discovers and categorizes tools from registry + plugins."""

    FAVORITES_FILE = "tool_favorites.json"

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or get_event_bus()
        self._cache: dict[str, ToolEntry] = {}
        self._recent: list[str] = []

    def refresh(self) -> builtins.list[ToolEntry]:
        """Scan registry + plugins and rebuild the tool catalog."""
        tools: dict[str, ToolEntry] = {}

        # Registered tools
        try:
            from jarvis.tools.registry import get_registry

            registry = get_registry()
            for tool in registry.get_all():
                perm = registry.get_permission(tool.name)
                tools[tool.name] = ToolEntry(
                    name=tool.name,
                    description=tool.description or "",
                    category=getattr(tool, "category", "system") or "system",
                    permission=perm.value if perm else "ask_once",
                    source="registry",
                    read_only=getattr(tool, "is_read_only", False),
                    dangerous=getattr(tool, "is_dangerous", False),
                )
        except Exception as e:
            logger.debug(f"Tool registry scan skipped: {e}")

        # Plugin-provided tools
        try:
            from jarvis.plugins.plugin_manager import get_plugin_manager

            pm = get_plugin_manager()
            for defn in pm.get_tool_definitions():
                name = defn.get("name") or defn.get("tool")
                if not name:
                    continue
                tools[name] = ToolEntry(
                    name=name,
                    description=defn.get("description", ""),
                    category=defn.get("category", "plugin"),
                    source="plugin",
                    plugin_id=defn.get("plugin_id"),
                )
        except Exception as e:
            logger.debug(f"Plugin tool scan skipped: {e}")

        # Preserve favorites/recent from previous cache
        for name, entry in tools.items():
            prev = self._cache.get(name)
            if prev:
                entry.favorite = prev.favorite
                entry.used_at = prev.used_at

        self._cache = tools
        self.bus.emit(EventType.PLUGIN, {"action": "tools_discovered", "count": len(tools)})
        return self.list()

    def list(self) -> builtins.list[ToolEntry]:
        return list(self._cache.values())

    def get(self, name: str) -> ToolEntry | None:
        return self._cache.get(name)

    def categories(self) -> builtins.list[str]:
        seen = []
        for entry in self._cache.values():
            if entry.category not in seen:
                seen.append(entry.category)
        return seen

    def search(self, query: str, category: str | None = None) -> builtins.list[ToolEntry]:
        """Search tools by name/description; optionally filter by category."""
        q = (query or "").lower().strip()
        results = []
        for entry in self._cache.values():
            if category and entry.category != category:
                continue
            if not q:
                results.append(entry)
                continue
            if q in entry.name.lower() or q in entry.description.lower():
                results.append(entry)
        # Favorites + recency as soft ranking
        results.sort(key=lambda e: (not e.favorite, -e.used_at, e.name))
        return results

    def mark_used(self, name: str) -> None:
        entry = self._cache.get(name)
        if entry:
            entry.used_at = time.time()
        if name in self._recent:
            self._recent.remove(name)
        self._recent.insert(0, name)
        self._recent = self._recent[:20]

    def recent(self, limit: int = 8) -> builtins.list[ToolEntry]:
        out = []
        for name in self._recent:
            entry = self._cache.get(name)
            if entry:
                out.append(entry)
            if len(out) >= limit:
                break
        return out

    def toggle_favorite(self, name: str) -> bool:
        entry = self._cache.get(name)
        if entry is None:
            return False
        entry.favorite = not entry.favorite
        return entry.favorite

    def favorites(self) -> builtins.list[ToolEntry]:
        return [e for e in self._cache.values() if e.favorite]

    def to_dict(self) -> builtins.list[dict[str, Any]]:
        return [asdict(e) for e in self.list()]


# Global default library
_default_library: ToolLibrary | None = None


def get_tool_library() -> ToolLibrary:
    global _default_library
    if _default_library is None:
        _default_library = ToolLibrary()
    return _default_library


def reset_tool_library() -> None:
    global _default_library
    _default_library = None
