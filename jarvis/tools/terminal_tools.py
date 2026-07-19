"""
Terminal/shell command tools for JARVIS.
Adapted from Claude Code's BashTool.
"""

import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jarvis.tools.base import PermissionLevel, ToolResult, WriteTool


class BashTool(WriteTool):
    """Execute shell commands."""

    def __init__(self):
        super().__init__()
        self.permission_level = PermissionLevel.ASK_ALWAYS
        self._allowed_commands: list[str] = []
        self._denied_commands: list[str] = ["rm -rf /", "dd if=", ":(){:|:&};:"]

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command. Returns command output."

    @property
    def category(self) -> str:
        return self.CATEGORY_TERMINAL

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
                "cwd": {"type": "string", "description": "Working directory for command"},
            },
            "required": ["command"],
        }

    def check_permission(self, input_data: dict[str, Any]) -> PermissionLevel:
        """Check if the command is allowed."""
        command = input_data.get("command", "")

        # Check denied patterns
        for denied in self._denied_commands:
            if denied in command:
                return PermissionLevel.DENY

        # Check allowed patterns if set
        if self._allowed_commands:
            for allowed in self._allowed_commands:
                if allowed in command:
                    return PermissionLevel.ASK_ALWAYS
            return PermissionLevel.DENY

        return PermissionLevel.ASK_ALWAYS

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            command = input_data["command"]
            timeout = input_data.get("timeout", 30)
            cwd = input_data.get("cwd")

            # Expand environment variables
            command = os.path.expandvars(command)

            # Use shell=True for complex commands, False for simple ones
            use_shell = any(s in command for s in [";", "|", "&", "&&", "||", ">", "<"])

            if use_shell:
                # Run through shell for complex commands
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd or str(Path.cwd()),
                )
            else:
                # Simple command parsing
                args = shlex.split(command)
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=cwd or str(Path.cwd()),
                )

            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"STDERR: {result.stderr}")

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output="\n".join(output) if output else "Command completed successfully",
                )
            else:
                return ToolResult(
                    success=True,  # Still success, just with non-zero exit
                    output=(
                        "\n".join(output)
                        if output
                        else f"Command exited with code {result.returncode}"
                    ),
                )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None, error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class RunScriptTool(WriteTool):
    """Run a Python or shell script."""

    @property
    def name(self) -> str:
        return "run_script"

    @property
    def description(self) -> str:
        return "Run a Python or shell script file."

    @property
    def category(self) -> str:
        return self.CATEGORY_TERMINAL

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the script file"},
                "args": {"type": "string", "description": "Arguments to pass to the script"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"},
            },
            "required": ["path"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Script not found: {path}")

            suffix = path.suffix.lower()

            if suffix == ".py":
                cmd = ["python3", str(path)]
            elif suffix in [".sh", ".bash"]:
                cmd = ["bash", str(path)]
            else:
                cmd = [str(path)]

            args = input_data.get("args", "")
            if args:
                cmd.extend(shlex.split(args))

            timeout = input_data.get("timeout", 60)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"STDERR: {result.stderr}")

            return ToolResult(
                success=result.returncode == 0,
                output=(
                    "\n".join(output) if output else f"Script exited with code {result.returncode}"
                ),
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CreateTempFileTool(WriteTool):
    """Create a temporary file."""

    @property
    def name(self) -> str:
        return "create_temp_file"

    @property
    def description(self) -> str:
        return "Create a temporary file with content."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content for the temporary file"},
                "suffix": {
                    "type": "string",
                    "description": "File suffix/extension (e.g., .py, .txt)",
                },
                "delete_on_exit": {
                    "type": "boolean",
                    "description": "Delete file when script exits",
                },
            },
            "required": ["content"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            content = input_data["content"]
            suffix = input_data.get("suffix", ".tmp")
            delete_on_exit = input_data.get("delete_on_exit", True)

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=delete_on_exit, encoding="utf-8"
            ) as f:
                f.write(content)
                temp_path = f.name

            return ToolResult(success=True, output=f"Created temp file: {temp_path}")

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
