"""
JARVIS Plugins - Extensible architecture for custom commands.

Two plugin systems:
1. base.py - Simple command/event-based plugins
2. plugin_manager.py - Advanced plugins with intents, tools, memory
"""

from jarvis.plugins.base import Plugin, PluginMetadata, PluginManager
from jarvis.plugins.plugin_manager import (
    PluginState,
    PluginInfo,
    PluginInterface,
    IntentPlugin,
    ToolPlugin,
    MemoryPlugin,
    get_plugin_manager as _get_manager,
)

# Keep backward compatibility
def get_plugin_manager() -> PluginManager:
    """Get plugin manager instance."""
    return _get_manager()

__all__ = [
    # Base classes
    "Plugin",
    "PluginMetadata",
    "PluginManager",
    # Advanced classes
    "PluginState",
    "PluginInfo",
    "PluginInterface",
    "IntentPlugin",
    "ToolPlugin",
    "MemoryPlugin",
    "get_plugin_manager",
]
