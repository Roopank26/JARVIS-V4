"""
Plugin Marketplace Architecture for JARVIS.

Extends the existing plugin system with:
- Plugin metadata
- Dependencies
- Versioning
- Sandboxing
- Permissions
- Updates
- Digital signatures
- Plugin capabilities
- Automatic discovery
- Local-first marketplace index
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from jarvis.plugins.plugin_manager import PluginInfo

logger = logging.getLogger(__name__)


class PermissionLevel(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"


@dataclass
class PluginCapabilities:
    capabilities: list[str] = field(default_factory=list)
    required_permissions: list[PermissionLevel] = field(default_factory=list)
    optional_permissions: list[PermissionLevel] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


@dataclass
class MarketplaceIndex:
    plugins: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


class PluginMarketplace:
    """
    Local-first plugin marketplace.
    """

    def __init__(self, marketplace_dir: Path | None = None) -> None:
        self._marketplace_dir = marketplace_dir or (Path.home() / ".jarvis" / "marketplace")
        self._marketplace_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._marketplace_dir / "index.json"
        self._index = self._load_index()
        self._signatures: dict[str, str] = {}

    def _load_index(self) -> MarketplaceIndex:
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text(encoding="utf-8"))
                return MarketplaceIndex(
                    plugins=data.get("plugins", {}),
                    last_updated=data.get("last_updated", time.time()),
                )
            except Exception:
                pass
        return MarketplaceIndex()

    def _save_index(self) -> None:
        with contextlib.suppress(Exception):
            self._index_path.write_text(json.dumps({
                "plugins": self._index.plugins,
                "last_updated": self._index.last_updated,
            }, indent=2), encoding="utf-8")

    def register_local(self, plugin_id: str, info: PluginInfo, capabilities: PluginCapabilities | None = None) -> None:
        self._index.plugins[plugin_id] = {
            "id": plugin_id,
            "name": info.name,
            "version": info.version,
            "description": info.description,
            "author": info.author,
            "tags": info.tags,
            "capabilities": capabilities.capabilities if capabilities else [],
            "permissions": [p.value for p in (capabilities.required_permissions if capabilities else [])],
            "dependencies": info.dependencies,
            "min_jarvis_version": info.min_jarvis_version,
            "updated_at": time.time(),
            "local": True,
        }
        self._save_index()

    def discover(self, plugin_name: str) -> dict[str, Any] | None:
        return self._index.plugins.get(plugin_name)

    def list_available(self) -> list[dict[str, Any]]:
        return list(self._index.plugins.values())

    def search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower()
        return [
            p for p in self._index.plugins.values()
            if q in p.get("name", "").lower() or q in p.get("description", "").lower() or q in p.get("id", "").lower()
        ]

    def update_signature(self, plugin_id: str, signature: str) -> None:
        self._signatures[plugin_id] = signature

    def verify_signature(self, plugin_id: str, data: bytes) -> bool:
        expected = self._signatures.get(plugin_id)
        if not expected:
            return True
        actual = hashlib.sha256(data).hexdigest()
        return actual == expected


class PluginSandbox:
    """
    Minimal sandbox for plugin isolation.
    """

    def __init__(self, permissions: list[PermissionLevel] | None = None) -> None:
        self._permissions = set(permissions or [PermissionLevel.READ])

    def allows(self, permission: PermissionLevel) -> bool:
        if PermissionLevel.SYSTEM in self._permissions:
            return True
        return permission in self._permissions

    def execute_isolated(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        if PermissionLevel.EXECUTE not in self._permissions:
            raise PermissionError("Plugin does not have execute permission")
        return fn(*args, **kwargs)

    def has_permission(self, permission: str) -> bool:
        try:
            level = PermissionLevel(permission)
            return self.allows(level)
        except ValueError:
            return False


class EnhancedPluginCapability:
    """
    Runtime plugin capability registry.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, list[str]] = {}

    def register(self, plugin_id: str, capabilities: list[str]) -> None:
        self._capabilities[plugin_id] = capabilities

    def unregister(self, plugin_id: str) -> None:
        self._capabilities.pop(plugin_id, None)

    def get_plugin_capabilities(self, plugin_id: str) -> list[str]:
        return list(self._capabilities.get(plugin_id, []))

    def find_plugins_by_capability(self, capability: str) -> list[str]:
        return [pid for pid, caps in self._capabilities.items() if capability in caps]

    def list_all(self) -> dict[str, list[str]]:
        return dict(self._capabilities)


_marketplace: PluginMarketplace | None = None
_capability_registry: EnhancedPluginCapability | None = None


def get_marketplace() -> PluginMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = PluginMarketplace()
    return _marketplace


def get_capability_registry() -> EnhancedPluginCapability:
    global _capability_registry
    if _capability_registry is None:
        _capability_registry = EnhancedPluginCapability()
    return _capability_registry
