"""
Background service daemon for JARVIS.
Provides persistent background operation with system integration.
"""

import asyncio
import signal
import sys
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DaemonConfig:
    """Daemon configuration."""
    name: str = "jarvis"
    pid_file: Optional[Path] = None
    log_file: Optional[Path] = None
    data_dir: Path = None
    auto_restart: bool = True
    restart_delay: float = 5.0


class JarvisDaemon:
    """
    Background daemon for JARVIS desktop assistant.
    Handles service lifecycle, signals, and state persistence.
    """

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self._running = False
        self._tasks: list = []
        self._state: Dict[str, Any] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._start_time: Optional[datetime] = None

        # Set default paths
        if self.config.data_dir is None:
            self.config.data_dir = Path.home() / ".jarvis"
        
        if self.config.pid_file is None:
            self.config.pid_file = self.config.data_dir / "jarvis.pid"
        
        if self.config.log_file is None:
            self.config.log_file = self.config.data_dir / "jarvis.log"

    def set_callback(self, event: str, callback: Callable) -> None:
        """Set callback for daemon events."""
        self._callbacks[event] = callback

    async def start(self) -> bool:
        """
        Start the daemon.
        
        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Daemon already running")
            return False

        # Check if already running
        if self._is_running():
            logger.error("JARVIS is already running")
            return False

        try:
            # Create PID file
            self._write_pid()
            
            # Load state
            self._load_state()

            self._running = True
            self._start_time = datetime.now()
            
            logger.info(f"JARVIS daemon started")
            
            # Call startup callback
            if "on_start" in self._callbacks:
                await self._callbacks["on_start"]()

            return True

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            self._remove_pid()
            return False

    async def stop(self) -> bool:
        """
        Stop the daemon.
        
        Returns:
            True if stopped successfully
        """
        if not self._running:
            return True

        logger.info("Stopping JARVIS daemon...")
        
        try:
            # Call shutdown callback
            if "on_stop" in self._callbacks:
                await self._callbacks["on_stop"]()

            # Cancel all tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Save state
            self._save_state()

            self._running = False
            self._remove_pid()
            
            logger.info("JARVIS daemon stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping daemon: {e}")
            return False

    async def restart(self) -> bool:
        """Restart the daemon."""
        await self.stop()
        await asyncio.sleep(self.config.restart_delay)
        return await self.start()

    def _is_running(self) -> bool:
        """Check if daemon is already running."""
        pid_file = self.config.pid_file
        if pid_file and pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                # Check if process exists
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    return True
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    pid_file.unlink()
            except (ValueError, IOError):
                pass
        return False

    def _write_pid(self) -> None:
        """Write PID file."""
        self.config.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.pid_file.write_text(str(os.getpid()))

    def _remove_pid(self) -> None:
        """Remove PID file."""
        if self.config.pid_file and self.config.pid_file.exists():
            self.config.pid_file.unlink()

    def _load_state(self) -> None:
        """Load daemon state from disk."""
        state_file = self.config.data_dir / "daemon_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    self._state = json.load(f)
                logger.debug("Loaded daemon state")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
                self._state = {}

    def _save_state(self) -> None:
        """Save daemon state to disk."""
        state_file = self.config.data_dir / "daemon_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_file, "w") as f:
                json.dump(self._state, f, indent=2, default=str)
            logger.debug("Saved daemon state")
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def set_state(self, key: str, value: Any) -> None:
        """Set state value."""
        self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self._state.get(key, default)

    async def add_task(self, coro) -> asyncio.Task:
        """Add a background task."""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    @property
    def uptime(self) -> Optional[float]:
        """Get uptime in seconds."""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        return self._running


class ServiceManager:
    """
    Manages JARVIS as a system service.
    Supports systemd (Linux), LaunchAgent (macOS), and manual mode.
    """

    @staticmethod
    def install_systemd() -> bool:
        """Install as systemd service (Linux)."""
        if sys.platform != "linux":
            logger.error("systemd only supported on Linux")
            return False

        service_content = """[Unit]
Description=JARVIS Desktop Assistant
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={home}
ExecStart={python} -m jarvis daemon
Restart=on-failure
RestartSec=10
StandardOutput=append:{log}
StandardError=append:{log}

[Install]
WantedBy=default.target
""".format(
            user=os.environ.get("USER", "root"),
            home=Path.home(),
            python=sys.executable,
            log=Path.home() / ".jarvis" / "jarvis.log"
        )

        service_path = Path.home() / ".config" / "systemd" / "user" / "jarvis.service"
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

    @staticmethod
    def install_launchagent() -> bool:
        """Install as LaunchAgent (macOS)."""
        if sys.platform != "darwin":
            logger.error("LaunchAgent only supported on macOS")
            return False

        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.desktop</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>jarvis</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{home}/.jarvis/jarvis.log</string>
    <key>StandardErrorPath</key>
    <string>{home}/.jarvis/jarvis.log</string>
</dict>
</plist>
""".format(
            python=sys.executable,
            home=Path.home()
        )

        plist_path = Path.home() / "Library" / "LaunchAgents" / "com.jarvis.desktop.plist"
        plist_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(plist_path, "w") as f:
                f.write(plist_content)
            
            logger.info(f"Created LaunchAgent: {plist_path}")
            logger.info("Run: launchctl load ~/Library/LaunchAgents/com.jarvis.desktop.plist")
            return True
        except Exception as e:
            logger.error(f"Failed to install LaunchAgent: {e}")
            return False

    @staticmethod
    def install() -> bool:
        """Install as system service based on platform."""
        if sys.platform == "linux":
            return ServiceManager.install_systemd()
        elif sys.platform == "darwin":
            return ServiceManager.install_launchagent()
        else:
            logger.error(f"Unsupported platform: {sys.platform}")
            return False

    @staticmethod
    def uninstall() -> bool:
        """Uninstall system service."""
        if sys.platform == "linux":
            service_path = Path.home() / ".config" / "systemd" / "user" / "jarvis.service"
            if service_path.exists():
                service_path.unlink()
                logger.info("Removed systemd service")
                return True
        elif sys.platform == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.jarvis.desktop.plist"
            if plist_path.exists():
                plist_path.unlink()
                logger.info("Removed LaunchAgent")
                return True
        return False


def run_daemon():
    """Run JARVIS as a standalone daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS Desktop Assistant Daemon")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "stop", "restart", "status"])
    args = parser.parse_args()

    daemon = JarvisDaemon()

    if args.command == "status":
        if daemon._is_running():
            print("JARVIS is running")
            sys.exit(0)
        else:
            print("JARVIS is not running")
            sys.exit(1)

    elif args.command == "stop":
        if daemon._is_running():
            # Use PID file to send signal
            pid_file = Path.home() / ".jarvis" / "jarvis.pid"
            if pid_file.exists():
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                print("Sent stop signal to JARVIS")
        else:
            print("JARVIS is not running")
        sys.exit(0)

    elif args.command == "restart":
        # Implementation similar to stop then start
        print("Restarting JARVIS...")
        # Would need proper implementation

    else:  # start
        async def main():
            await daemon.start()
            # Keep running
            while daemon.is_running:
                await asyncio.sleep(1)

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            asyncio.run(daemon.stop())
