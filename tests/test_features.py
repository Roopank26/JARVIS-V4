"""
Feature tests for JARVIS - Voice, Vision, Browser, Memory.
"""

import tempfile
from pathlib import Path

import pytest


class TestVoiceFeatures:
    """Test voice input/output features."""

    def test_stt_import(self):
        """Test SpeechToText can be imported."""
        from jarvis.voice import AudioConfig, SpeechToText, TextToSpeech, VoiceAssistant

        assert SpeechToText is not None
        assert TextToSpeech is not None
        assert VoiceAssistant is not None
        assert AudioConfig is not None

    def test_tts_import(self):
        """Test TextToSpeech can be imported."""
        from jarvis.voice import TextToSpeech

        tts = TextToSpeech()
        assert tts.engine == "gtts"

    def test_tts_engine_selection(self):
        """Test TTS engine selection."""
        from jarvis.voice import TextToSpeech

        tts = TextToSpeech()
        tts.engine = "pyttsx3"
        assert tts.engine == "pyttsx3"
        tts.engine = "edge"
        assert tts.engine == "edge"

    @pytest.mark.asyncio
    async def test_tts_speak_simple(self):
        """Test TTS speak (simple output)."""
        from jarvis.voice import TextToSpeech

        tts = TextToSpeech()
        # This will just print since no audio in container
        await tts.speak("Hello, this is a test", blocking=False)
        # Should not crash

    def test_audio_config(self):
        """Test AudioConfig."""
        from jarvis.voice import AudioConfig

        config = AudioConfig(sample_rate=44100, channels=2)
        assert config.sample_rate == 44100
        assert config.channels == 2


class TestVisionFeatures:
    """Test screen capture and vision features."""

    def test_screen_capture_import(self):
        """Test ScreenCapture can be imported."""
        from jarvis.vision import ScreenAnalyzer, ScreenCapture, VisionCapture

        assert ScreenCapture is not None
        assert ScreenAnalyzer is not None
        assert VisionCapture is not None

    def test_screen_capture_init(self):
        """Test ScreenCapture initialization."""
        from jarvis.vision import ScreenCapture

        capture = ScreenCapture()
        assert capture._monitor == 1

    def test_screen_dimensions(self):
        """Test getting screen dimensions."""
        from jarvis.vision import ScreenCapture

        capture = ScreenCapture()
        dims = capture.get_dimensions()
        assert isinstance(dims, tuple)
        assert len(dims) == 2

    def test_screen_region(self):
        """Test ScreenRegion dataclass."""
        from jarvis.vision.screen import ScreenRegion

        region = ScreenRegion(x=0, y=0, width=800, height=600)
        assert region.x == 0
        assert region.width == 800

    def test_screen_analyzer_init(self):
        """Test ScreenAnalyzer initialization."""
        from jarvis.vision import ScreenAnalyzer

        ScreenAnalyzer()
        # Should not crash, just set flags

    def test_vision_capture_init(self):
        """Test VisionCapture initialization."""
        from jarvis.vision import VisionCapture

        vision = VisionCapture()
        assert vision.screen is not None
        assert vision.screen_analyzer is not None


class TestBrowserFeatures:
    """Test browser automation features."""

    def test_browser_tool_import(self):
        """Test BrowserTool can be imported."""
        from jarvis.tools import BrowserTool, ScrapeWebTool, SearchWebTool

        assert BrowserTool is not None
        assert SearchWebTool is not None
        assert ScrapeWebTool is not None

    def test_browser_tool_init(self):
        """Test BrowserTool initialization."""
        from jarvis.tools import BrowserTool

        tool = BrowserTool()
        assert tool.name == "browser"
        assert tool.config.headless is True

    def test_browser_tool_description(self):
        """Test BrowserTool has proper description."""
        from jarvis.tools import BrowserTool

        tool = BrowserTool()
        assert "browser" in tool.description.lower()

    def test_browser_tool_parameters(self):
        """Test BrowserTool has proper parameters."""
        from jarvis.tools import BrowserTool

        tool = BrowserTool()
        params = tool.parameters
        assert "action" in params["properties"]
        assert params["properties"]["action"]["type"] == "string"


class TestLongTermMemory:
    """Test long-term memory features."""

    def test_memory_import(self):
        """Test LongTermMemory can be imported."""
        from jarvis.memory import LongTermMemory

        assert LongTermMemory is not None

    def test_memory_init(self):
        """Test LongTermMemory initialization."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")
            assert memory is not None

    def test_memory_remember_recall(self):
        """Test memory remember and recall."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            # Store a fact
            memory.remember("test_key", "test_value", category="notes")

            # Recall it
            results = memory.recall("test_key")
            assert len(results) == 1
            assert results[0]["value"] == "test_value"

    def test_memory_categories(self):
        """Test different memory categories."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            # Test different categories
            memory.remember("name", "John", category="identity")
            memory.remember("theme", "dark", category="preferences")
            memory.remember("project_x", "in progress", category="projects")

            assert memory.get_identity()["name"]["value"] == "John"
            assert memory.get_preferences()["theme"]["value"] == "dark"
            assert memory.get_projects()["project_x"]["value"] == "in progress"

    def test_memory_forget(self):
        """Test memory forget."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("temp_key", "temp_value")
            assert len(memory.recall("temp_key")) == 1

            memory.forget("temp_key")
            assert len(memory.recall("temp_key")) == 0

    def test_memory_search(self):
        """Test memory search."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("python_project", "a web app in Python")
            memory.remember("java_project", "a mobile app in Java")

            results = memory.recall("python")
            assert len(results) >= 1
            assert any("python" in r["value"].lower() for r in results)

    def test_memory_semantic_search_fallback(self):
        """Test semantic search (falls back to keyword without embeddings)."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("favorite_color", "blue")
            memory.remember("least_favorite", "orange")

            # Should work even without sentence_transformers
            results = memory.semantic_search("color")
            assert len(results) >= 1

    def test_memory_format_for_prompt(self):
        """Test memory formatting for prompts."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("name", "Alice", category="identity")
            memory.remember("favorite_lang", "Python", category="preferences")

            formatted = memory.format_for_prompt()
            assert "Alice" in formatted or "Alice" in str(formatted)
            assert "Python" in formatted or "Python" in str(formatted)

    def test_memory_clear(self):
        """Test clearing memory."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("test", "value")
            assert len(memory.recall("test")) == 1

            memory.clear()
            assert len(memory.recall("test")) == 0

    def test_memory_stats(self):
        """Test memory statistics (categories method)."""
        from jarvis.memory import LongTermMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = LongTermMemory(Path(tmpdir) / "test_memory.json")

            memory.remember("fact1", "value1", category="identity")
            memory.remember("pref1", "value1", category="preferences")

            # Test getting categories
            identity = memory.get_identity()
            prefs = memory.get_preferences()
            assert "fact1" in identity
            assert "pref1" in prefs


class TestFileManagement:
    """Test file management features."""

    def test_file_tools_import(self):
        """Test file tools can be imported."""
        from jarvis.tools.file_tools import (
            ListDirectoryTool,
            ReadFileTool,
            WriteFileTool,
        )

        assert ReadFileTool is not None
        assert WriteFileTool is not None
        assert ListDirectoryTool is not None

    @pytest.mark.asyncio
    async def test_read_write_file(self):
        """Test read and write file tools."""
        from jarvis.tools.file_tools import ReadFileTool, WriteFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            content = "Hello, JARVIS!"

            # Write
            write_tool = WriteFileTool()
            result = await write_tool.execute(
                input_data={"path": str(test_file), "content": content}
            )
            assert result.success

            # Read
            read_tool = ReadFileTool()
            result = await read_tool.execute(input_data={"path": str(test_file)})
            assert result.success
            assert content in result.output

    @pytest.mark.asyncio
    async def test_list_directory(self):
        """Test list directory tool."""
        from jarvis.tools.file_tools import ListDirectoryTool

        with tempfile.TemporaryDirectory() as tmpdir:
            tool = ListDirectoryTool()
            result = await tool.execute(input_data={"path": tmpdir})
            assert result.success
            # Should list the directory contents


class TestTerminalExecution:
    """Test terminal execution features."""

    def test_terminal_tools_import(self):
        """Test terminal tools can be imported."""
        from jarvis.tools.terminal_tools import BashTool, RunScriptTool

        assert BashTool is not None
        assert RunScriptTool is not None

    @pytest.mark.asyncio
    async def test_bash_tool(self):
        """Test bash tool execution."""
        from jarvis.tools.terminal_tools import BashTool

        tool = BashTool()
        result = await tool.execute(input_data={"command": "echo 'Hello from JARVIS'"})
        assert result.success
        assert "Hello from JARVIS" in result.output

    @pytest.mark.asyncio
    async def test_bash_with_args(self):
        """Test bash tool with arguments."""
        from jarvis.tools.terminal_tools import BashTool

        tool = BashTool()
        result = await tool.execute(input_data={"command": "ls", "args": ["-la", "/tmp"]})
        assert result.success


class TestIntegration:
    """Integration tests combining features."""

    @pytest.mark.asyncio
    async def test_memory_with_file_tools(self):
        """Test memory combined with file tools."""
        from jarvis.memory import LongTermMemory
        from jarvis.tools.file_tools import WriteFileTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Store file path in memory
            memory = LongTermMemory(Path(tmpdir) / "memory.json")
            test_file = Path(tmpdir) / "notes.txt"

            memory.remember("notes_file", str(test_file), category="preferences")

            # Write to file
            write_tool = WriteFileTool()
            await write_tool.execute(
                input_data={"path": str(test_file), "content": "Important notes for JARVIS"}
            )

            # Verify memory references correct path
            results = memory.recall("notes_file")
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_voice_and_tts(self):
        """Test voice input and TTS output."""
        from jarvis.voice import AudioConfig, TextToSpeech

        config = AudioConfig(sample_rate=16000, channels=1)
        tts = TextToSpeech(config)

        # Should be able to speak
        await tts.speak("Testing voice output", blocking=False)

    def test_vision_and_memory(self):
        """Test vision with memory."""
        from jarvis.memory import LongTermMemory
        from jarvis.vision import ScreenCapture

        with tempfile.TemporaryDirectory() as tmpdir:
            capture = ScreenCapture()
            memory = LongTermMemory(Path(tmpdir) / "memory.json")

            # Store screen dimensions in memory
            dims = capture.get_dimensions()
            memory.remember("screen_resolution", f"{dims[0]}x{dims[1]}", category="preferences")

            results = memory.recall("screen")
            assert len(results) >= 1
