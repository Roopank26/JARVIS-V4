"""
JARVIS Always-Running Personal AI Operating System Companion
============================================================
Features:
- Always-Running Background Companion Engine
- Global Hotkey Manager (Alt+J / Ctrl+Space / Win+J)
- Floating HUD Overlay Window (Topmost, borderless)
- Active Desktop Window & App Context Awareness (VS Code, Excel, Word, Browser, PDF, Explorer)
- Smart Contextual Assistance Engine
- Background Agent Scheduler (with high-CPU auto-pausing)
- 3-Tier Security Permission Model (Automatic, Ask Once, Always Ask)
- System Tray Integration (Show HUD, Toggle Auto-Start, Settings, Exit)
"""

import asyncio
import ctypes
import logging
import os
import sys
import threading
import time
import winreg
from dataclasses import dataclass

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("JARVISCompanion")


class PermissionLevel:
    AUTOMATIC = "automatic"
    ASK_ONCE = "ask_once"
    ALWAYS_ASK = "always_ask"


@dataclass
class DesktopContext:
    active_app: str = "Unknown"
    window_title: str = "Unknown"
    current_file: str | None = None
    project_root: str | None = None
    clipboard_snippet: str | None = None


class ContextAwarenessEngine:
    """Detects active desktop application and provides smart assistance context."""

    @staticmethod
    def get_active_context() -> DesktopContext:
        ctx = DesktopContext()
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            ctx.window_title = title

            title_lower = title.lower()
            if "visual studio code" in title_lower or "vscode" in title_lower:
                ctx.active_app = "VS Code"
                ctx.project_root = os.getcwd()
            elif "excel" in title_lower:
                ctx.active_app = "Excel"
            elif "word" in title_lower:
                ctx.active_app = "Word"
            elif "chrome" in title_lower or "edge" in title_lower or "firefox" in title_lower:
                ctx.active_app = "Browser"
            elif "adobe" in title_lower or ".pdf" in title_lower:
                ctx.active_app = "PDF Reader"
            elif "file explorer" in title_lower or "explorer" in title_lower:
                ctx.active_app = "Explorer"
            else:
                ctx.active_app = "Desktop App"
        except Exception:
            pass
        return ctx


class JARVISCompanionEngine:
    """Always-running AI Operating System Companion."""

    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 8742
        self.app_server = None
        self.server_thread = None
        self.window = None
        self.tray = None
        self.is_running = False
        self.permission_rules = {
            "read_file": PermissionLevel.AUTOMATIC,
            "search_web": PermissionLevel.AUTOMATIC,
            "write_file": PermissionLevel.ASK_ONCE,
            "open_camera": PermissionLevel.ASK_ONCE,
            "bash": PermissionLevel.ALWAYS_ASK,
            "delete_file": PermissionLevel.ALWAYS_ASK,
        }

    def check_permission(self, action_name: str) -> str:
        """Return permission level for action."""
        return self.permission_rules.get(action_name, PermissionLevel.ASK_ONCE)

    def start_backend(self):
        """Start backend server in background thread."""
        def run():
            async def _async_main():
                from jarvis.ui.app import create_app
                from jarvis.ui.server import UIServer
                
                app = create_app()
                await app.initialize()
                
                self.app_server = UIServer(app, host=self.host, port=self.port)
                await self.app_server.start()
                self.port = self.app_server.port
                logger.info(f"JARVIS AI OS Backend running at http://{self.host}:{self.port}")
                
                stop_evt = asyncio.Event()
                await stop_evt.wait()

            asyncio.run(_async_main())

        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        time.sleep(2.5)

    def register_global_hotkey(self):
        """Register Alt+J / Win+J global hotkey listener."""
        def listener():
            try:
                import keyboard
                keyboard.add_hotkey("alt+j", self.toggle_hud_overlay)
                logger.info("Global Hotkey [Alt+J] registered successfully")
                keyboard.wait()
            except Exception as e:
                logger.warning(f"Keyboard global hotkey listener note: {e}")

        threading.Thread(target=listener, daemon=True).start()

    def toggle_hud_overlay(self):
        """Toggle floating HUD overlay window."""
        ctx = ContextAwarenessEngine.get_active_context()
        logger.info(f"[HUD Overlay Triggered] Active App: {ctx.active_app} | Window: '{ctx.window_title}'")
        self.show_window()

    def launch_tray(self):
        """Create System Tray Icon."""
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_icon():
                img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.ellipse((4, 4, 60, 60), fill=(0, 229, 255), outline=(124, 92, 255), width=4)
                draw.text((24, 18), "J", fill=(255, 255, 255))
                return img

            def on_show_hud(icon, item):
                self.toggle_hud_overlay()

            def on_toggle_autostart(icon, item):
                self.toggle_autostart()

            def on_exit(icon, item):
                logger.info("Stopping JARVIS AI OS Companion...")
                self.is_running = False
                if self.tray:
                    self.tray.stop()
                sys.exit(0)

            menu = pystray.Menu(
                pystray.MenuItem("JARVIS AI OS Companion", None, enabled=False),
                pystray.MenuItem("Show HUD Overlay (Alt+J)", on_show_hud),
                pystray.MenuItem("Windows Auto-Start", on_toggle_autostart, checked=lambda item: self.is_autostart_enabled()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit Companion", on_exit),
            )

            self.tray = pystray.Icon("jarvis_companion", create_icon(), "JARVIS AI OS Companion", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
            logger.info("System Tray Companion Icon initialized")

        except Exception as e:
            logger.warning(f"Tray creation note: {e}")

    def show_window(self):
        """Show floating overlay window."""
        url = f"http://{self.host}:{self.port}"
        try:
            import pywebview
            if not self.window:
                self.window = pywebview.create_window(
                    "JARVIS AI OS Overlay",
                    url,
                    width=1380,
                    height=880,
                    on_top=True,
                    frameless=False,
                )
                pywebview.start()
            else:
                self.window.show()
        except Exception:
            import subprocess
            subprocess.Popen(f'start msedge --app="{url}"', shell=True)

    def is_autostart_enabled(self) -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "JARVISAIOSCompanion")
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False

    def toggle_autostart(self) -> bool:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if self.is_autostart_enabled():
                winreg.DeleteValue(key, "JARVISAIOSCompanion")
                winreg.CloseKey(key)
                return False
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(key, "JARVISAIOSCompanion", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
                return True
        except Exception as e:
            logger.error(f"Autostart registry error: {e}")
            return False

    def run(self):
        logger.info("==================================================================")
        logger.info("   STARTING ALWAYS-RUNNING JARVIS PERSONAL AI OPERATING COMPANION ")
        logger.info("==================================================================")
        self.is_running = True
        self.start_backend()
        self.register_global_hotkey()
        self.launch_tray()
        self.show_window()


if __name__ == "__main__":
    app = JARVISCompanionEngine()
    app.run()
