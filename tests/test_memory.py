"""
Tests for JARVIS memory systems.
"""

import tempfile
from pathlib import Path

from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.session import SessionMemory


class TestSessionMemory:
    """Tests for SessionMemory."""

    def test_add_user_message(self):
        """Test adding user messages."""
        memory = SessionMemory()
        memory.add_user_message("Hello")

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "user"
        assert memory.messages[0].content == "Hello"

    def test_add_assistant_message(self):
        """Test adding assistant messages."""
        memory = SessionMemory()
        memory.add_assistant_message("Hi there!")

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "assistant"
        assert memory.messages[0].content == "Hi there!"

    def test_add_tool_message(self):
        """Test adding tool messages."""
        memory = SessionMemory()
        memory.add_tool_message("read_file", "file contents")

        assert len(memory.messages) == 1
        assert memory.messages[0].role == "tool"
        assert memory.messages[0].tool_name == "read_file"
        assert memory.messages[0].tool_result == "file contents"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        memory = SessionMemory()
        for i in range(15):
            memory.add_user_message(f"Message {i}")

        recent = memory.get_recent_messages(5)
        assert len(recent) == 5
        assert recent[-1].content == "Message 14"

    def test_get_context_string(self):
        """Test getting formatted context."""
        memory = SessionMemory()
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")

        context = memory.get_context_string()

        assert "User: Hello" in context
        assert "Assistant: Hi!" in context

    def test_clear(self):
        """Test clearing memory."""
        memory = SessionMemory()
        memory.add_user_message("Hello")
        memory.clear()

        assert len(memory.messages) == 0


class TestLongTermMemory:
    """Tests for LongTermMemory."""

    def test_remember(self):
        """Test storing memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.json")

            result = memory.remember("name", "John", "identity")
            assert result is True

            # Check it was stored
            recall = memory.recall("name")
            assert len(recall) > 0
            assert any(r["value"] == "John" for r in recall)

    def test_forget(self):
        """Test forgetting memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.json")

            memory.remember("test", "value", "notes")
            result = memory.forget("test", "notes")

            assert result is True

    def test_format_for_prompt(self):
        """Test prompt formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "memory.json")

            memory.remember("name", "Alice", "identity")
            memory.remember("color", "blue", "preferences")

            formatted = memory.format_for_prompt()

            assert "Name: Alice" in formatted
            assert "Color: blue" in formatted or "color" in formatted.lower()


class TestMemoryManager:
    """Tests for MemoryManager."""

    def test_session_and_longterm(self):
        """Test combined session and long-term memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(Path(tmpdir) / "memory.json")

            # Test session
            manager.add_user_message("Test message")
            assert len(manager.session.messages) == 1

            # Test long-term
            manager.remember("key", "value", "notes")
            assert len(manager.recall("key")) > 0

    def test_quick_updates(self):
        """Test quick update methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(Path(tmpdir) / "memory.json")

            manager.update_identity("name", "Bob")
            manager.update_preference("color", "red")
            manager.update_project("jarvis", "AI assistant")

            identity = manager.get_identity()
            assert "name" in identity
