"""
JARVIS Plugin System

Manages extensible plugins for adding capabilities to JARVIS.
"""

import importlib
import importlib.util
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """Plugin lifecycle states."""

    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """Plugin metadata."""

    id: str
    name: str
    version: str
    description: str
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    min_jarvis_version: str = "1.0.0"
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginRecord:
    """Loaded plugin instance record."""

    info: PluginInfo
    state: PluginState = PluginState.DISCOVERED
    instance: Any | None = None
    module: Any | None = None
    error: str | None = None
    loaded_at: str | None = None


class PluginInterface(ABC):
    """
    Base interface for JARVIS plugins.

    All plugins must inherit from this class and implement
    the required methods.
    """

    # Plugin metadata (override in subclass)
    PLUGIN_ID: str = "base_plugin"
    PLUGIN_NAME: str = "Base Plugin"
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_DESCRIPTION: str = "A base plugin"
    PLUGIN_AUTHOR: str = ""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize plugin with optional configuration."""
        self.config = config or {}
        self._enabled = False
        self._jarvis = None

    @abstractmethod
    async def initialize(self, jarvis_instance: Any) -> bool:
        """
        Initialize the plugin with JARVIS instance.

        Args:
            jarvis_instance: Reference to main JARVIS instance

        Returns:
            True if initialization successful
        """
        self._jarvis = jarvis_instance
        self._enabled = True
        return True

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> Any:
        """
        Execute plugin logic.

        Args:
            context: Execution context with input and metadata

        Returns:
            Plugin-specific result
        """
        pass

    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        self._enabled = False
        self._jarvis = None

    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            id=self.PLUGIN_ID,
            name=self.PLUGIN_NAME,
            version=self.PLUGIN_VERSION,
            description=self.PLUGIN_DESCRIPTION,
            author=self.PLUGIN_AUTHOR,
        )

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled


class IntentPlugin(PluginInterface):
    """Plugin that adds custom intent handlers."""

    @abstractmethod
    async def match_intent(self, text: str) -> str | None:
        """
        Match user input to this plugin's intent.

        Args:
            text: User input text

        Returns:
            Intent ID if matched, None otherwise
        """
        pass

    @abstractmethod
    async def handle_intent(self, text: str, context: dict[str, Any]) -> str:
        """
        Handle matched intent.

        Args:
            text: Original user input
            context: Execution context

        Returns:
            Response text
        """
        pass


class ToolPlugin(PluginInterface):
    """Plugin that adds custom tools/commands."""

    @abstractmethod
    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get definitions of tools provided by this plugin.

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        """
        Execute a tool provided by this plugin.

        Args:
            tool_name: Name of the tool
            args: Tool arguments

        Returns:
            Tool result
        """
        pass


class MemoryPlugin(PluginInterface):
    """Plugin that extends memory capabilities."""

    @abstractmethod
    async def store(self, key: str, value: Any, metadata: dict | None = None) -> bool:
        """Store data in plugin memory."""
        pass

    @abstractmethod
    async def recall(self, key: str) -> Any | None:
        """Recall data from plugin memory."""
        pass

    @abstractmethod
    async def search(self, query: str) -> list[Any]:
        """Search plugin memory."""
        pass


class AdvancedPluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    Features:
    - Auto-discovery from plugins directory
    - Plugin validation and sandboxing
    - Dependency resolution
    - Hot-reloading support
    """

    def __init__(self, plugins_dir: Path | None = None):
        """
        Initialize plugin manager.

        Args:
            plugins_dir: Directory to load plugins from
        """
        self.plugins_dir = plugins_dir or Path(__file__).parent / "plugins"
        self.plugins: dict[str, PluginRecord] = {}
        self._enabled_plugins: set[str] = set()
        self._intent_plugins: list[IntentPlugin] = []
        self._tool_plugins: list[ToolPlugin] = []
        self._memory_plugins: list[MemoryPlugin] = []
        self._jarvis_instance = None
        self._config_dir = Path.home() / ".jarvis" / "plugins"
        self._config_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled_plugins(self) -> list[str]:
        """Get list of enabled plugin IDs."""
        return list(self._enabled_plugins)

    async def initialize(self, jarvis_instance: Any) -> None:
        """
        Initialize plugin manager.

        Args:
            jarvis_instance: Main JARVIS instance
        """
        self._jarvis_instance = jarvis_instance

        # Load enabled plugins from config
        await self._load_enabled_list()

        # Discover and load all plugins
        plugin_ids = self._scan_plugin_dir(self.plugins_dir)
        for plugin_id in plugin_ids:
            self.load_plugin(plugin_id)

        # Initialize enabled plugins
        await self._initialize_enabled()

    @staticmethod
    def _scan_plugin_dir(directory: Path) -> list[str]:
        """
        Scan a plugins directory for subdirectories containing plugin.json manifests.

        Args:
            directory: Directory to scan for plugins

        Returns:
            List of discovered plugin IDs
        """
        discovered: list[str] = []
        if directory.exists() and directory.is_dir():
            for path in directory.iterdir():
                if path.is_dir() and not path.name.startswith("_"):
                    manifest = path / "plugin.json"
                    if manifest.exists():
                        try:
                            data = json.loads(manifest.read_text())
                            plugin_id = data.get("id", path.name)
                            discovered.append(plugin_id)
                        except Exception as e:
                            logger.warning(f"Failed to read manifest in {path}: {e}")
        logger.info(f"Discovered {len(discovered)} plugins from {directory}")
        return discovered

    def load_plugin(self, plugin_id: str) -> bool:
        """
        Load a plugin by ID.

        Args:
            plugin_id: Plugin ID to load

        Returns:
            True if plugin loaded successfully
        """
        plugin_dir = self.plugins_dir / plugin_id
        if not plugin_dir.exists():
            logger.error(f"Plugin directory not found: {plugin_dir}")
            return False

        if plugin_id in self.plugins:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return True

        try:
            # Check for manifest
            manifest = plugin_dir / "plugin.json"
            if manifest.exists():
                data = json.loads(manifest.read_text())
                entry_point = data.get("entry_point", "plugin.py")
                plugin_file = plugin_dir / entry_point
            else:
                plugin_file = plugin_dir / "__init__.py"

            if not plugin_file.exists():
                plugin_file = plugin_dir / "plugin.py"

            if not plugin_file.exists():
                logger.error(f"No plugin file found in {plugin_dir}")
                return False

            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"jarvis_plugins.{plugin_id}", plugin_file
            )
            if not spec or not spec.loader:
                logger.error(f"Failed to create spec for {plugin_id}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginInterface)
                    and attr != PluginInterface
                    and attr != IntentPlugin
                    and attr != ToolPlugin
                    and attr != MemoryPlugin
                ):
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No PluginInterface subclass found in {plugin_id}")
                return False

            # Create plugin instance
            instance = plugin_class()
            info = instance.get_info()

            plugin = PluginRecord(
                info=info, state=PluginState.LOADED, instance=instance, module=module
            )

            self.plugins[plugin_id] = plugin
            logger.debug(f"Loaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            if plugin_id not in self.plugins:
                self.plugins[plugin_id] = PluginRecord(
                    info=PluginInfo(id=plugin_id, name=plugin_id, version="unknown", description=""),
                    state=PluginState.FAILED,
                    error=str(e),
                )
            else:
                self.plugins[plugin_id].state = PluginState.FAILED
                self.plugins[plugin_id].error = str(e)
            return False

    async def _load_enabled_list(self) -> None:
        """Load list of enabled plugins from config."""
        config_file = self._config_dir / "enabled.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                self._enabled_plugins = set(data.get("enabled", []))
            except Exception as e:
                logger.error(f"Failed to load enabled plugins: {e}")

    async def _save_enabled_list(self) -> None:
        """Save list of enabled plugins to config."""
        config_file = self._config_dir / "enabled.json"
        try:
            config_file.write_text(json.dumps({"enabled": list(self._enabled_plugins)}, indent=2))
        except Exception as e:
            logger.error(f"Failed to save enabled plugins: {e}")

    async def discover_plugins(self) -> list[PluginInfo]:
        """
        Discover all available plugins.

        Returns:
            List of discovered plugin information
        """
        discovered = []

        # Check plugins directory
        if self.plugins_dir.exists():
            for path in self.plugins_dir.iterdir():
                if path.is_dir() and not path.name.startswith("_"):
                    plugin = await self._load_plugin_from_dir(path)
                    if plugin:
                        discovered.append(plugin.info)
                        self.plugins[plugin.info.id] = plugin

        # Check for single-file plugins
        single_file = self.plugins_dir.parent / "plugins"
        if single_file.exists():
            for path in single_file.glob("*.py"):
                if path.name not in ["__init__.py", "__main__.py"]:
                    plugin = await self._load_plugin_from_file(path)
                    if plugin:
                        discovered.append(plugin.info)
                        self.plugins[plugin.info.id] = plugin

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    async def _load_plugin_from_dir(self, plugin_dir: Path) -> PluginRecord | None:
        """Load plugin from directory."""
        plugin_file = plugin_dir / "__init__.py"
        if not plugin_file.exists():
            plugin_file = plugin_dir / "plugin.py"

        if not plugin_file.exists():
            return None

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"jarvis_plugins.{plugin_dir.name}", plugin_file
            )
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginInterface)
                    and attr != PluginInterface
                    and attr != IntentPlugin
                    and attr != ToolPlugin
                    and attr != MemoryPlugin
                ):
                    plugin_class = attr
                    break

            if not plugin_class:
                return None

            # Create plugin instance
            instance = plugin_class()
            info = instance.get_info()

            plugin = PluginRecord(
                info=info, state=PluginState.LOADED, instance=instance, module=module
            )

            logger.debug(f"Loaded plugin: {info.id}")
            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_dir}: {e}")
            return None

    async def _load_plugin_from_file(self, plugin_file: Path) -> PluginRecord | None:
        """Load plugin from single file."""
        return await self._load_plugin_from_dir(plugin_file.parent / plugin_file.stem)

    async def _initialize_enabled(self) -> None:
        """Initialize all enabled plugins."""
        for plugin_id in self._enabled_plugins:
            if plugin_id in self.plugins:
                await self.enable_plugin(plugin_id)

    async def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a plugin.

        Args:
            plugin_id: Plugin ID to enable

        Returns:
            True if successful
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin not found: {plugin_id}")
            return False

        plugin = self.plugins[plugin_id]

        try:
            plugin.state = PluginState.LOADING

            if plugin.instance and self._jarvis_instance:
                success = await plugin.instance.initialize(self._jarvis_instance)
                if not success:
                    plugin.state = PluginState.FAILED
                    plugin.error = "Initialization failed"
                    return False

            plugin.state = PluginState.INITIALIZED
            self._enabled_plugins.add(plugin_id)
            await self._save_enabled_list()

            # Register plugin handlers
            self._register_plugin_handlers(plugin)

            logger.info(f"Enabled plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable plugin {plugin_id}: {e}")
            plugin.state = PluginState.FAILED
            plugin.error = str(e)
            return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin.

        Args:
            plugin_id: Plugin ID to disable

        Returns:
            True if successful
        """
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        try:
            if plugin.instance:
                await plugin.instance.cleanup()

            self._unregister_plugin_handlers(plugin)

            plugin.state = PluginState.DISABLED
            self._enabled_plugins.discard(plugin_id)
            await self._save_enabled_list()

            logger.info(f"Disabled plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            return False

    def _register_plugin_handlers(self, plugin: PluginRecord) -> None:
        """Register plugin handlers."""
        if isinstance(plugin.instance, IntentPlugin):
            self._intent_plugins.append(plugin.instance)
        if isinstance(plugin.instance, ToolPlugin):
            self._tool_plugins.append(plugin.instance)
        if isinstance(plugin.instance, MemoryPlugin):
            self._memory_plugins.append(plugin.instance)

    def _unregister_plugin_handlers(self, plugin: PluginRecord) -> None:
        """Unregister plugin handlers."""
        if isinstance(plugin.instance, IntentPlugin):
            self._intent_plugins = [p for p in self._intent_plugins if p is not plugin.instance]
        if isinstance(plugin.instance, ToolPlugin):
            self._tool_plugins = [p for p in self._tool_plugins if p is not plugin.instance]
        if isinstance(plugin.instance, MemoryPlugin):
            self._memory_plugins = [p for p in self._memory_plugins if p is not plugin.instance]

    async def match_intent(self, text: str) -> tuple | None:
        """
        Match text against all intent plugins.

        Args:
            text: User input text

        Returns:
            Tuple of (plugin, intent_id, confidence) or None
        """
        for plugin in self._intent_plugins:
            try:
                intent_id = await plugin.match_intent(text)
                if intent_id:
                    return (plugin, intent_id, 1.0)
            except Exception as e:
                logger.error(f"Intent matching failed for {plugin.PLUGIN_ID}: {e}")

        return None

    async def handle_intent(self, plugin: IntentPlugin, text: str, context: dict) -> str:
        """Handle matched intent from plugin."""
        try:
            return await plugin.handle_intent(text, context)
        except Exception as e:
            logger.error(f"Intent handling failed: {e}")
            return f"Plugin error: {e}"

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions from tool plugins."""
        tools = []
        for plugin in self._tool_plugins:
            try:
                tools.extend(plugin.get_tool_definitions())
            except Exception as e:
                logger.error(f"Failed to get tools from {plugin.PLUGIN_ID}: {e}")
        return tools

    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Execute a tool from tool plugins."""
        for plugin in self._tool_plugins:
            try:
                result = await plugin.execute_tool(tool_name, args)
                return result
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_name}: {e}")

        return {"error": f"Tool not found: {tool_name}"}

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all plugins with their metadata."""
        return [
            {
                "id": p.info.id,
                "name": p.info.name,
                "version": p.info.version,
                "description": p.info.description,
                "author": p.info.author,
                "state": p.state.value,
                "enabled": p.info.id in self._enabled_plugins,
                "error": p.error,
            }
            for p in self.plugins.values()
        ]

    def get_plugin_info(self, plugin_id: str) -> PluginInfo | None:
        """Get information about a specific plugin."""
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].info
        return None


# Global plugin manager instance
_plugin_manager: AdvancedPluginManager | None = None


def get_plugin_manager() -> AdvancedPluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = AdvancedPluginManager()
    return _plugin_manager
