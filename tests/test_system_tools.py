"""
Tests for system tools including OpenAppTool Windows fix.
"""

import pytest
from unittest.mock import patch, MagicMock
import platform
import sys

# Mock os.startfile for testing on non-Windows
if not hasattr(__import__('os'), 'startfile'):
    def _mock_startfile(path):
        pass
    patch_os_startfile = patch.dict(sys.modules, {'os': MagicMock(startfile=_mock_startfile)})
else:
    patch_os_startfile = patch('os.startfile')

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

    @pytest.mark.asyncio
    async def test_open_notepad_windows(self, tool):
        """Test opening notepad on Windows."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True) as mock_startfile:
                result = await tool.execute({"target": "notepad"})
                
                assert result.success is True
                assert "notepad" in result.output
                mock_startfile.assert_called_once_with("notepad.exe")

    @pytest.mark.asyncio
    async def test_open_calculator_windows(self, tool):
        """Test opening calculator on Windows."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True) as mock_startfile:
                result = await tool.execute({"target": "calculator"})
                
                assert result.success is True
                mock_startfile.assert_called_once_with("calc.exe")

    @pytest.mark.asyncio
    async def test_open_powershell_windows(self, tool):
        """Test opening PowerShell on Windows."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True) as mock_startfile:
                result = await tool.execute({"target": "powershell"})
                
                assert result.success is True
                mock_startfile.assert_called_once_with("powershell.exe")

    @pytest.mark.asyncio
    async def test_open_url_windows(self, tool):
        """Test opening URL on Windows."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True) as mock_startfile:
                result = await tool.execute({"target": "https://github.com"})
                
                assert result.success is True
                mock_startfile.assert_called_once_with("https://github.com")

    @pytest.mark.asyncio
    async def test_open_file_windows(self, tool):
        """Test opening file on Windows."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True) as mock_startfile:
                result = await tool.execute({"target": "C:\\Users\\test\\document.txt"})
                
                assert result.success is True
                mock_startfile.assert_called_once_with("C:\\Users\\test\\document.txt")

    @pytest.mark.asyncio
    async def test_windows_fallback_to_cmd(self, tool):
        """Test Windows fallback to cmd /c start when os.startfile fails."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True, side_effect=OSError("Not found")):
                with patch('jarvis.tools.system_tools.subprocess.run') as mock_run:
                    result = await tool.execute({"target": "notepad"})
                    
                    assert result.success is True
                    mock_run.assert_called_once()
                    # Verify cmd /c start was used
                    call_args = mock_run.call_args[0][0]
                    assert call_args[0] == "cmd"
                    assert call_args[1] == "/c"
                    assert call_args[2] == "start"

    @pytest.mark.asyncio
    async def test_windows_background_mode(self, tool):
        """Test Windows background mode."""
        with patch.object(platform, 'system', return_value='Windows'):
            with patch('jarvis.tools.system_tools.os.startfile', create=True, side_effect=OSError("Not found")):
                with patch('jarvis.tools.system_tools.subprocess.run') as mock_run:
                    result = await tool.execute({"target": "notepad", "background": True})
                    
                    assert result.success is True
                    call_args = mock_run.call_args[0][0]
                    assert "/B" in call_args

    @pytest.mark.asyncio
    async def test_macos(self, tool):
        """Test macOS open command."""
        with patch.object(platform, 'system', return_value='Darwin'):
            with patch('jarvis.tools.system_tools.subprocess.run') as mock_run:
                result = await tool.execute({"target": "Safari"})
                
                assert result.success is True
                mock_run.assert_called_once()
                assert mock_run.call_args[0][0] == ["open", "Safari"]

    @pytest.mark.asyncio
    async def test_linux(self, tool):
        """Test Linux xdg-open command."""
        with patch.object(platform, 'system', return_value='Linux'):
            with patch('jarvis.tools.system_tools.subprocess.run') as mock_run:
                result = await tool.execute({"target": "firefox"})
                
                assert result.success is True
                mock_run.assert_called_once()
                assert "xdg-open" in mock_run.call_args[0][0]


class TestOpenAppToolAliases:
    """Test all supported aliases."""

    @pytest.fixture
    def tool(self):
        return OpenAppTool()

    @pytest.mark.parametrize("alias,expected", [
        ("notepad", "notepad.exe"),
        ("calc", "calc.exe"),
        ("calculator", "calc.exe"),
        ("cmd", "cmd.exe"),
        ("powershell", "powershell.exe"),
        ("explorer", "explorer.exe"),
        ("word", "winword.exe"),
        ("excel", "excel.exe"),
        ("browser", "msedge.exe"),
        ("edge", "msedge.exe"),
        ("chrome", "chrome.exe"),
        ("firefox", "firefox.exe"),
        ("paint", "mspaint.exe"),
        ("taskmgr", "taskmgr.exe"),
        ("taskmanager", "taskmgr.exe"),
        ("control", "control.exe"),
        ("settings", "ms-settings:"),
        ("regedit", "regedit.exe"),
    ])
    def test_alias_resolution(self, tool, alias, expected):
        """Test all aliases resolve correctly."""
        assert tool._resolve_windows_alias(alias) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
