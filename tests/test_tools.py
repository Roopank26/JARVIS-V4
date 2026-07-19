"""
Tests for JARVIS tool system.
"""

import tempfile
from pathlib import Path

import pytest

from jarvis.tools.base import ToolResult
from jarvis.tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from jarvis.tools.registry import ToolRegistry


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        """Test successful result."""
        result = ToolResult(success=True, output="test output")

        assert result.success is True
        assert result.output == "test output"
        assert result.error is None
        assert str(result) == "test output"

    def test_error_result(self):
        """Test error result."""
        result = ToolResult(success=False, output=None, error="Something went wrong")

        assert result.success is False
        assert result.output is None
        assert "Something went wrong" in str(result)


class TestReadFileTool:
    """Tests for ReadFileTool."""

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test reading a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!")
            temp_path = f.name

        try:
            tool = ReadFileTool()
            result = await tool.execute({"path": temp_path})

            assert result.success is True
            assert "Hello, World!" in result.output
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_read_nonexistent(self):
        """Test reading non-existent file."""
        tool = ReadFileTool()
        result = await tool.execute({"path": "/nonexistent/file.txt"})

        assert result.success is False
        assert "not found" in result.error.lower()


class TestWriteFileTool:
    """Tests for WriteFileTool."""

    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test writing a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"

            tool = WriteFileTool()
            result = await tool.execute({"path": str(file_path), "content": "Test content"})

            assert result.success is True
            assert file_path.exists()
            assert file_path.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_append_file(self):
        """Test appending to a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("Original")

            tool = WriteFileTool()
            result = await tool.execute(
                {"path": str(file_path), "content": " appended", "append": True}
            )

            assert result.success is True
            assert file_path.read_text() == "Original appended"


class TestListDirectoryTool:
    """Tests for ListDirectoryTool."""

    @pytest.mark.asyncio
    async def test_list_directory(self):
        """Test listing a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.txt").touch()
            Path(tmpdir, "file2.txt").touch()
            Path(tmpdir, "subdir").mkdir()

            tool = ListDirectoryTool()
            result = await tool.execute({"path": tmpdir})

            assert result.success is True
            assert "file1.txt" in result.output
            assert "file2.txt" in result.output


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = ReadFileTool()

        registry.register(tool)

        assert "read_file" in registry.list_names()
        assert registry.get("read_file") is tool

    def test_get_tools_for_prompt(self):
        """Test getting tools for prompt."""
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())

        tools = registry.get_tools_for_prompt()

        assert len(tools) == 2
        assert any(t["name"] == "read_file" for t in tools)

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing a tool through registry."""
        registry = ToolRegistry()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        registry.register(ReadFileTool())

        try:
            result = await registry.execute("read_file", {"path": temp_path})

            assert result.success is True
            assert "Test content" in result.output
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        registry = ToolRegistry()
        result = await registry.execute("nonexistent_tool", {})

        assert result.success is False
        assert "Unknown tool" in result.error
