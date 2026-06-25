"""
Desktop Automation Module for JARVIS.
Provides cross-platform desktop control capabilities.
"""

import asyncio
import logging
import platform
import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Window information."""
    title: str
    process: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    focused: bool = False


class DesktopAutomation:
    """
    Cross-platform desktop automation.
    
    Supports:
    - Window management (list, focus, move, resize, minimize, maximize)
    - Application launching
    - Clipboard operations
    - Screenshot capture
    - System commands
    """

    def __init__(self):
        self.system = platform.system().lower()
        self._clipboard_content: str = ""

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self.system == "windows"

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self.system == "darwin"

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self.system == "linux"

    async def list_windows(self) -> List[WindowInfo]:
        """
        List all open windows.
        
        Returns:
            List of WindowInfo objects
        """
        windows = []
        
        try:
            if self.is_linux:
                # Use wmctrl on Linux
                result = subprocess.run(
                    ["wmctrl", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        parts = line.split(None, 3)
                        if len(parts) >= 4:
                            windows.append(WindowInfo(
                                title=parts[3],
                                process=""
                            ))
                            
            elif self.is_macos:
                # Use osascript on macOS
                script = '''
                tell application "System Events"
                    set windowList to every window of every process
                    set output to ""
                    repeat with win in windowList
                        set winName to name of win
                        set appName to name of application of win
                        set output to output & winName & "|" & appName & "\n"
                    end repeat
                    return output
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if "|" in line:
                            title, app = line.rsplit("|", 1)
                            windows.append(WindowInfo(title=title, process=app))
                            
            elif self.is_windows:
                # Use PowerShell on Windows
                script = '''
                Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                using System.Text;
                public class Win32 {
                    [DllImport("user32.dll")]
                    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
                    [DllImport("user32.dll")]
                    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
                    [DllImport("user32.dll")]
                    public static extern bool IsWindowVisible(IntPtr hWnd);
                    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
                }
"@
                $windows = @()
                $callback = [Win32+EnumWindowsProc]{ param($hWnd,$lParam)
                    $sb = New-Object System.Text.StringBuilder 256
                    [void][Win32]::GetWindowText($hWnd, $sb, 256)
                    $title = $sb.ToString()
                    if ($title) { $script:windows += $title }
                    return $true
                }
                [void][Win32]::EnumWindows($callback, [IntPtr]::Zero)
                $windows | Where-Object { $_ } | ForEach-Object { $_ }
                '''
                result = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    for title in result.stdout.strip().split("\n"):
                        if title.strip():
                            windows.append(WindowInfo(title=title.strip(), process=""))
                            
        except FileNotFoundError:
            logger.warning("Window listing tool not found")
        except Exception as e:
            logger.error(f"Error listing windows: {e}")
        
        return windows

    async def focus_window(self, title: str) -> bool:
        """
        Focus a window by title.
        
        Args:
            title: Window title or partial title to match
            
        Returns:
            True if successful
        """
        try:
            if self.is_linux:
                result = subprocess.run(
                    ["wmctrl", "-a", title],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            elif self.is_macos:
                script = f'''
                tell application "System Events"
                    set winList to every window whose name contains "{title}"
                    if (count of winList) > 0 then
                        perform action "AXRaise" of winList[1]
                    end if
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            elif self.is_windows:
                # Use PowerShell to find and focus window
                script = f'''
                Add-Type @" 
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")] 
                    public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")]
                    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
                }}
"@
                $hwnd = [Win32]::FindWindow([NullString]::Value, "{title}")
                if ($hwnd -ne [IntPtr]::Zero) {{
                    [void][Win32]::SetForegroundWindow($hwnd)
                    $true
                }}
                '''
                result = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    timeout=5
                )
                return "$true" in result.stdout.lower()
                
        except Exception as e:
            logger.error(f"Error focusing window: {e}")
            return False
        
        return False

    async def minimize_window(self, title: str) -> bool:
        """Minimize a window."""
        try:
            if self.is_linux:
                result = subprocess.run(
                    ["xdotool", "search", "--name", title, "minimize"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            # Similar for other platforms...
        except Exception as e:
            logger.error(f"Error minimizing window: {e}")
        return False

    async def close_window(self, title: str) -> bool:
        """
        Close a window by title.
        
        Args:
            title: Window title to close
            
        Returns:
            True if successful
        """
        try:
            if self.is_linux:
                # Find window ID and close it
                result = subprocess.run(
                    ["xdotool", "search", "--name", title, "windowclose"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            elif self.is_macos:
                script = f'''
                tell application "System Events"
                    set winList to every window whose name contains "{title}"
                    if (count of winList) > 0 then
                        click button 1 of winList[1]
                    end if
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
                
            elif self.is_windows:
                # Alt+F4 equivalent
                await self.focus_window(title)
                await asyncio.sleep(0.2)
                subprocess.run(
                    ["xdotool", "key", "Alt+F4"] if self.is_linux else ["Alt+F4"],
                    shell=True,
                    timeout=2
                )
                return True
                
        except Exception as e:
            logger.error(f"Error closing window: {e}")
        
        return False

    async def launch_app(self, app_name: str) -> bool:
        """
        Launch an application.
        
        Args:
            app_name: Name of the application to launch
            
        Returns:
            True if successful
        """
        try:
            if self.is_linux:
                # Try common launch methods
                for cmd in [
                    ["xdg-open", app_name],
                    [app_name],
                    ["gnome-open", app_name],
                    ["kde-open", app_name],
                ]:
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
                    except FileNotFoundError:
                        continue
                        
            elif self.is_macos:
                result = subprocess.run(
                    ["open", "-a", app_name],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
                
            elif self.is_windows:
                subprocess.Popen(
                    ["start", "", app_name],
                    shell=True,
                    stdout=subprocess.DEVNULL
                )
                return True
                
        except Exception as e:
            logger.error(f"Error launching app: {e}")
        
        return False

    async def get_clipboard(self) -> str:
        """
        Get clipboard content.
        
        Returns:
            Clipboard text content
        """
        try:
            if self.is_linux:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout
                    
            elif self.is_macos:
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout
                    
            elif self.is_windows:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return result.stdout
                    
        except Exception as e:
            logger.error(f"Error getting clipboard: {e}")
        
        return ""

    async def set_clipboard(self, text: str) -> bool:
        """
        Set clipboard content.
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            True if successful
        """
        try:
            if self.is_linux:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-i"],
                    input=text,
                    text=True,
                    timeout=2
                )
                return True
                
            elif self.is_macos:
                subprocess.run(
                    ["pbcopy"],
                    input=text,
                    text=True,
                    timeout=2
                )
                return True
                
            elif self.is_windows:
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                    capture_output=True,
                    timeout=2
                )
                return True
                
        except Exception as e:
            logger.error(f"Error setting clipboard: {e}")
        
        return False

    async def take_screenshot(self, path: Optional[Path] = None) -> Optional[str]:
        """
        Take a screenshot.
        
        Args:
            path: Optional output path (defaults to ~/Pictures/screenshot.png)
            
        Returns:
            Path to screenshot file or None on failure
        """
        if path is None:
            path = Path.home() / "Pictures" / "screenshot.png"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.is_linux:
                # Try gnome-screenshot, scrot, or import
                for cmd in [
                    ["gnome-screenshot", "-f", str(path)],
                    ["scrot", str(path)],
                    ["import", "-window", "root", str(path)],
                ]:
                    result = subprocess.run(cmd, capture_output=True, timeout=5)
                    if result.returncode == 0 and path.exists():
                        return str(path)
                        
            elif self.is_macos:
                result = subprocess.run(
                    ["screencapture", str(path)],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and path.exists():
                    return str(path)
                    
            elif self.is_windows:
                # Use PowerShell
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.Screen]::PrimaryScreen
                $bitmap = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen([System.Drawing.Point]::Empty, [System.Drawing.Point]::Empty, $bitmap.Size)
                $bitmap.Save("{path}")
                '''
                result = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0 and path.exists():
                    return str(path)
                    
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
        
        return None

    async def execute_hotkey(self, keys: List[str]) -> bool:
        """
        Execute a hotkey combination.
        
        Args:
            keys: List of keys (e.g., ["ctrl", "c"] for Ctrl+C)
            
        Returns:
            True if successful
        """
        try:
            # Normalize keys
            key_str = "+".join(keys)
            
            if self.is_linux:
                subprocess.run(
                    ["xdotool", "key", key_str],
                    capture_output=True,
                    timeout=2
                )
                return True
                
            elif self.is_macos:
                script = f'''
                tell application "System Events"
                    keystroke "{keys[-1]}" using {{{"+".join(["command down" if k == "ctrl" else k for k in keys]).replace("ctrl", "command")} down}}
                end tell
                '''
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=2
                )
                return True
                
            elif self.is_windows:
                subprocess.run(
                    ["xdotool", "key", key_str] if self.is_linux else key_str.split("+"),
                    shell=True,
                    timeout=2
                )
                return True
                
        except Exception as e:
            logger.error(f"Error executing hotkey: {e}")
        
        return False

    async def type_text(self, text: str) -> bool:
        """
        Type text at the current cursor position.
        
        Args:
            text: Text to type
            
        Returns:
            True if successful
        """
        try:
            if self.is_linux:
                # Escape special characters
                escaped = text.replace("'", "'\"'\"'")
                subprocess.run(
                    ["xdotool", "type", "--delay", "50", escaped],
                    capture_output=True,
                    timeout=len(text) * 0.1
                )
                return True
                
            elif self.is_macos:
                script = f'''
                tell application "System Events"
                    keystroke "{text.replace('"', '\\"')}"
                end tell
                '''
                subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=len(text) * 0.1
                )
                return True
                
            elif self.is_windows:
                subprocess.run(
                    ["powershell", "-Command", f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{text}')"],
                    capture_output=True,
                    timeout=len(text) * 0.1
                )
                return True
                
        except Exception as e:
            logger.error(f"Error typing text: {e}")
        
        return False

    def format_windows_list(self, windows: List[WindowInfo]) -> str:
        """Format window list for display."""
        if not windows:
            return "No windows found."
        
        lines = ["[Open Windows]", "=" * 40, ""]
        for i, win in enumerate(windows, 1):
            lines.append(f"{i}. {win.title}")
            if win.process:
                lines.append(f"   App: {win.process}")
        
        return "\n".join(lines)


# Global instance
_desktop_automation: Optional[DesktopAutomation] = None


def get_desktop_automation() -> DesktopAutomation:
    """Get global desktop automation instance."""
    global _desktop_automation
    if _desktop_automation is None:
        _desktop_automation = DesktopAutomation()
    return _desktop_automation
