"""
System tray icon for JARVIS Desktop Assistant.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.desktop import DesktopAssistant

logger = logging.getLogger(__name__)


class TrayIcon:
    """System tray icon with menu."""

    def __init__(self, assistant: "DesktopAssistant"):
        self.assistant = assistant
        self.icon = None

    async def create(self) -> bool:
        """Create tray icon."""
        try:
            import pystray
            from PIL import Image, ImageDraw

            def make_image():
                """Create tray icon image."""
                img = Image.new("RGB", (64, 64), color=(30, 60, 90))
                draw = ImageDraw.Draw(img)
                draw.text((22, 20), "J", fill="white")
                return img

            def on_quit(icon, item):
                """Handle quit menu item."""
                asyncio.create_task(self.assistant.stop())

            def on_status(icon, item):
                """Handle status menu item."""
                asyncio.create_task(self._show_status())

            def on_restart(icon, item):
                """Handle restart menu item."""
                asyncio.create_task(self.assistant.restart())

            menu = pystray.Menu(
                pystray.MenuItem("JARVIS", None, enabled=False),
                pystray.MenuItem("Status", on_status),
                pystray.MenuItem("Restart", on_restart),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", on_quit),
            )

            self.icon = pystray.Icon("jarvis", make_image(), "JARVIS Desktop", menu)

            import threading

            self.thread = threading.Thread(target=self.icon.run, daemon=True)
            self.thread.start()

            return True

        except ImportError as e:
            logger.warning(f"Tray dependencies missing: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create tray: {e}")
            return False

    async def _show_status(self) -> None:
        """Show status notification."""
        status = self.assistant._get_status()
        await self.assistant._notify(status)

    def destroy(self) -> None:
        """Destroy tray icon."""
        if self.icon:
            self.icon.stop()
            self.icon = None
