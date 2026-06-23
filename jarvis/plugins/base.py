"""
Plugin system for JARVIS - Extensible architecture for custom commands and integrations.
"""

import asyncio
import json
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Plugin metadata from plugin.json."""
    name: str
    version: str
    author: str = ""
    description: str = ""
    commands: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    min_jarvis_version: str = "3.0.0"

    @classmethod
    def from_dict(cls, data: Dict) -> "PluginMetadata":
        """Create metadata from dictionary."""
        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "0.0.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            commands=data.get("commands", []),
            events=data.get("events", []),
            dependencies=data.get("dependencies", []),
            min_jarvis_version=data.get("min_jarvis_version", "3.0.0")
        )


@dataclass
class Plugin:
    """Base plugin class."""
    metadata: PluginMetadata
    path: Path
    enabled: bool = True
    loaded_at: Optional[datetime] = None

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    async def on_load(self, jarvis: Any) -> None:
        """Called when plugin is loaded."""
        logger.info(f"Plugin '{self.name}' loaded")

    async def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        logger.info(f"Plugin '{self.name}' unloaded")

    async def on_enable(self) -> None:
        """Called when plugin is enabled."""
        pass

    async def on_disable(self) -> None:
        """Called when plugin is disabled."""
        pass

    async def on_command(self, command: str, args: List[str], context: Dict) -> Optional[str]:
        """Handle custom command. Return response or None."""
        return None

    async def on_event(self, event: str, data: Any) -> None:
        """Handle events."""
        pass


class PluginManager:
    """
    Manages plugin lifecycle, loading, and command routing.
    """

    def __init__(self, plugins_dir: Path = None):
        if plugins_dir is None:
            plugins_dir = Path.home() / ".jarvis" / "plugins"
        
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Plugin] = {}
        self._jarvis = None
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._command_handlers: Dict[str, Callable] = {}
        self._loaded = False

    def set_jarvis(self, jarvis: Any) -> None:
        """Set reference to main JARVIS instance."""
        self._jarvis = jarvis

    @property
    def plugin_count(self) -> int:
        """Number of loaded plugins."""
        return len(self.plugins)

    @property
    def enabled_plugins(self) -> List[str]:
        """List of enabled plugin names."""
        return [p.name for p in self.plugins.values() if p.enabled]

    async def discover_plugins(self) -> List[Path]:
        """Discover plugins in plugins directory."""
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return []

        plugins = []
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "plugin.json").exists():
                plugins.append(item)

        return plugins

    async def load_plugin(self, path: Path) -> Optional[Plugin]:
        """Load a plugin from path."""
        try:
            metadata_path = path / "plugin.json"
            if not metadata_path.exists():
                logger.warning(f"No plugin.json found in {path}")
                return None

            with open(metadata_path, "r") as f:
                metadata_data = json.load(f)

            metadata = PluginMetadata.from_dict(metadata_data)

            if metadata.name in self.plugins:
                logger.info(f"Plugin '{metadata.name}' already loaded")
                return self.plugins[metadata.name]

            plugin = await self._import_plugin(path, metadata)

            if plugin:
                plugin.loaded_at = datetime.now()
                self.plugins[metadata.name] = plugin

                for cmd in metadata.commands:
                    self._command_handlers[cmd] = plugin.on_command

                for event in metadata.events:
                    if event not in self._event_handlers:
                        self._event_handlers[event] = []
                    self._event_handlers[event].append(plugin.on_event)

                if self._jarvis:
                    await plugin.on_load(self._jarvis)

                logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")
                return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {path}: {e}")
            return None

    async def _import_plugin(self, path: Path, metadata: PluginMetadata) -> Optional[Plugin]:
        """Import plugin module and instantiate."""
        try:
            init_file = path / "__init__.py"
            if not init_file.exists():
                main_files = list(path.glob("*.py"))
                if main_files:
                    init_file = main_files[0]
                else:
                    logger.warning(f"No Python files in plugin directory: {path}")
                    return None

            spec = importlib.util.spec_from_file_location(
                f"jarvis_plugin_{metadata.name}",
                init_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                    return obj(metadata=metadata, path=path)

            class DefaultPlugin(Plugin):
                pass
            return DefaultPlugin(metadata=metadata, path=path)

        except Exception as e:
            logger.error(f"Failed to import plugin: {e}")
            return None

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        if name not in self.plugins:
            return False

        plugin = self.plugins[name]
        await plugin.on_unload()

        for cmd in plugin.metadata.commands:
            self._command_handlers.pop(cmd, None)

        for event in plugin.metadata.events:
            if event in self._event_handlers:
                self._event_handlers[event] = [
                    h for h in self._event_handlers[event] 
                    if h != plugin.on_event
                ]

        del self.plugins[name]
        logger.info(f"Unloaded plugin: {name}")
        return True

    async def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        if name not in self.plugins:
            return False

        plugin = self.plugins[name]
        plugin.enabled = True
        await plugin.on_enable()
        logger.info(f"Enabled plugin: {name}")
        return True

    async def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        if name not in self.plugins:
            return False

        plugin = self.plugins[name]
        plugin.enabled = False
        await plugin.on_disable()
        logger.info(f"Disabled plugin: {name}")
        return True

    async def load_all(self) -> int:
        """Discover and load all plugins."""
        if self._loaded:
            return len(self.plugins)

        paths = await self.discover_plugins()
        for path in paths:
            await self.load_plugin(path)

        self._loaded = True
        return len(self.plugins)

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for name in list(self.plugins.keys()):
            await self.unload_plugin(name)
        self._loaded = False

    async def handle_command(self, command: str, args: List[str], context: Dict) -> Optional[str]:
        """Route command to appropriate plugin."""
        if command in self._command_handlers:
            handler = self._command_handlers[command]
            return await handler(command, args, context)
        return None

    async def emit_event(self, event: str, data: Any = None) -> None:
        """Emit event to all registered handlers."""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    await handler(event, data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

    def get_plugin_info(self, name: str) -> Optional[Dict]:
        """Get plugin information."""
        if name not in self.plugins:
            return None

        plugin = self.plugins[name]
        return {
            "name": plugin.name,
            "version": plugin.version,
            "author": plugin.metadata.author,
            "description": plugin.metadata.description,
            "enabled": plugin.enabled,
            "loaded_at": plugin.loaded_at.isoformat() if plugin.loaded_at else None,
            "commands": plugin.metadata.commands,
            "events": plugin.metadata.events,
        }

    def list_plugins(self) -> List[Dict]:
        """List all loaded plugins."""
        return [self.get_plugin_info(name) for name in self.plugins]
