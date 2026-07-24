"""
Universal Computer Agent for JARVIS.

Extends DesktopAutomation into full computer control.

Capabilities:
- Open / close applications
- Read windows
- Control mouse
- Control keyboard
- Interact with dialogs
- Manage clipboard
- File management
- Terminal control
- IDE interaction
- Browser interaction
- Multi-monitor awareness
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from jarvis.desktop.automation import DesktopAutomation, get_desktop_automation

logger = logging.getLogger(__name__)


@dataclass
class ComputerState:
    active_window: str | None = None
    clipboard_text: str = ""
    monitors: int = 1
    open_apps: list[str] = field(default_factory=list)
    platform: str = platform.system().lower()


@dataclass
class ActionResult:
    success: bool
    output: str = ""
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class UniversalComputerAgent:
    """
    Full computer control for JARVIS.

    The computer becomes another tool for JARVIS.
    """

    def __init__(self, desktop: DesktopAutomation | None = None) -> None:
        self._desktop = desktop or get_desktop_automation()
        self._state = ComputerState(platform=self._desktop.system)

    async def open_application(self, app_name: str) -> ActionResult:
        try:
            success = await self._desktop.launch_app(app_name)
            if success:
                self._state.open_apps.append(app_name)
                return ActionResult(success=True, output=f"Opened {app_name}")
            return ActionResult(success=False, error=f"Failed to open {app_name}")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def close_application(self, app_name: str) -> ActionResult:
        try:
            windows = await self._desktop.list_windows()
            for win in windows:
                if app_name.lower() in win.title.lower() or app_name.lower() in win.process.lower():
                    success = await self._desktop.close_window(win.title)
                    if success and app_name in self._state.open_apps:
                        self._state.open_apps.remove(app_name)
                    return ActionResult(success=success, output=f"Closed {win.title}" if success else f"Failed to close {win.title}")
            return ActionResult(success=False, error=f"Application {app_name} not found")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def read_windows(self) -> list[dict[str, Any]]:
        try:
            windows = await self._desktop.list_windows()
            return [
                {
                    "title": win.title,
                    "process": win.process,
                    " focused": win.focused,
                    "x": win.x,
                    "y": win.y,
                    "width": win.width,
                    "height": win.height,
                }
                for win in windows
            ]
        except Exception as exc:
            logger.error("Error reading windows: %s", exc)
            return []

    async def focus_window(self, title: str) -> ActionResult:
        try:
            success = await self._desktop.focus_window(title)
            if success:
                self._state.active_window = title
                return ActionResult(success=True, output=f"Focused {title}")
            return ActionResult(success=False, error=f"Window {title} not found")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def control_mouse(self, action: str, x: int | None = None, y: int | None = None, button: str = "left") -> ActionResult:
        try:
            if self._desktop.is_windows:
                if action == "move":
                    ps_script = (
                        f"[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y})"
                    )
                    subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True, timeout=2)
                    return ActionResult(success=True, output=f"Moved mouse to ({x}, {y})")
                elif action == "click":
                    click_cmd = {
                        "left": "[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y}); "
                                "[System.Windows.Forms.SendKeys]::SendWait('{LEFTCLICK}')",
                        "right": "[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y}); "
                                 "[System.Windows.Forms.SendKeys]::SendWait('{RIGHTCLICK}')",
                        "double": "[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y}); "
                                  "[System.Windows.Forms.SendKeys]::SendWait('{LEFTCLICK}{LEFTCLICK}')",
                    }.get(button, "")
                    if click_cmd:
                        subprocess.run(["powershell", "-Command", click_cmd], check=True, capture_output=True, timeout=2)
                        return ActionResult(success=True, output=f"Clicked {button} at ({x}, {y})")
                elif action == "scroll":
                    import math
                    scroll_cmd = (
                        f"[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x}, {y}); "
                        f"[System.Windows.Forms.SendKeys]::SendWait('{{{int(math.copysign(5, y or 1)) * 120}}}')"
                    )
                    subprocess.run(["powershell", "-Command", scroll_cmd], check=True, capture_output=True, timeout=2)
                    return ActionResult(success=True, output=f"Scrolled at ({x}, {y})")
            return ActionResult(success=False, error=f"Mouse action {action} not supported on {self._desktop.system}")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def control_keyboard(self, action: str, keys: list[str] | None = None, text: str | None = None) -> ActionResult:
        try:
            if action == "type" and text:
                success = await self._desktop.type_text(text)
                return ActionResult(success=success, output=f"Typed {len(text)} characters" if success else "Failed to type")
            elif action == "hotkey" and keys:
                success = await self._desktop.execute_hotkey(keys)
                return ActionResult(success=success, output=f"Pressed {'+'.join(keys)}" if success else "Failed to press keys")
            return ActionResult(success=False, error="Invalid keyboard action")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def interact_dialog(self, action: str, button_name: str | None = None, text: str | None = None) -> ActionResult:
        try:
            if self._desktop.is_windows:
                if action == "ok":
                    subprocess.run(["powershell", "-Command", "[System.Windows.Forms.SendKeys]::SendWait('%o')"], capture_output=True, timeout=2)
                    return ActionResult(success=True, output="Clicked OK")
                elif action == "cancel":
                    subprocess.run(["powershell", "-Command", "[System.Windows.Forms.SendKeys]::SendWait('%c')"], capture_output=True, timeout=2)
                    return ActionResult(success=True, output="Clicked Cancel")
                elif action == "enter_text":
                    subprocess.run(
                        ["powershell", "-Command", f"[System.Windows.Forms.SendKeys]::SendWait('{text}')"],
                        capture_output=True, timeout=2,
                    )
                    return ActionResult(success=True, output="Entered text in dialog")
                elif action == "close":
                    subprocess.run(["powershell", "-Command", "[System.Windows.Forms.SendKeys]::SendWait('%{F4}')"], capture_output=True, timeout=2)
                    return ActionResult(success=True, output="Closed dialog")
            return ActionResult(success=False, error="Dialog interaction not supported")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def manage_clipboard(self, action: str, text: str | None = None) -> ActionResult:
        try:
            if action == "get":
                clipboard = await self._desktop.get_clipboard()
                self._state.clipboard_text = clipboard
                return ActionResult(success=True, output=clipboard)
            elif action == "set" and text is not None:
                success = await self._desktop.set_clipboard(text)
                if success:
                    self._state.clipboard_text = text
                return ActionResult(success=success, output=f"Copied {len(text)} characters" if success else "Failed to set clipboard")
            return ActionResult(success=False, error="Invalid clipboard action")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def manage_files(self, action: str, path: str, destination: str | None = None) -> ActionResult:
        try:
            if action == "open":
                success = await self._desktop.open_folder(path)
                return ActionResult(success=success, output=f"Opened {path}" if success else f"Failed to open {path}")
            elif action == "search":
                results = await self._desktop.search_files("*", directory=path)
                return ActionResult(success=True, output=f"Found {len(results)} files", details={"results": results})
            elif action == "delete":
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    return ActionResult(success=True, output=f"Deleted {path}")
                return ActionResult(success=False, error=f"Path {path} not found")
            elif action == "move" and destination:
                shutil.move(path, destination)
                return ActionResult(success=True, output=f"Moved {path} to {destination}")
            return ActionResult(success=False, error="Invalid file action")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def control_terminal(self, command: str, shell: str | None = None) -> ActionResult:
        try:
            if self._desktop.is_windows:
                cmd = ["powershell", "-Command", command] if not shell else [shell, command]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=(shell == "cmd"))
                return ActionResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                )
            return ActionResult(success=False, error="Terminal control not supported on this platform")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def capture_screen(self) -> ActionResult:
        try:
            path = await self._desktop.take_screenshot()
            if path:
                return ActionResult(success=True, output=path)
            return ActionResult(success=False, error="Failed to capture screen")
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

    async def get_state(self) -> ComputerState:
        try:
            windows = await self._desktop.list_windows()
            focused = [w for w in windows if w.focused]
            if focused:
                self._state.active_window = focused[0].title
            self._state.open_apps = list({w.process for w in windows if w.process})
        except Exception:
            pass
        return self._state

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": True,
            "platform": self._state.platform,
            "open_apps": len(self._state.open_apps),
        }


_computer_agent: UniversalComputerAgent | None = None


def get_computer_agent() -> UniversalComputerAgent:
    global _computer_agent
    if _computer_agent is None:
        _computer_agent = UniversalComputerAgent()
    return _computer_agent


def reset_computer_agent() -> None:
    global _computer_agent
    _computer_agent = None
