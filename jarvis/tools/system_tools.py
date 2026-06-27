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
    """Open an application, URL, or file with proper verification.
    
    Features:
    - Comprehensive alias registry for common applications
    - Browser URL handling (open google → https://www.google.com)
    - Installed application detection
    - Launch verification before reporting success
    - Rich output with executable path
    """

    # Browser URL mappings (web searches)
    BROWSER_URLS = {
        "google": "https://www.google.com",
        "youtube": "https://youtube.com",
        "github": "https://github.com",
        "chatgpt": "https://chat.openai.com",
        "gmail": "https://mail.google.com",
        "linkedin": "https://linkedin.com",
        "wikipedia": "https://wikipedia.org",
        "reddit": "https://reddit.com",
        "stackoverflow": "https://stackoverflow.com",
        "twitter": "https://twitter.com",
        "facebook": "https://facebook.com",
        "amazon": "https://amazon.com",
        "netflix": "https://netflix.com",
        "discord": "https://discord.com",
        "spotify": "https://spotify.com",
        "twitch": "https://twitch.tv",
        "instagram": "https://instagram.com",
    }

    # Common Windows application aliases
    WINDOWS_ALIASES = {
        # Basic utilities
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        
        # Terminals
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "terminal": "cmd.exe",
        "powershell": "powershell.exe",
        "pwsh": "powershell.exe",
        
        # File explorer
        "explorer": "explorer.exe",
        "files": "explorer.exe",
        "file explorer": "explorer.exe",
        
        # Microsoft Office
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        
        # Browsers
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "firefox": "firefox.exe",
        "browser": "msedge.exe",
        
        # Development tools
        "vscode": "Code.exe",
        "vs code": "Code.exe",
        "visual studio code": "Code.exe",
        "code": "Code.exe",
        "notepad++": "notepad++.exe",
        "sublime": "sublime_text.exe",
        
        # Communication
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "steam": "steam.exe",
        "telegram": "telegram.exe",
        "zoom": "zoom.exe",
        "teams": "teams.exe",
        "slack": "slack.exe",
        
        # System tools
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "control panel": "control.exe",
        "settings": "ms-settings:",
        "registry": "regedit.exe",
        "regedit": "regedit.exe",
        
        # Media
        "vlc": "vlc.exe",
        "media player": "wmplayer.exe",
        "windows media player": "wmplayer.exe",
        
        # Misc
        "snipping tool": "SnippingTool.exe",
        "snip": "SnippingTool.exe",
        "character map": "charmap.exe",
    }

    # Windows search paths for installed applications
    WINDOWS_SEARCH_PATHS = [
        os.path.expandvars(r"C:\Program Files"),
        os.path.expandvars(r"C:\Program Files (x86)"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\Users\Public\Desktop",
    ]

    # Executable extensions
    EXECUTABLE_EXTENSIONS = [".exe", ".bat", ".cmd", ".ps1", ".lnk"]

    def __init__(self):
        super().__init__()
        self._installed_apps_cache: Dict[str, str] = {}

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open an application, file, or URL. Supports aliases (chrome, vscode, calculator)."

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
                    "description": "App name, file path, or URL to open. Supports aliases like 'chrome', 'vscode', 'calculator', 'google', 'youtube', etc."
                },
                "background": {
                    "type": "boolean",
                    "description": "Open in background without focus"
                }
            },
            "required": ["target"]
        }

    def _is_url(self, target: str) -> bool:
        """Check if target is a URL."""
        return target.lower().startswith(("http://", "https://", "www."))

    def _is_browser_search(self, target: str) -> Optional[str]:
        """Check if target is a browser search term.
        
        Returns URL if it matches a known browser search, else None.
        """
        lower = target.lower().strip()
        # Remove "open " prefix if present
        if lower.startswith("open "):
            lower = lower[5:].strip()
        
        # Check exact match
        if lower in self.BROWSER_URLS:
            return self.BROWSER_URLS[lower]
        
        # Check partial match
        for key, url in self.BROWSER_URLS.items():
            if key in lower or lower in key:
                return url
        
        return None

    def _resolve_windows_alias(self, target: str) -> str:
        """Resolve Windows application aliases to executable names."""
        lower_target = target.lower().strip()
        # Remove "open " prefix if present
        if lower_target.startswith("open "):
            lower_target = lower_target[5:].strip()
        
        return self.WINDOWS_ALIASES.get(lower_target, target)

    def _find_in_path(self, executable: str) -> Optional[str]:
        """Find executable in system PATH."""
        # Handle common Windows executables
        if not executable.endswith((".exe", ".bat", ".cmd")):
            executable = executable + ".exe"
        
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            if os.path.isdir(path_dir):
                candidate = os.path.join(path_dir, executable)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _find_in_windows_paths(self, executable: str) -> Optional[str]:
        """Search common Windows installation directories."""
        if not executable.endswith((".exe", ".bat", ".cmd", ".lnk")):
            search_names = [executable + ext for ext in self.EXECUTABLE_EXTENSIONS]
        else:
            search_names = [executable]
        
        for search_path in self.WINDOWS_SEARCH_PATHS:
            if not os.path.isdir(search_path):
                continue
            try:
                for root, dirs, files in os.walk(search_path):
                    for name in files:
                        if any(name.lower() == s.lower() for s in search_names):
                            return os.path.join(root, name)
            except (OSError, PermissionError):
                continue
        return None

    def _find_installed_app(self, target: str) -> Optional[str]:
        """Find an installed application on Windows."""
        if target in self._installed_apps_cache:
            return self._installed_apps_cache[target]
        
        # First try PATH
        path_exe = self._find_in_path(target)
        if path_exe:
            self._installed_apps_cache[target] = path_exe
            return path_exe
        
        # Then search common installation directories
        win_exe = self._find_in_windows_paths(target)
        if win_exe:
            self._installed_apps_cache[target] = win_exe
            return win_exe
        
        return None

    def _launch_windows(self, target: str, background: bool = False) -> tuple[bool, str, str]:
        """Launch a Windows application.
        
        Returns: (success, executable_path, message)
        """
        # Check if it's a URL
        if self._is_url(target):
            return self._launch_url(target)
        
        # Check if it's a browser search
        browser_url = self._is_browser_search(target)
        if browser_url:
            return self._launch_url(browser_url)
        
        # Resolve alias
        resolved = self._resolve_windows_alias(target)
        
        # Check for special protocols (ms-settings:, etc.)
        if ":" in resolved and not resolved.endswith((".exe", ".bat", ".cmd", ".lnk")):
            try:
                os.startfile(resolved)
                return True, resolved, f"Opened via protocol: {resolved}"
            except OSError as e:
                return False, resolved, str(e)
        
        # Try to find the executable
        executable_path = self._find_installed_app(resolved)
        
        if not executable_path:
            # Try direct path or unresolved target
            if os.path.isfile(resolved):
                executable_path = resolved
            elif os.path.isfile(resolved + ".exe"):
                executable_path = resolved + ".exe"
        
        if not executable_path:
            # Build search list for error message
            search_locations = []
            if not resolved.endswith((".exe", ".bat", ".cmd", ".lnk")):
                search_locations.append(f"  - Program Files")
                search_locations.append(f"  - Program Files (x86)")
                search_locations.append(f"  - PATH environment variable")
                search_locations.append(f"  - Start Menu")
            else:
                search_locations.append(f"  - {resolved}")
            
            return False, "", f"Application not found.\n\nSearched:\n" + "\n".join(search_locations)
        
        # Launch the application
        try:
            if background:
                subprocess.Popen(
                    [executable_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            else:
                os.startfile(executable_path)
            return True, executable_path, "SUCCESS"
        except OSError as e:
            return False, executable_path, str(e)

    def _launch_url(self, url: str) -> tuple[bool, str, str]:
        """Launch a URL in the default browser."""
        try:
            # Normalize URL
            if url.startswith("www.") and not url.startswith("http"):
                url = "https://" + url
            
            # Use startfile which opens URLs in default browser
            os.startfile(url)
            return True, url, "Opened in default browser"
        except OSError as e:
            return False, url, str(e)

    def _launch_macos(self, target: str, background: bool = False) -> tuple[bool, str, str]:
        """Launch on macOS."""
        try:
            cmd = ["open"]
            if background:
                cmd.append("-g")
            
            # Normalize URL
            if target.startswith("www.") and not target.startswith("http"):
                target = "https://" + target
            elif self._is_browser_search(target):
                url = self._is_browser_search(target)
                if url:
                    target = url
            
            cmd.append(target)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, target, "SUCCESS"
            else:
                return False, target, result.stderr or "Failed to open"
        except subprocess.TimeoutExpired:
            return False, target, "Timeout while opening"
        except Exception as e:
            return False, target, str(e)

    def _launch_linux(self, target: str, background: bool = False) -> tuple[bool, str, str]:
        """Launch on Linux."""
        try:
            cmd = ["xdg-open"]
            if background:
                cmd = ["nohup"] + cmd
            
            # Normalize URL
            if target.startswith("www.") and not target.startswith("http"):
                target = "https://" + target
            elif self._is_browser_search(target):
                url = self._is_browser_search(target)
                if url:
                    target = url
            
            cmd.append(target)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, target, "SUCCESS"
            else:
                return False, target, result.stderr or "Failed to open"
        except subprocess.TimeoutExpired:
            return False, target, "Timeout while opening"
        except Exception as e:
            return False, target, str(e)

    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResult:
        try:
            target = input_data["target"]
            background = input_data.get("background", False)

            system = platform.system()

            # Build opening message
            display_name = target.lower().replace("open ", "").strip()
            display_name = display_name.title() if display_name not in self.BROWSER_URLS else display_name.upper()
            opening_msg = f"Opening {display_name}..."

            if system == "Windows":
                success, executable, message = self._launch_windows(target, background)
            elif system == "Darwin":
                success, executable, message = self._launch_macos(target, background)
            else:
                success, executable, message = self._launch_linux(target, background)

            if success:
                output = f"{opening_msg}\n"
                if executable:
                    output += f"Executable: {executable}\n"
                output += f"Status: {message}"
                return ToolResult(success=True, output=output)
            else:
                return ToolResult(success=False, output=None, error=message)

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
