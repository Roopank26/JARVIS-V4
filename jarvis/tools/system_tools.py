"""
System control tools for JARVIS.
Adapted from Mark-XXXIX-OR's computer_settings.py and desktop.py
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from jarvis.tools.base import WriteTool, ReadOnlyTool, ToolResult


class GetSystemInfoTool(ReadOnlyTool):
    """Get system information."""

    @property
    def name(self) -> str:
        return "get_system_info"

    @property
    def description(self) -> str:
        return "Get information about the current system (OS, hostname, user, etc.)"

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
                "home": str(Path.home()),
                "cwd": str(Path.cwd()),
                "python_version": platform.python_version(),
            }

            # Add platform-specific info
            if platform.system() == "Linux":
                info["linux_distro"] = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
            elif platform.system() == "Darwin":
                info["mac_version"] = platform.mac_ver()[0]
            elif platform.system() == "Windows":
                info["windows_version"] = platform.win32_ver()[0]

            output = "\n".join(f"{k}: {v}" for k, v in info.items())
            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class OpenAppTool(WriteTool):
    """Open an application or URL."""

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open an application, file, or URL using the system's default handler."

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "App name, file path, or URL to open"
                },
                "background": {
                    "type": "boolean",
                    "description": "Open in background without focus"
                }
            },
            "required": ["target"]
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            target = input_data["target"]
            background = input_data.get("background", False)

            system = platform.system()

            if system == "Darwin":  # macOS
                cmd = ["open"]
                if background:
                    cmd.append("-g")
                cmd.append(target)
            elif system == "Windows":
                cmd = ["start"]
                if background:
                    cmd.append("/B")
                cmd.append(target)
            else:  # Linux
                cmd = ["xdg-open"]
                if background:
                    cmd = ["nohup"] + cmd
                cmd.append(target)

            subprocess.run(cmd, capture_output=True, text=True)

            return ToolResult(success=True, output=f"Opened: {target}")

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GetEnvironmentTool(ReadOnlyTool):
    """Get environment variables."""

    @property
    def name(self) -> str:
        return "get_environment"

    @property
    def description(self) -> str:
        return "Get environment variables. Optionally filter by prefix."

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": "Filter variables by prefix (e.g., PATH, HOME)"
                },
                "all": {
                    "type": "boolean",
                    "description": "Return all variables (careful - may be large)"
                }
            },
            "required": []
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            all_vars = input_data.get("all", False)
            prefix = input_data.get("prefix", "")

            if all_vars:
                output = "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))
            elif prefix:
                output = "\n".join(
                    f"{k}={v}" for k, v in sorted(os.environ.items())
                    if k.startswith(prefix.upper())
                )
            else:
                # Default: show common variables
                common = ["PATH", "HOME", "USER", "PWD", "SHELL", "LANG", "TERM"]
                output = "\n".join(
                    f"{k}={os.environ.get(k, '')}" for k in common
                )

            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SetEnvironmentTool(WriteTool):
    """Set environment variables for the current session."""

    @property
    def name(self) -> str:
        return "set_environment"

    @property
    def description(self) -> str:
        return "Set environment variables for the current session."

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "variable": {
                    "type": "string",
                    "description": "Variable name"
                },
                "value": {
                    "type": "string",
                    "description": "Variable value"
                }
            },
            "required": ["variable", "value"]
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            variable = input_data["variable"]
            value = input_data["value"]

            os.environ[variable] = value

            return ToolResult(success=True, output=f"Set {variable}={value}")

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GetClipboardTool(ReadOnlyTool):
    """Get clipboard contents."""

    @property
    def name(self) -> str:
        return "get_clipboard"

    @property
    def description(self) -> str:
        return "Get the current clipboard contents."

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            system = platform.system()

            if system == "Darwin":
                result = subprocess.run(
                    ["pbpaste"], capture_output=True, text=True
                )
            elif system == "Windows":
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True
                )
            else:  # Linux
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True, text=True
                )

            content = result.stdout.strip() if result.stdout else "(empty)"

            return ToolResult(success=True, output=content)

        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="Clipboard tool not available")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SetClipboardTool(WriteTool):
    """Set clipboard contents."""

    @property
    def name(self) -> str:
        return "set_clipboard"

    @property
    def description(self) -> str:
        return "Set the clipboard contents."

    @property
    def category(self) -> str:
        return self.CATEGORY_SYSTEM

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to copy to clipboard"
                }
            },
            "required": ["content"]
        }

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            content = input_data["content"]
            system = platform.system()

            if system == "Darwin":
                subprocess.run(
                    ["pbcopy"], input=content, text=True, capture_output=True
                )
            elif system == "Windows":
                escaped = content.replace("'", "''")
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{escaped}'"],
                    capture_output=True, text=True
                )
            else:  # Linux
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-i"],
                    input=content, text=True, capture_output=True
                )

            return ToolResult(success=True, output="Clipboard set")

        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="Clipboard tool not available")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
