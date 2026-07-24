"""
Capability Discovery Service.

Dynamically inventories JARVIS resources before planning:
- AI providers and models
- Available tools
- Plugins
- System dependencies (git, docker, node, java, cuda)
- Hardware (cpu, ram, gpu)
- OS and network
- Browser and services
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Capabilities:
    """Aggregated capability snapshot for planning context."""

    providers: list[dict[str, Any]] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    python_packages: list[str] = field(default_factory=list)
    system: dict[str, Any] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    services: dict[str, bool] = field(default_factory=dict)
    browser: dict[str, Any] = field(default_factory=dict)
    filesystem: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self, max_items: int = 40) -> str:
        lines: list[str] = ["[AVAILABLE CAPABILITIES — plan accordingly]"]
        if self.providers:
            lines.append("AI Providers:")
            for p in self.providers[: max_items // 3]:
                lines.append(f"  - {p.get('name', 'unknown')}: {p.get('status', 'unknown')}")
        if self.models:
            lines.append("Models:")
            for m in self.models[: max_items // 4]:
                lines.append(f"  - {m}")
        if self.tools:
            lines.append("Tools:")
            for t in self.tools[: max_items // 4]:
                lines.append(f"  - {t}")
        if self.plugins:
            lines.append("Plugins:")
            for p in self.plugins[: max_items // 5]:
                lines.append(f"  - {p}")
        if self.system:
            lines.append("System:")
            for k, v in list(self.system.items())[:10]:
                lines.append(f"  - {k}: {v}")
        if self.hardware:
            lines.append("Hardware:")
            for k, v in list(self.hardware.items())[:10]:
                lines.append(f"  - {k}: {v}")
        return "\n".join(lines) + "\n"


class CapabilityDiscovery:
    """Read-only capability inventory."""

    def __init__(self) -> None:
        self._cache: Capabilities | None = None

    async def discover(self, tool_registry=None, plugin_manager=None) -> Capabilities:
        if self._cache is not None:
            return self._cache
        caps = Capabilities()

        self._discover_providers(caps)
        self._discover_tools(caps, tool_registry)
        self._discover_plugins(caps, plugin_manager)
        self._discover_python_packages(caps)
        self._discover_system(caps)
        self._discover_hardware(caps)
        self._discover_services(caps)
        self._discover_browser(caps)
        self._discover_filesystem(caps)
        self._discover_network(caps)

        self._cache = caps
        return caps

    def invalidate_cache(self) -> None:
        self._cache = None

    def _discover_providers(self, caps: Capabilities) -> None:
        try:
            from jarvis.core.provider_manager import get_provider_manager

            pm = get_provider_manager()
            caps.providers = [
                {"name": name, "status": "configured"}
                for name in getattr(pm, "_providers", {})
            ]
            caps.models = list(getattr(pm, "_available_models", set()))
        except Exception:
            logger.debug("Provider discovery skipped", exc_info=True)

    def _discover_tools(self, caps: Capabilities, tool_registry=None) -> None:
        try:
            registry = tool_registry
            if registry is None:
                from jarvis.tools.registry import get_registry

                registry = get_registry()
            caps.tools = registry.list_names()
        except Exception:
            logger.debug("Tool discovery skipped", exc_info=True)

    def _discover_plugins(self, caps: Capabilities, plugin_manager=None) -> None:
        try:
            manager = plugin_manager
            if manager is None:
                from jarvis.plugins.base import get_plugin_manager

                manager = get_plugin_manager()
            caps.plugins = list(getattr(manager, "plugins", {}).keys())
        except Exception:
            logger.debug("Plugin discovery skipped", exc_info=True)

    def _discover_python_packages(self, caps: Capabilities) -> None:
        try:
            import importlib.metadata as metadata

            caps.python_packages = [
                dist.metadata["Name"]
                for dist in metadata.distributions()
                if dist.metadata.get("Name")
            ][:50]
        except Exception:
            logger.debug("Python package discovery skipped", exc_info=True)

    def _discover_system(self, caps: Capabilities) -> None:
        try:
            caps.system = {
                "os": platform.system(),
                "os_version": platform.version(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            }
            for name in ("git", "docker", "node", "java"):
                caps.system[f"{name}_installed"] = shutil.which(name) is not None
        except Exception:
            logger.debug("System discovery skipped", exc_info=True)

    def _discover_hardware(self, caps: Capabilities) -> None:
        try:
            caps.hardware = {
                "cpu_count": os.cpu_count(),
                "architecture": platform.machine(),
            }
            try:
                import psutil

                caps.hardware.update(
                    {
                        "memory_total_gb": round(
                            psutil.virtual_memory().total / (1024 ** 3), 1
                        ),
                        "memory_available_gb": round(
                            psutil.virtual_memory().available / (1024 ** 3), 1
                        ),
                        "cpu_percent": psutil.cpu_percent(interval=0),
                    }
                )
            except ImportError:
                caps.hardware["memory_detected"] = False
        except Exception:
            logger.debug("Hardware discovery skipped", exc_info=True)

    def _discover_services(self, caps: Capabilities) -> None:
        ports = {
            "ollama": 11434,
            "lm_studio": 1234,
            "groq": 443,
            "chromadb": 8000,
            "redis": 6379,
            "postgres": 5432,
            "docker": 2375,
            "vscode_server": 8000,
        }
        for name, port in ports.items():
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    caps.services[name] = True
            except Exception:
                caps.services[name] = False

    def _discover_browser(self, caps: Capabilities) -> None:
        try:
            caps.browser = {
                "default_browser_available": shutil.which("chrome") is not None
                or shutil.which("firefox") is not None
                or shutil.which("msedge") is not None,
            }
        except Exception:
            logger.debug("Browser discovery skipped", exc_info=True)

    def _discover_filesystem(self, caps: Capabilities) -> None:
        try:
            caps.filesystem = {
                "cwd_writable": os.access(os.getcwd(), os.W_OK),
                "home_dir": os.path.expanduser("~"),
            }
            data_dir = Path.home() / ".jarvis"
            caps.filesystem["jarvis_dir"] = str(data_dir)
            caps.filesystem["jarvis_dir_writable"] = os.access(data_dir, os.W_OK)
        except Exception:
            logger.debug("Filesystem discovery skipped", exc_info=True)

    def _discover_network(self, caps: Capabilities) -> None:
        try:
            caps.network = {"internet_available": True}
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=1)
            except Exception:
                caps.network["internet_available"] = False
        except Exception:
            logger.debug("Network discovery skipped", exc_info=True)


def get_capability_discovery() -> CapabilityDiscovery:
    global _default_discovery
    if "_default_discovery" not in globals():
        _default_discovery = CapabilityDiscovery()
    return _default_discovery
