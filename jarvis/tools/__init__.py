"""
Tools module for JARVIS.
Provides file operations, terminal execution, browser control, and system tools.
"""

from jarvis.tools.base import (
    Tool,
    ToolResult,
    PermissionLevel,
    ReadOnlyTool,
    WriteTool,
    DestructiveTool,
    ToolCallback
)
from jarvis.tools.registry import ToolRegistry, get_registry, init_registry
from jarvis.tools.browser_tools import BrowserTool, SearchWebTool, ScrapeWebTool

__all__ = [
    "Tool",
    "ToolResult",
    "PermissionLevel",
    "ReadOnlyTool",
    "WriteTool",
    "DestructiveTool",
    "ToolCallback",
    "ToolRegistry",
    "get_registry",
    "init_registry",
    "BrowserTool",
    "SearchWebTool",
    "ScrapeWebTool",
]
