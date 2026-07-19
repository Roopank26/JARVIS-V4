"""
Cross-platform compatibility utilities for JARVIS Desktop.
Handles platform-specific implementations transparently.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Platform information."""

    platform: Platform
    name: str
    version: str
    machine: str
    data_dir: Path
    temp_dir: Path
    audio_available: bool
    tray_available: bool
    service_available: bool


def get_platform() -> Platform:
    """Get current platform."""
    if sys.platform.startswith("linux"):
        return Platform.LINUX
    elif sys.platform == "darwin":
        return Platform.MACOS
    elif sys.platform in ("win32", "cygwin") or os.name == "nt":
        return Platform.WINDOWS
    return Platform.UNKNOWN


def get_platform_info() -> PlatformInfo:
    """Get comprehensive platform information."""
    plat = get_platform()

    # Determine directories
    if plat == Platform.WINDOWS:
        data_dir = Path(os.environ.get("APPDATA", "")) / "JARVIS"
        temp_dir = Path(os.environ.get("TEMP", "")) / "JARVIS"
    elif plat == Platform.MACOS:
        data_dir = Path.home() / "Library" / "Application Support" / "JARVIS"
        temp_dir = Path("/tmp") / "JARVIS"
    else:  # Linux
        data_dir = Path.home() / ".jarvis"
        temp_dir = Path("/tmp") / "JARVIS"

    # Check feature availability
    audio_available = True  # Assume available, check at runtime
    tray_available = plat in (Platform.WINDOWS, Platform.LINUX, Platform.MACOS)
    service_available = plat in (Platform.WINDOWS, Platform.LINUX)

    return PlatformInfo(
        platform=plat,
        name=platform.system(),
        version=platform.release(),
        machine=platform.machine(),
        data_dir=data_dir,
        temp_dir=temp_dir,
        audio_available=audio_available,
        tray_available=tray_available,
        service_available=service_available,
    )


def ensure_directories() -> None:
    """Ensure JARVIS directories exist."""
    info = get_platform_info()
    info.data_dir.mkdir(parents=True, exist_ok=True)
    info.temp_dir.mkdir(parents=True, exist_ok=True)


class CrossPlatformAudio:
    """Cross-platform audio management."""

    @staticmethod
    def get_microphones() -> list[dict[str, Any]]:
        """Get available microphones."""
        try:
            import pyaudio

            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": info["name"],
                            "channels": info["maxInputChannels"],
                        }
                    )
            p.terminate()
            return devices
        except ImportError:
            logger.warning("PyAudio not available")
            return []
        except Exception as e:
            logger.error(f"Error getting microphones: {e}")
            return []

    @staticmethod
    def get_speakers() -> list[dict[str, Any]]:
        """Get available speakers."""
        try:
            import pyaudio

            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxOutputChannels"] > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": info["name"],
                            "channels": info["maxOutputChannels"],
                        }
                    )
            p.terminate()
            return devices
        except ImportError:
            return []
        except Exception as e:
            logger.error(f"Error getting speakers: {e}")
            return []

    @staticmethod
    def test_audio() -> dict[str, Any]:
        """Test audio system."""
        plat = get_platform()
        mics = CrossPlatformAudio.get_microphones()
        speakers = CrossPlatformAudio.get_speakers()

        return {
            "platform": plat.value,
            "microphones": mics,
            "speakers": speakers,
            "has_microphone": len(mics) > 0,
            "has_speakers": len(speakers) > 0,
            "ready": len(mics) > 0 and len(speakers) > 0,
        }


class CrossPlatformTray:
    """Cross-platform system tray."""

    @staticmethod
    def is_available() -> bool:
        """Check if tray is available."""
        return get_platform() != Platform.UNKNOWN

    @staticmethod
    def create_icon() -> PILImage | None:
        """Create tray icon."""
        try:
            from PIL import Image, ImageDraw

            plat = get_platform()
            size = 256 if plat == Platform.WINDOWS else 64

            img = Image.new("RGBA", (size, size), color=(30, 60, 90, 255))
            draw = ImageDraw.Draw(img)

            # Draw circle
            margin = size // 8
            draw.ellipse([margin, margin, size - margin, size - margin], fill=(70, 130, 180, 255))

            # Draw J
            draw.text((size // 3, size // 4), "J", fill="white")

            return img
        except ImportError:
            logger.warning("PIL not available")
            return None
        except Exception as e:
            logger.error(f"Error creating icon: {e}")
            return None

    @staticmethod
    def create_menu(assistant: Any = None) -> list:
        """Create tray menu items."""
        plat = get_platform()

        if plat == Platform.WINDOWS:
            return CrossPlatformTray._windows_menu(assistant)
        elif plat == Platform.MACOS:
            return CrossPlatformTray._macos_menu(assistant)
        else:
            return CrossPlatformTray._linux_menu(assistant)

    @staticmethod
    def _windows_menu(assistant):
        """Windows tray menu."""
        try:
            import pystray

            return [
                pystray.MenuItem("JARVIS", None, enabled=False),
                pystray.MenuItem("Status", lambda i, e: _show_status(assistant)),
                pystray.MenuItem("Restart", lambda i, e: _restart(assistant)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Open", lambda i, e: _open_window(assistant)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda i, e: _quit(assistant)),
            ]
        except ImportError:
            return []

    @staticmethod
    def _macos_menu(assistant):
        """macOS tray menu."""
        return CrossPlatformTray._windows_menu(assistant)

    @staticmethod
    def _linux_menu(assistant):
        """Linux tray menu."""
        return CrossPlatformTray._windows_menu(assistant)


# Tray callback functions
async def _show_status(assistant):
    """Show status notification."""
    if assistant:
        status = assistant._get_status()
        await assistant._notify(status)


async def _restart(assistant):
    """Restart JARVIS."""
    if assistant:
        await assistant.restart()


def _open_window(assistant):
    """Open main window."""
    pass  # Implementation depends on UI


async def _quit(assistant):
    """Quit JARVIS."""
    if assistant:
        await assistant.stop()


class CrossPlatformService:
    """Cross-platform service management."""

    @staticmethod
    def is_available() -> bool:
        """Check if service management is available."""
        plat = get_platform()
        return plat in (Platform.WINDOWS, Platform.LINUX)

    @staticmethod
    def install_service() -> bool:
        """Install as system service."""
        plat = get_platform()

        if plat == Platform.WINDOWS:
            return CrossPlatformService._install_windows()
        elif plat == Platform.LINUX:
            return CrossPlatformService._install_linux()
        return False

    @staticmethod
    def _install_windows() -> bool:
        """Install Windows service."""
        try:
            from jarvis.desktop.windows_service import WindowsServiceManager

            manager = WindowsServiceManager()
            return manager.install()
        except Exception as e:
            logger.error(f"Failed to install Windows service: {e}")
            return False

    @staticmethod
    def _install_linux() -> bool:
        """Install systemd user service."""
        try:
            import sys
            from pathlib import Path

            service_content = f"""[Unit]
Description=JARVIS Desktop Assistant
After=network.target

[Service]
Type=simple
User={os.environ.get("USER", "root")}
WorkingDirectory={Path.cwd()}
ExecStart={sys.executable} -m jarvis.desktop run
Restart=on-failure
RestartSec=10
StandardOutput=append:{Path.home()}/.jarvis/jarvis.log
StandardError=append:{Path.home()}/.jarvis/jarvis.log

[Install]
WantedBy=default.target
"""
            service_path = Path.home() / ".config" / "systemd" / "user" / "jarvis.service"
            service_path.parent.mkdir(parents=True, exist_ok=True)

            with open(service_path, "w") as f:
                f.write(service_content)

            logger.info(f"Created systemd service: {service_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return False

    @staticmethod
    def uninstall_service() -> bool:
        """Uninstall system service."""
        plat = get_platform()

        if plat == Platform.WINDOWS:
            try:
                from jarvis.desktop.windows_service import WindowsServiceManager

                manager = WindowsServiceManager()
                return manager.uninstall()
            except Exception:
                return False
        elif plat == Platform.LINUX:
            try:
                from pathlib import Path

                service_path = Path.home() / ".config" / "systemd" / "user" / "jarvis.service"
                if service_path.exists():
                    service_path.unlink()
                return True
            except Exception:
                return False
        return False


class CrossPlatformVSCode:
    """Cross-platform VS Code integration."""

    @staticmethod
    def get_extension_path() -> Path:
        """Get VS Code extensions path."""
        plat = get_platform()

        if plat == Platform.WINDOWS:
            return Path(os.environ.get("USERPROFILE", "")) / ".vscode" / "extensions"
        elif plat == Platform.MACOS:
            return Path.home() / ".vscode" / "extensions"
        else:  # Linux
            return Path.home() / ".vscode" / "extensions"

    @staticmethod
    def get_settings_path() -> Path:
        """Get VS Code settings path."""
        plat = get_platform()

        if plat == Platform.WINDOWS:
            return Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"
        elif plat == Platform.MACOS:
            return (
                Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"
            )
        else:  # Linux
            return Path.home() / ".config" / "Code" / "User" / "settings.json"

    @staticmethod
    def get_executable_path() -> Path | None:
        """Find VS Code executable."""
        plat = get_platform()

        candidates = []

        if plat == Platform.WINDOWS:
            candidates = [
                Path(
                    os.environ.get("LOCALAPPDATA", "") + "\\Programs\\Microsoft VS Code\\Code.exe"
                ),
                Path("C:\\Program Files\\Microsoft VS Code\\Code.exe"),
                Path("C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"),
            ]
        elif plat == Platform.MACOS:
            candidates = [
                Path("/Applications/Visual Studio Code.app/Contents/MacOS/Electron"),
                Path.home() / "Applications/Visual Studio Code.app/Contents/MacOS/Electron",
            ]
        else:  # Linux
            candidates = [
                Path("/usr/bin/code"),
                Path("/usr/local/bin/code"),
                Path.home() / ".local/bin/code",
            ]

        for path in candidates:
            if path.exists():
                return path

        return None
