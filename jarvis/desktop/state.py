"""
Persistent state management for JARVIS Desktop.
Ensures state survives restarts and crashes.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Application state that persists across restarts."""
    version: str = "3.0.0"
    last_start: Optional[str] = None
    last_stop: Optional[str] = None
    crash_count: int = 0
    last_crash: Optional[str] = None
    restart_count: int = 0
    total_uptime_seconds: float = 0.0
    memory_entries: int = 0
    project_count: int = 0
    knowledge_entries: int = 0
    plugins_loaded: int = 0
    tasks_scheduled: int = 0
    wake_word: str = "jarvis"
    daily_summary_time: str = "18:00"
    auto_index_projects: bool = True
    session_start: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "AppState":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class PersistentState:
    """
    Manages persistent state across JARVIS restarts.
    Handles crash recovery and state persistence.
    """

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state = AppState()
        self._lock = asyncio.Lock()
        self._load()

    def _load(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                self.state = AppState.from_dict(data)
                logger.info(f"Loaded state from {self.state_file}")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
                self.state = AppState()

    async def save(self) -> None:
        """Save state to file."""
        async with self._lock:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.state_file, "w") as f:
                    json.dump(self.state.to_dict(), f, indent=2, default=str)
                logger.debug(f"Saved state to {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    async def on_start(self) -> None:
        """Called when JARVIS starts."""
        now = datetime.now().isoformat()
        self.state.last_start = now
        self.state.session_start = now
        self.state.restart_count += 1
        
        # Check for crash recovery
        if self.state.last_stop:
            last_stop = datetime.fromisoformat(self.state.last_stop)
            # If last session was less than 5 minutes, it might be a crash
            time_since_stop = (datetime.now() - last_stop).total_seconds()
            if time_since_stop < 300:
                self.state.crash_count += 1
                self.state.last_crash = now
                logger.warning(f"Possible crash detected (crash #{self.state.crash_count})")
        
        await self.save()

    async def on_stop(self) -> None:
        """Called when JARVIS stops."""
        now = datetime.now().isoformat()
        self.state.last_stop = now
        
        # Calculate uptime contribution
        if self.state.session_start:
            session_start = datetime.fromisoformat(self.state.session_start)
            session_uptime = (datetime.now() - session_start).total_seconds()
            self.state.total_uptime_seconds += session_uptime
            self.state.session_start = None
        
        await self.save()

    async def on_crash(self, error: str) -> None:
        """Called when JARVIS crashes."""
        self.state.crash_count += 1
        self.state.last_crash = datetime.now().isoformat()
        
        # Save crash info
        crash_file = self.state_file.parent / "crash.log"
        crash_info = {
            "timestamp": self.state.last_crash,
            "error": error,
            "restart_count": self.state.restart_count
        }
        try:
            with open(crash_file, "a") as f:
                f.write(json.dumps(crash_info) + "\n")
        except Exception:
            pass
        
        await self.save()

    def update_stats(self, **kwargs) -> None:
        """Update state statistics."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

    def get_recovery_info(self) -> Dict:
        """Get information for crash recovery."""
        return {
            "crash_count": self.state.crash_count,
            "last_crash": self.state.last_crash,
            "total_uptime": self.state.total_uptime_seconds,
            "restart_count": self.state.restart_count
        }


class StartupManager:
    """
    Manages JARVIS startup and auto-start configuration.
    Supports systemd, LaunchAgent, and manual startup.
    """

    def __init__(self):
        self.platform = self._detect_platform()

    def _detect_platform(self) -> str:
        """Detect operating system."""
        import sys
        if sys.platform == "linux":
            return "linux"
        elif sys.platform == "darwin":
            return "macos"
        elif sys.platform == "win32":
            return "windows"
        return "unknown"

    def install_auto_start(self) -> bool:
        """Install auto-start on system boot."""
        if self.platform == "linux":
            return self._install_systemd()
        elif self.platform == "macos":
            return self._install_launchagent()
        elif self.platform == "windows":
            return self._install_windows()
        return False

    def uninstall_auto_start(self) -> bool:
        """Remove auto-start configuration."""
        if self.platform == "linux":
            return self._uninstall_systemd()
        elif self.platform == "macos":
            return self._uninstall_launchagent()
        return False

    def _install_systemd(self) -> bool:
        """Install systemd user service."""
        import sys
        import os
        from pathlib import Path
        
        # Use HOME environment variable (respects test overrides)
        home_dir = Path(os.environ.get("HOME", str(Path.home())))
        user_name = os.environ.get("USER", "root")
        
        service_content = f"""[Unit]
Description=JARVIS Desktop Assistant
After=network.target

[Service]
Type=simple
User={user_name}
WorkingDirectory={Path.cwd()}
ExecStart={sys.executable} -m jarvis.desktop run
Restart=on-failure
RestartSec=10
StandardOutput=append:{home_dir}/.jarvis/jarvis.log
StandardError=append:{home_dir}/.jarvis/jarvis.log

[Install]
WantedBy=default.target
"""
        service_path = home_dir / ".config" / "systemd" / "user" / "jarvis.service"
        service_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(service_path, "w") as f:
                f.write(service_content)
            
            logger.info(f"Created systemd service: {service_path}")
            logger.info("Run: systemctl --user daemon-reload && systemctl --user enable --now jarvis")
            return True
        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return False

    def _uninstall_systemd(self) -> bool:
        """Remove systemd service."""
        from pathlib import Path
        service_path = Path.home() / ".config" / "systemd" / "user" / "jarvis.service"
        try:
            if service_path.exists():
                service_path.unlink()
            logger.info("Removed systemd service")
            return True
        except Exception as e:
            logger.error(f"Failed to remove systemd service: {e}")
            return False

    def _install_launchagent(self) -> bool:
        """Install LaunchAgent for macOS."""
        import sys
        from pathlib import Path
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>jarvis.desktop</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.jarvis/jarvis.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.jarvis/jarvis.log</string>
</dict>
</plist>
"""
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.jarvis.desktop.plist"
        plist_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(plist_path, "w") as f:
                f.write(plist_content)
            logger.info(f"Created LaunchAgent: {plist_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to install LaunchAgent: {e}")
            return False

    def _uninstall_launchagent(self) -> bool:
        """Remove LaunchAgent."""
        from pathlib import Path
        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.jarvis.desktop.plist"
        try:
            if plist_path.exists():
                plist_path.unlink()
            logger.info("Removed LaunchAgent")
            return True
        except Exception as e:
            logger.error(f"Failed to remove LaunchAgent: {e}")
            return False

    def _install_windows(self) -> bool:
        """Install Windows startup registry entry."""
        import sys
        import winreg
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "JARVIS", 0, winreg.REG_SZ, f'"{sys.executable}" -m jarvis.desktop run')
            winreg.CloseKey(key)
            logger.info("Added Windows startup entry")
            return True
        except Exception as e:
            logger.error(f"Failed to add Windows startup: {e}")
            return False

    def is_auto_start_enabled(self) -> bool:
        """Check if auto-start is enabled."""
        if self.platform == "linux":
            from pathlib import Path
            return (Path.home() / ".config" / "systemd" / "user" / "jarvis.service").exists()
        elif self.platform == "macos":
            from pathlib import Path
            return (Path.home() / "Library" / "LaunchAgents" / "com.jarvis.desktop.plist").exists()
        return False
