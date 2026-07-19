"""
Tests for system tools including OpenAppTool Windows fix.
"""

import platform
from unittest.mock import Mock, patch

import pytest

from jarvis.tools.system_tools import OpenAppTool


class TestOpenAppTool:
    """Tests for OpenAppTool."""

    @pytest.fixture
    def tool(self):
        """Create OpenAppTool instance."""
        return OpenAppTool()

    def test_name(self, tool):
        """Test tool name."""
        assert tool.name == "open_app"

    def test_description(self, tool):
        """Test tool description."""
        assert "Open" in tool.description

    def test_parameters(self, tool):
        """Test parameters schema."""
        params = tool.parameters
        assert "target" in params["properties"]
        assert "background" in params["properties"]

    def test_windows_aliases(self, tool):
        """Test Windows alias resolution."""
        assert tool._resolve_windows_alias("notepad") == "notepad.exe"
        assert tool._resolve_windows_alias("calc") == "calc.exe"
        assert tool._resolve_windows_alias("calculator") == "calc.exe"
        assert tool._resolve_windows_alias("cmd") == "cmd.exe"
        assert tool._resolve_windows_alias("powershell") == "powershell.exe"
        assert tool._resolve_windows_alias("explorer") == "explorer.exe"
        assert tool._resolve_windows_alias("chrome") == "chrome.exe"
        assert tool._resolve_windows_alias("edge") == "msedge.exe"

    def test_windows_alias_case_insensitive(self, tool):
        """Test alias resolution is case insensitive."""
        assert tool._resolve_windows_alias("Notepad") == "notepad.exe"
        assert tool._resolve_windows_alias("CALC") == "calc.exe"
        assert tool._resolve_windows_alias(" PowerShell ") == "powershell.exe"

    def test_windows_alias_unknown(self, tool):
        """Test unknown targets pass through."""
        assert tool._resolve_windows_alias("myapp") == "myapp"
        assert tool._resolve_windows_alias("/path/to/file.txt") == "/path/to/file.txt"
        assert tool._resolve_windows_alias("https://example.com") == "https://example.com"

    def test_settings_alias(self, tool):
        """Test Windows Settings alias uses protocol."""
        assert tool._resolve_windows_alias("settings") == "ms-settings:"

    def test_browser_url_detection(self, tool):
        """Test browser URL detection."""
        assert tool._is_browser_search("google") == "https://www.google.com"
        assert tool._is_browser_search("youtube") == "https://youtube.com"
        assert tool._is_browser_search("github") == "https://github.com"
        assert tool._is_browser_search("chrome") is None  # This is an app, not a URL

    def test_is_url(self, tool):
        """Test URL detection."""
        assert tool._is_url("https://example.com") is True
        assert tool._is_url("http://example.com") is True
        assert tool._is_url("www.example.com") is True
        assert tool._is_url("notepad") is False
        assert tool._is_url("chrome") is False

    @pytest.mark.asyncio
    async def test_open_notepad_windows(self, tool):
        """Test opening notepad on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(tool, "_find_installed_app", return_value=r"C:\Windows\notepad.exe"):
                with patch("jarvis.tools.system_tools.os.startfile", create=True) as mock_startfile:
                    result = await tool.execute({"target": "notepad"})

                    assert result.success is True
                    assert "notepad" in result.output.lower()
                    assert "Executable:" in result.output
                    mock_startfile.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_calculator_windows(self, tool):
        """Test opening calculator on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(
                tool, "_find_installed_app", return_value=r"C:\Windows\System32\calc.exe"
            ):
                with patch("jarvis.tools.system_tools.os.startfile", create=True) as mock_startfile:
                    result = await tool.execute({"target": "calculator"})

                    assert result.success is True
                    mock_startfile.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_powershell_windows(self, tool):
        """Test opening PowerShell on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(
                tool,
                "_find_installed_app",
                return_value=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            ):
                with patch("jarvis.tools.system_tools.os.startfile", create=True) as mock_startfile:
                    result = await tool.execute({"target": "powershell"})

                    assert result.success is True
                    mock_startfile.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_url_windows(self, tool):
        """Test opening URL on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch("jarvis.tools.system_tools.os.startfile", create=True) as mock_startfile:
                result = await tool.execute({"target": "https://github.com"})

                assert result.success is True
                assert "Status:" in result.output
                mock_startfile.assert_called_once_with("https://github.com")

    @pytest.mark.asyncio
    async def test_open_google_as_url(self, tool):
        """Test opening 'google' as a URL."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch("jarvis.tools.system_tools.os.startfile", create=True) as mock_startfile:
                result = await tool.execute({"target": "google"})

                assert result.success is True
                assert "GOOGLE" in result.output
                assert "https://www.google.com" in str(mock_startfile.call_args)

    @pytest.mark.asyncio
    async def test_open_youtube_as_url(self, tool):
        """Test opening 'youtube' as a URL."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch("jarvis.tools.system_tools.os.startfile", create=True) as _mock_startfile:
                result = await tool.execute({"target": "youtube"})

                assert result.success is True
                assert "YOUTUBE" in result.output

    @pytest.mark.asyncio
    async def test_open_file_windows(self, tool):
        """Test opening file on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(tool, "_find_installed_app", return_value=None):
                with patch("jarvis.tools.system_tools.os.path.isfile", return_value=True):
                    with patch(
                        "jarvis.tools.system_tools.os.startfile", create=True
                    ) as mock_startfile:
                        result = await tool.execute({"target": r"C:\Users\test\document.txt"})

                        assert result.success is True
                        mock_startfile.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_app_not_found_windows(self, tool):
        """Test opening non-existent app on Windows."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(tool, "_find_installed_app", return_value=None):
                with patch("jarvis.tools.system_tools.os.path.isfile", return_value=False):
                    result = await tool.execute({"target": "nonexistentapp"})

                    assert result.success is False
                    error_msg = result.error or result.output or ""
                    assert (
                        "not found" in error_msg.lower() or "not found" in str(result.error).lower()
                    )

    @pytest.mark.asyncio
    async def test_windows_background_mode(self, tool):
        """Test Windows background mode."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(tool, "_find_installed_app", return_value=r"C:\Windows\notepad.exe"):
                with patch("jarvis.tools.system_tools.subprocess.Popen") as mock_popen:
                    result = await tool.execute({"target": "notepad", "background": True})

                    assert result.success is True
                    mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_macos(self, tool):
        """Test macOS open command."""
        with patch.object(platform, "system", return_value="Darwin"):
            with patch("jarvis.tools.system_tools.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = await tool.execute({"target": "Safari"})

                assert result.success is True
                mock_run.assert_called_once()
                assert mock_run.call_args[0][0] == ["open", "Safari"]

    @pytest.mark.asyncio
    async def test_macos_browser_url(self, tool):
        """Test macOS browser URL."""
        with patch.object(platform, "system", return_value="Darwin"):
            with patch("jarvis.tools.system_tools.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = await tool.execute({"target": "google"})

                assert result.success is True
                call_args = mock_run.call_args[0][0]
                assert "open" in call_args
                assert "https://www.google.com" in call_args

    @pytest.mark.asyncio
    async def test_linux(self, tool):
        """Test Linux xdg-open command."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch("jarvis.tools.system_tools.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = await tool.execute({"target": "firefox"})

                assert result.success is True
                mock_run.assert_called_once()
                assert "xdg-open" in mock_run.call_args[0][0]

    @pytest.mark.asyncio
    async def test_linux_browser_url(self, tool):
        """Test Linux browser URL."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch("jarvis.tools.system_tools.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = await tool.execute({"target": "youtube"})

                assert result.success is True
                call_args = mock_run.call_args[0][0]
                assert "xdg-open" in call_args
                assert "https://youtube.com" in call_args

    @pytest.mark.asyncio
    async def test_linux_app_not_found(self, tool):
        """Test Linux app not found."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch("jarvis.tools.system_tools.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=1, stderr="Error")
                result = await tool.execute({"target": "nonexistentapp"})

                assert result.success is False


class TestOpenAppToolAliases:
    """Test all supported aliases."""

    @pytest.fixture
    def tool(self):
        return OpenAppTool()

    @pytest.mark.parametrize(
        "alias,expected",
        [
            # Basic utilities
            ("notepad", "notepad.exe"),
            ("wordpad", "wordpad.exe"),
            ("calc", "calc.exe"),
            ("calculator", "calc.exe"),
            ("paint", "mspaint.exe"),
            # Terminals
            ("cmd", "cmd.exe"),
            ("command prompt", "cmd.exe"),
            ("terminal", "cmd.exe"),
            ("powershell", "powershell.exe"),
            ("pwsh", "powershell.exe"),
            # File explorer
            ("explorer", "explorer.exe"),
            ("files", "explorer.exe"),
            ("file explorer", "explorer.exe"),
            # Browsers
            ("chrome", "chrome.exe"),
            ("google chrome", "chrome.exe"),
            ("edge", "msedge.exe"),
            ("microsoft edge", "msedge.exe"),
            ("firefox", "firefox.exe"),
            ("brave", "brave.exe"),
            ("opera", "opera.exe"),
            ("browser", "msedge.exe"),
            # Development tools
            ("vscode", "Code.exe"),
            ("vs code", "Code.exe"),
            ("code", "Code.exe"),
            # Communication
            ("discord", "discord.exe"),
            ("steam", "steam.exe"),
            ("telegram", "telegram.exe"),
            ("whatsapp", "WhatsApp.exe"),
            # Settings
            ("settings", "ms-settings:"),
            ("regedit", "regedit.exe"),
        ],
    )
    def test_alias_resolution(self, tool, alias, expected):
        """Test all aliases resolve correctly."""
        assert tool._resolve_windows_alias(alias) == expected


class TestBrowserURLs:
    """Test browser URL handling."""

    @pytest.fixture
    def tool(self):
        return OpenAppTool()

    @pytest.mark.parametrize(
        "search,expected_url",
        [
            # Search engines
            ("google", "https://www.google.com"),
            ("youtube", "https://youtube.com"),
            ("bing", "https://www.bing.com"),
            ("duckduckgo", "https://duckduckgo.com"),
            # Development
            ("github", "https://github.com"),
            ("gitlab", "https://gitlab.com"),
            ("stackoverflow", "https://stackoverflow.com"),
            ("huggingface", "https://huggingface.co"),
            # AI Services
            ("chatgpt", "https://chat.openai.com"),
            ("claude", "https://claude.ai"),
            ("gemini", "https://gemini.google.com"),
            ("ollama", "https://ollama.com"),
            ("groq", "https://console.groq.com"),
            # Communication
            ("gmail", "https://mail.google.com"),
            ("linkedin", "https://linkedin.com"),
            ("reddit", "https://reddit.com"),
            ("discord", "https://discord.com"),
            ("whatsapp", "https://web.whatsapp.com"),
            # Reference
            ("wikipedia", "https://wikipedia.org"),
            ("amazon", "https://amazon.com"),
            ("spotify", "https://spotify.com"),
        ],
    )
    def test_browser_urls(self, tool, search, expected_url):
        """Test all browser URLs resolve correctly."""
        assert tool._is_browser_search(search) == expected_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
