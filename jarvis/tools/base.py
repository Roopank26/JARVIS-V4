"""
Tool base classes for JARVIS.
Adapted from Claude Code's Tool framework.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass


class PermissionLevel(Enum):
    """Permission levels for tool execution."""
    AUTOMATIC = "automatic"      # Always allowed
    ASK_ONCE = "ask_once"         # Ask once per session
    ASK_ALWAYS = "ask_always"     # Ask every time
    DENY = "deny"                # Never allowed


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return str(self.output)
        return f"Error: {self.error}"


class Tool(ABC):
    """
    Abstract base class for all JARVIS tools.
    Adapted from Claude Code's Tool framework.
    """

    name: str = ""
    description: str = ""
    permission_level: PermissionLevel = PermissionLevel.ASK_ONCE

    # Categories for tool organization
    CATEGORY_FILE = "file"
    CATEGORY_SYSTEM = "system"
    CATEGORY_WEB = "web"
    CATEGORY_TERMINAL = "terminal"
    CATEGORY_COMMUNICATION = "communication"
    CATEGORY_MEDIA = "media"
    CATEGORY_DEVELOPMENT = "development"
    CATEGORY_MEMORY = "memory"

    name: str = ""
    description: str = ""

    @property
    def category(self) -> str:
        """Tool category for organization."""
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for tool parameters."""
        return {"type": "object", "properties": {}, "required": []}

    @property
    def is_read_only(self) -> bool:
        """Whether this tool only reads data (no side effects)."""
        return False

    @property
    def is_dangerous(self) -> bool:
        """Whether this tool could cause harm if misused."""
        return False

    def get_permission_level(self) -> PermissionLevel:
        """Get the permission level for this tool."""
        return self.permission_level

    def check_permission(self, input_data: Dict[str, Any]) -> PermissionLevel:
        """
        Check if this tool can be executed with the given input.
        Can be overridden for input-specific permission checks.
        """
        return self.get_permission_level()

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute the tool with the given input.

        Args:
            input_data: Tool-specific input parameters
            context: Execution context (user info, session info, etc.)

        Returns:
            ToolResult with success status and output/error
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters before execution.

        Returns:
            (is_valid, error_message)
        """
        return True, None

    def format_for_display(self, input_data: Dict[str, Any]) -> str:
        """Format tool call for display in UI."""
        params = ", ".join(f"{k}={v}" for k, v in input_data.items() if v is not None)
        return f"{self.name}({params})"

    def format_result(self, result: Any) -> str:
        """Format the result for display."""
        if isinstance(result, str):
            return result
        return str(result)


class ReadOnlyTool(Tool):
    """Base class for read-only tools."""

    @property
    def is_read_only(self) -> bool:
        return True

    permission_level = PermissionLevel.AUTOMATIC


class WriteTool(Tool):
    """Base class for tools that modify data."""

    permission_level = PermissionLevel.ASK_ONCE


class DestructiveTool(Tool):
    """Base class for tools that can cause data loss."""

    permission_level = PermissionLevel.ASK_ALWAYS
    is_dangerous = True


class ToolCallback:
    """Callback interface for tool execution events."""

    def on_tool_start(self, tool_name: str, input_data: Dict[str, Any]) -> None:
        """Called when a tool starts executing."""
        pass

    def on_tool_complete(self, tool_name: str, result: ToolResult) -> None:
        """Called when a tool completes execution."""
        pass

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Called when a tool encounters an error."""
        pass
