"""
File operation tools for JARVIS.
Adapted from Mark-XXXIX-OR's file_controller.py
"""

import shutil
from pathlib import Path
from typing import Any

from jarvis.tools.base import DestructiveTool, ReadOnlyTool, ToolResult, WriteTool


class ReadFileTool(ReadOnlyTool):
    """Read contents of a file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns the file content."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (0 = all)",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {path}")

            if not path.is_file():
                return ToolResult(success=False, output=None, error=f"Not a file: {path}")

            content = path.read_text(encoding="utf-8")

            max_lines = input_data.get("max_lines", 0)
            if max_lines > 0:
                lines = content.split("\n")
                content = "\n".join(lines[:max_lines])
                if len(lines) > max_lines:
                    content += f"\n... ({len(lines) - max_lines} more lines)"

            return ToolResult(success=True, output=content)

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WriteFileTool(WriteTool):
    """Write content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create a new file or overwrite an existing file with content."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write to the file"},
                "append": {
                    "type": "boolean",
                    "description": "Append to file instead of overwriting",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if input_data.get("append", False) else "w"

            with open(path, mode, encoding="utf-8") as f:
                f.write(input_data["content"])

            return ToolResult(success=True, output=f"File written: {path}")

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ListDirectoryTool(ReadOnlyTool):
    """List contents of a directory."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories in a given path."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list"},
                "show_hidden": {
                    "type": "boolean",
                    "description": "Show hidden files (default: false)",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Path not found: {path}")

            if not path.is_dir():
                return ToolResult(success=False, output=None, error=f"Not a directory: {path}")

            show_hidden = input_data.get("show_hidden", False)

            items = []
            for item in sorted(path.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue

                item_type = "DIR" if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else 0
                items.append(f"{item_type:4} {size:>10} {item.name}")

            if not items:
                return ToolResult(success=True, output="(empty directory)")

            return ToolResult(success=True, output="\n".join(items))

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class FindFilesTool(ReadOnlyTool):
    """Find files matching a pattern."""

    @property
    def name(self) -> str:
        return "find_files"

    @property
    def description(self) -> str:
        return "Search for files by name pattern. Supports * and ? wildcards."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory to search in"},
                "pattern": {
                    "type": "string",
                    "description": "File name pattern (e.g., *.py, test_*.txt)",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search recursively (default: true)",
                },
            },
            "required": ["path", "pattern"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()
            pattern = input_data["pattern"]
            recursive = input_data.get("recursive", True)

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Path not found: {path}")

            matches = list(path.rglob(pattern) if recursive else path.glob(pattern))

            if not matches:
                return ToolResult(success=True, output=f"No files matching '{pattern}' found")

            results = [str(m.relative_to(path)) for m in matches[:50]]

            return ToolResult(
                success=True, output=f"Found {len(matches)} files:\n" + "\n".join(results)
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DeleteFileTool(DestructiveTool):
    """Delete a file or directory."""

    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return "Delete a file or directory. Use with caution - this cannot be undone."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to delete"},
                "recursive": {"type": "boolean", "description": "Delete directories recursively"},
            },
            "required": ["path"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Path not found: {path}")

            recursive = input_data.get("recursive", False)

            if path.is_dir():
                if recursive:
                    shutil.rmtree(path)
                else:
                    path.rmdir()
            else:
                path.unlink()

            return ToolResult(success=True, output=f"Deleted: {path}")

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DiskUsageTool(ReadOnlyTool):
    """Get disk usage information."""

    @property
    def name(self) -> str:
        return "disk_usage"

    @property
    def description(self) -> str:
        return "Get disk usage information for a path."

    @property
    def category(self) -> str:
        return self.CATEGORY_FILE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to check disk usage"}},
            "required": ["path"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        try:
            path = Path(input_data["path"]).expanduser()

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Path not found: {path}")

            if path.is_file():
                size = path.stat().st_size
                return ToolResult(success=True, output=f"File size: {_format_size(size)}")

            # Directory - calculate total
            total_size = 0
            file_count = 0
            dir_count = 0

            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1

            return ToolResult(
                success=True,
                output=f"Path: {path}\nTotal size: {_format_size(total_size)}\nFiles: {file_count}\nDirectories: {dir_count}",
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


def _format_size(size: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
