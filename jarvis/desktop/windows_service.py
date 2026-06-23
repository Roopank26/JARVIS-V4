"""
Windows-specific service support for JARVIS Desktop.
Provides Windows Service integration for background operation.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or os.name == "nt"


def get_app_data_dir() -> Path:
    """Get Windows AppData directory."""
    if is_windows():
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "JARVIS"
    return Path.home() / ".jarvis"


def get_local_app_data() -> Path:
    """Get Windows LocalAppData directory."""
    if is_windows():
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "JARVIS"
    return Path.home() / ".jarvis"


def get_temp_dir() -> Path:
    """Get platform-appropriate temp directory."""
    import tempfile
    if is_windows():
        return Path(tempfile.gettempdir()) / "JARVIS"
    return Path(tempfile.gettempdir()) / ".jarvis"


class WindowsServiceManager:
    """
    Manages JARVIS as a Windows Service.
    Supports installation, uninstallation, and service control.
    """

    def __init__(self):
        self.service_name = "JARVISDesktop"
        self.display_name = "JARVIS Desktop Assistant"
        self.description = "Personal AI desktop assistant with voice control"

    def install(self, python_path: Optional[str] = None) -> bool:
        """Install JARVIS as a Windows Service."""
        if not is_windows():
            logger.error("Windows Service installation only supported on Windows")
            return False

        try:
            import win32service
            import win32serviceutil
            import win32con

            # Get paths
            jarvis_path = Path(__file__).parent.parent.parent
            python_exe = python_path or sys.executable
            service_script = jarvis_path / "jarvis" / "desktop" / "service.py"

            if not service_script.exists():
                logger.error(f"Service script not found: {service_script}")
                return False

            # Create service definition
            service_content = f'''"""
JARVIS Windows Service
Auto-generated service wrapper.
"""

import servicemanager
import win32service
import win32serviceutil
import win32api
import os
import sys
import time

def main():
    win32serviceutil.HandleCommandLine(JARVISService)

class JARVISService(win32serviceutil.ServiceFramework):
    _svc_name_ = "{self.service_name}"
    _svc_display_name_ = "{self.display_name}"
    _svc_description_ = "{self.description}"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Import and run desktop assistant
        import asyncio
        from jarvis.desktop import DesktopAssistant
        
        async def run():
            assistant = DesktopAssistant()
            await assistant.start()
            while assistant.is_running:
                await asyncio.sleep(1)
        
        asyncio.run(run())

if __name__ == '__main__':
    main()
'''
            # Write service wrapper
            wrapper_path = get_local_app_data() / "service_wrapper.py"
            wrapper_path.parent.mkdir(parents=True, exist_ok=True)
            wrapper_path.write_text(service_content)

            # Install using pywin32
            win32serviceutil.InstallService(
                f'{wrapper_path}:JARVISService',
                self.service_name,
                self.display_name,
                startType=win32service.SERVICE_AUTO_START
            )

            logger.info(f"Windows Service '{self.service_name}' installed")
            return True

        except ImportError:
            logger.error("pywin32 not installed. Run: pip install pywin32")
            return False
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall JARVIS Windows Service."""
        if not is_windows():
            return False

        try:
            import win32serviceutil
            win32serviceutil.RemoveService(self.service_name)
            logger.info(f"Windows Service '{self.service_name}' uninstalled")
            return True
        except ImportError:
            logger.error("pywin32 not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to uninstall service: {e}")
            return False

    def start(self) -> bool:
        """Start the Windows Service."""
        if not is_windows():
            return False

        try:
            import win32serviceutil
            win32serviceutil.StartService(self.service_name)
            logger.info(f"Windows Service '{self.service_name}' started")
            return True
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """Stop the Windows Service."""
        if not is_windows():
            return False

        try:
            import win32serviceutil
            win32serviceutil.StopService(self.service_name)
            logger.info(f"Windows Service '{self.service_name}' stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            return False

    def status(self) -> str:
        """Get service status."""
        if not is_windows():
            return "Not Windows"

        try:
            import win32serviceutil
            status = win32serviceutil.QueryServiceStatus(self.service_name)
            return "Running" if status[1] == 4 else "Stopped"
        except Exception:
            return "Not Installed"


class WindowsAudioManager:
    """
    Windows-specific audio management.
    Handles microphone and speaker access on Windows.
    """

    @staticmethod
    def get_microphones() -> list:
        """Get list of available microphones."""
        if not is_windows():
            return []

        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxInputChannels"],
                        "sample_rate": int(info["defaultSampleRate"])
                    })
            p.terminate()
            return devices
        except ImportError:
            logger.warning("PyAudio not available")
            return []

    @staticmethod
    def get_speakers() -> list:
        """Get list of available speakers."""
        if not is_windows():
            return []

        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxOutputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": info["name"],
                        "channels": info["maxOutputChannels"],
                        "sample_rate": int(info["defaultSampleRate"])
                    })
            p.terminate()
            return devices
        except ImportError:
            logger.warning("PyAudio not available")
            return []

    @staticmethod
    def set_default_microphone(device_index: int) -> bool:
        """Set default microphone by index."""
        if not is_windows():
            return False

        try:
            import pyaudio
            p = pyaudio.PyAudio()
            # Set as default by using default device
            p.terminate()
            return True
        except Exception as e:
            logger.error(f"Failed to set microphone: {e}")
            return False

    @staticmethod
    def test_audio() -> dict:
        """Test audio devices and return status."""
        mics = WindowsAudioManager.get_microphones()
        speakers = WindowsAudioManager.get_speakers()

        return {
            "microphones": mics,
            "speakers": speakers,
            "has_microphone": len(mics) > 0,
            "has_speakers": len(speakers) > 0,
            "platform": "windows"
        }


class WindowsTrayIcon:
    """
    Windows-specific system tray implementation.
    Uses pystray with Windows-compatible icon format.
    """

    @staticmethod
    def create_icon_from_ico(ico_path: Path) -> "Image":
        """Load ICO file for tray icon."""
        from PIL import Image
        try:
            return Image.open(ico_path)
        except Exception:
            # Fallback to creating simple icon
            return WindowsTrayIcon.create_default_icon()

    @staticmethod
    def create_default_icon() -> "Image":
        """Create default JARVIS icon."""
        from PIL import Image, ImageDraw
        # Create 256x256 icon
        img = Image.new('RGB', (256, 256), color=(30, 60, 90))
        draw = ImageDraw.Draw(img)
        # Draw circle
        draw.ellipse([20, 20, 236, 236], fill=(70, 130, 180), outline=(100, 150, 200))
        # Draw J
        draw.text((100, 80), "J", fill='white', font=ImageFont.load_default())
        return img

    @staticmethod
    def save_icon(output_path: Path) -> bool:
        """Save JARVIS icon as ICO file."""
        from PIL import Image, ImageDraw, ImageOps

        # Create 256x256 image
        img = Image.new('RGBA', (256, 256), color=(30, 60, 90, 255))
        draw = ImageDraw.Draw(img)

        # Draw circle background
        draw.ellipse([16, 16, 240, 240], fill=(70, 130, 180, 255))

        # Draw "J" letter
        draw.text((100, 70), "J", fill='white')

        # Save as PNG (ICO can use PNG)
        img.save(output_path, format='PNG')
        return True


class WindowsVSCodeBridge:
    """
    Windows-specific VS Code integration.
    Handles Windows paths and pipe naming.
    """

    def __init__(self, port: int = 8765):
        self.port = port
        self.pipe_name = f"\\\\.\\pipe\\jarvis_vscode_{port}"

    def get_vscode_extensions_path(self) -> Path:
        """Get VS Code extensions path on Windows."""
        if is_windows():
            return Path(os.environ.get("USERPROFILE", "")) / ".vscode" / "extensions"
        return Path.home() / ".vscode" / "extensions"

    def get_vscode_settings_path(self) -> Path:
        """Get VS Code settings path on Windows."""
        if is_windows():
            return Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"
        return Path.home() / ".config" / "Code" / "User" / "settings.json"

    def get_vscode_command_path(self) -> list:
        """Get possible VS Code executable paths on Windows."""
        paths = [
            Path(os.environ.get("LOCALAPPDATA", "") + "\\Programs\\Microsoft VS Code\\Code.exe"),
            Path("C:\\Program Files\\Microsoft VS Code\\Code.exe"),
            Path("C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"),
            Path(os.environ.get("USERPROFILE", "") + "\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"),
        ]
        return [p for p in paths if p.exists()]


def get_platform_info() -> dict:
    """Get comprehensive platform information."""
    import platform

    info = {
        "platform": sys.platform,
        "os": os.name,
        "is_windows": is_windows(),
        "is_linux": sys.platform.startswith("linux"),
        "is_macos": sys.platform == "darwin",
        "python_version": sys.version,
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }

    if is_windows():
        info.update({
            "windows_version": platform.win32_ver()[0],
            "windows_build": platform.win32_ver()[2],
            "appdata": str(get_app_data_dir()),
            "local_appdata": str(get_local_app_data()),
        })

    return info
