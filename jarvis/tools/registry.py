"""
Tool registry for JARVIS.
Manages tool registration, discovery, and permission tracking.
"""

from typing import Any

from jarvis.tools.base import PermissionLevel, Tool, ToolCallback, ToolResult


class ToolRegistry:
    """
    Central registry for all JARVIS tools.
    Handles tool registration, lookup, and permission management.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._tool_classes: dict[str, type[Tool]] = {}
        self._categories: dict[str, list[str]] = {}
        self._permissions: dict[str, PermissionLevel] = {}
        self._callbacks: list[ToolCallback] = []

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        self._permissions[tool.name] = tool.get_permission_level()

        # Add to category
        category = tool.category
        if category not in self._categories:
            self._categories[category] = []
        if tool.name not in self._categories[category]:
            self._categories[category].append(tool.name)

    def register_class(self, tool_class: type[Tool], **kwargs) -> None:
        """Register a tool class with optional default parameters."""
        self._tool_classes[tool_class.__name__] = tool_class
        # Instantiate with kwargs
        tool = tool_class(**kwargs)
        self.register(tool)

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool."""
        if tool_name not in self._tools:
            return False

        self._tools.pop(tool_name, None)
        self._permissions.pop(tool_name, None)

        # Remove from category
        for _category, tools in self._categories.items():
            if tool_name in tools:
                tools.remove(tool_name)

        return True

    def get(self, tool_name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def get_all(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_by_category(self, category: str) -> list[Tool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def list_categories(self) -> list[str]:
        """List all tool categories."""
        return list(self._categories.keys())

    def search(self, query: str) -> list[Tool]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)
        return results

    async def execute(
        self, tool_name: str, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            input_data: Tool input parameters
            context: Execution context

        Returns:
            ToolResult from the tool execution
        """
        tool = self.get(tool_name)
        if tool is None:
            return ToolResult(success=False, output=None, error=f"Unknown tool: {tool_name}")

        # Check permission
        permission = tool.check_permission(input_data)
        if permission == PermissionLevel.DENY:
            return ToolResult(
                success=False, output=None, error=f"Tool '{tool_name}' is not allowed"
            )

        # Notify callbacks
        for callback in self._callbacks:
            callback.on_tool_start(tool_name, input_data)

        try:
            # Validate input
            is_valid, error = tool.validate_input(input_data)
            if not is_valid:
                return ToolResult(success=False, output=None, error=error)

            # Execute
            result = await tool.execute(input_data, context)

            # Notify callbacks
            for callback in self._callbacks:
                callback.on_tool_complete(tool_name, result)

            return result

        except Exception as e:
            error_result = ToolResult(success=False, output=None, error=str(e))
            for callback in self._callbacks:
                callback.on_tool_error(tool_name, e)
            return error_result

    def set_permission(self, tool_name: str, level: PermissionLevel) -> bool:
        """Override permission level for a tool."""
        if tool_name not in self._tools:
            return False
        self._permissions[tool_name] = level
        return True

    def get_permission(self, tool_name: str) -> PermissionLevel | None:
        """Get the current permission level for a tool."""
        return self._permissions.get(tool_name)

    def get_tools_for_prompt(self) -> list[dict[str, Any]]:
        """
        Get all tools formatted for LLM prompt inclusion.
        Returns tool name, description, and parameter schema.
        """
        tools = []
        for tool in self._tools.values():
            tools.append(
                {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            )
        return tools

    def add_callback(self, callback: ToolCallback) -> None:
        """Add a callback for tool execution events."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: ToolCallback) -> bool:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            return True
        return False


# Global registry instance
_registry: ToolRegistry | None = None


def _populate_default_tools(registry: ToolRegistry) -> None:

    """Auto-discover and register all built-in JARVIS tools."""
    # File tools
    try:
        from jarvis.tools.file_tools import (
            CreateTempFileTool,
            DeleteFileTool,
            DiskUsageTool,
            FindFilesTool,
            ListDirectoryTool,
            ReadFileTool,
            WriteFileTool,
        )
        for t in [ReadFileTool(), WriteFileTool(), ListDirectoryTool(), FindFilesTool(), DeleteFileTool(), DiskUsageTool(), CreateTempFileTool()]:
            if t.name not in registry._tools:
                registry.register(t)
    except Exception:
        pass

    # Terminal tools
    try:
        from jarvis.tools.terminal_tools import BashTool, RunScriptTool
        for t in [BashTool(), RunScriptTool()]:
            if t.name not in registry._tools:
                registry.register(t)
    except Exception:
        pass

    # System tools
    try:
        from jarvis.tools.system_tools import (
            GetClipboardTool,
            GetEnvironmentTool,
            GetSystemInfoTool,
            OpenAppTool,
            SetClipboardTool,
            SetEnvironmentTool,
        )
        for t in [GetSystemInfoTool(), OpenAppTool(), GetEnvironmentTool(), SetEnvironmentTool(), GetClipboardTool(), SetClipboardTool()]:
            if t.name not in registry._tools:
                registry.register(t)
    except Exception:
        pass

    # Web / Browser tools
    try:
        from jarvis.tools.browser_tools import BrowserTool, ScrapeWebTool, SearchWebTool
        for t in [BrowserTool(), SearchWebTool(), ScrapeWebTool()]:
            if t.name not in registry._tools:
                registry.register(t)
    except Exception:
        pass

    # Voice / Media / Camera capability tools
    try:
        from jarvis.tools.camera_tool import CameraTool, ScreenshotTool
        from jarvis.tools.image_gen_tool import ImageGenerationTool
        from jarvis.tools.speak_tool import SpeakTool
        for t in [SpeakTool(), ImageGenerationTool(), CameraTool(), ScreenshotTool()]:
            if t.name not in registry._tools:
                registry.register(t)
    except Exception:
        pass


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _populate_default_tools(_registry)
    return _registry


def init_registry() -> ToolRegistry:
    """Initialize the global tool registry."""
    global _registry
    _registry = ToolRegistry()
    _populate_default_tools(_registry)
    return _registry

