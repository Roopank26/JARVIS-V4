"""
Command Palette for JARVIS (Feature 5).

A single search index across commands, agents, plugins, files, models,
memory, settings, and history — Raycast/VS Code style. Built on top of the
existing backend modules (no backend changes); it only reads their state.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PaletteItem:
    id: str
    title: str
    category: str  # command | agent | plugin | file | model | memory | setting | history
    subtitle: str = ""
    action: str = ""  # e.g. "send:...", "run:...", "open:..."
    keywords: str = ""

    def matches(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        hay = f"{self.title} {self.subtitle} {self.keywords} {self.category}".lower()
        return q in hay


class CommandPalette:
    """Aggregates searchable items from across JARVIS."""

    def __init__(self) -> None:
        self._static: list[PaletteItem] = []
        self._history: list[PaletteItem] = []
        self._refresh_static()

    def _refresh_static(self) -> None:
        self._static = [
            PaletteItem("cmd.help", "Show help", "command", "Built-in commands and usage", "help"),
            PaletteItem("cmd.tools", "List tools", "command", "All registered tools", "tools"),
            PaletteItem(
                "cmd.status", "System status", "command", "Provider, memory, tasks", "status"
            ),
            PaletteItem(
                "cmd.memory", "Show memory", "command", "Stored long-term memory", "memory"
            ),
            PaletteItem("cmd.clear", "Clear conversation", "command", "Reset chat", "clear"),
            PaletteItem(
                "cmd.voice.on", "Start voice", "command", "Begin wake-word listening", "voice start"
            ),
            PaletteItem("cmd.voice.off", "Stop voice", "command", "Stop listening", "voice stop"),
            PaletteItem("cmd.research", "Research topic", "command", "Web research", "research"),
            PaletteItem(
                "cmd.index",
                "Index repository",
                "command",
                "Code analysis + indexing",
                "index repository",
            ),
            PaletteItem(
                "cmd.rag", "Ingest document", "command", "Add a PDF/doc to knowledge base", "ingest"
            ),
            PaletteItem("set.theme.dark", "Toggle dark mode", "setting", "UI theme", "theme dark"),
            PaletteItem(
                "set.theme.light", "Toggle light mode", "setting", "UI theme", "theme light"
            ),
            PaletteItem(
                "set.model",
                "Switch model",
                "setting",
                "Change active model/provider",
                "model switch provider",
            ),
            PaletteItem(
                "set.voice",
                "Voice settings",
                "setting",
                "Mic, thresholds, wake word",
                "voice config",
            ),
        ]

    # ---- Dynamic contributions ----
    def _agents(self) -> list[PaletteItem]:
        items: list[PaletteItem] = []
        try:
            from jarvis.agents.multi_agent import get_agent_coordinator

            coord = get_agent_coordinator()
            for a in getattr(coord, "agents", {}).values():
                name = getattr(a, "name", None) or getattr(a, "role", "agent")
                items.append(
                    PaletteItem(
                        f"agent.{name}",
                        f"Agent: {name}",
                        "agent",
                        getattr(a, "description", ""),
                        "agent",
                        action=f"agent:{name}",
                    )
                )
        except Exception:
            pass
        return items

    def _plugins(self) -> list[PaletteItem]:
        items: list[PaletteItem] = []
        try:
            from jarvis.plugins.plugin_manager import get_plugin_manager

            pm = get_plugin_manager()
            for p in pm.list_plugins():
                items.append(
                    PaletteItem(
                        f"plugin.{p['id']}",
                        f"Plugin: {p['name']}",
                        "plugin",
                        p.get("description", ""),
                        "plugin",
                        action=f"plugin:{p['id']}",
                    )
                )
        except Exception:
            pass
        return items

    def _models(self) -> list[PaletteItem]:
        items: list[PaletteItem] = []
        try:
            from jarvis.api.providers import get_provider_manager

            pm = get_provider_manager()
            provider = pm.providers.get(pm.primary_provider) if pm.primary_provider else None
            if provider:
                for m in provider.available_models:
                    items.append(
                        PaletteItem(
                            f"model.{m}",
                            f"Model: {m}",
                            "model",
                            provider.config.provider.value,
                            "model",
                            action=f"model:{m}",
                        )
                    )
        except Exception:
            pass
        return items

    def _memory(self) -> list[PaletteItem]:
        items: list[PaletteItem] = []
        try:
            from jarvis.core.agent import create_jarvis

            mem = create_jarvis.__self__ if hasattr(create_jarvis, "__self__") else None
        except Exception:
            pass
        try:
            from jarvis.memory.enhanced import get_enhanced_memory

            mem = get_enhanced_memory()
            for fact in getattr(mem, "memories", [])[:30]:
                key = (
                    getattr(fact, "key", None) or fact.get("key")
                    if isinstance(fact, dict)
                    else None
                )
                val = getattr(fact, "value", None) or (
                    fact.get("value") if isinstance(fact, dict) else None
                )
                if key:
                    items.append(
                        PaletteItem(
                            f"memory.{key}",
                            f"Memory: {key}",
                            "memory",
                            str(val)[:80] if val else "",
                            "memory",
                            action=f"recall:{key}",
                        )
                    )
        except Exception:
            pass
        return items

    def _files(self, root: str = ".", limit: int = 40) -> list[PaletteItem]:
        items: list[PaletteItem] = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip heavy/irrelevant dirs
                dirnames[:] = [
                    d
                    for d in dirnames
                    if d not in (".git", "__pycache__", "venv", "node_modules", ".ruff_cache")
                ]
                for fn in filenames:
                    if fn.endswith((".pyc",)):
                        continue
                    items.append(
                        PaletteItem(
                            f"file.{os.path.join(dirpath, fn)}",
                            fn,
                            "file",
                            os.path.join(dirpath, fn),
                            "file open",
                            action=f"open:{os.path.join(dirpath, fn)}",
                        )
                    )
                    if len(items) >= limit:
                        return items
        except Exception:
            pass
        return items

    def add_history(self, query: str) -> None:
        if not query.strip():
            return
        self._history.insert(
            0,
            PaletteItem(
                id=f"hist.{time.time()}",
                title=query,
                category="history",
                subtitle="Previous request",
                keywords="history",
                action=f"send:{query}",
            ),
        )
        self._history = self._history[:50]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search everything; returns ranked item dicts."""
        query = (query or "").strip()
        pool: list[PaletteItem] = []
        pool += self._static
        pool += self._history
        pool += self._agents()
        pool += self._plugins()
        pool += self._models()
        pool += self._memory()
        pool += self._files()

        # De-duplicate by id, keeping first occurrence (history over static)
        seen = set()
        unique: list[PaletteItem] = []
        for item in pool:
            if item.id in seen:
                continue
            seen.add(item.id)
            unique.append(item)

        matches = [i for i in unique if i.matches(query)]
        # Rank: history first for exact-ish, then by category priority
        cat_priority = {
            "history": 0,
            "command": 1,
            "agent": 2,
            "plugin": 3,
            "model": 4,
            "memory": 5,
            "file": 6,
            "setting": 7,
        }
        matches.sort(key=lambda i: (cat_priority.get(i.category, 9), i.title.lower()))
        return [asdict(i) for i in matches[:limit]]


# Global default palette
_default_palette: CommandPalette | None = None


def get_command_palette() -> CommandPalette:
    global _default_palette
    if _default_palette is None:
        _default_palette = CommandPalette()
    return _default_palette


def reset_command_palette() -> None:
    global _default_palette
    _default_palette = None
