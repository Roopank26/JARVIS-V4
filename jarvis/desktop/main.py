"""
JARVIS Desktop - Main Entry Point

Usage:
    python -m jarvis.desktop run       # Start desktop assistant
    python -m jarvis.desktop status    # Show status
    python -m jarvis.desktop stop      # Stop running instance
    python -m jarvis.desktop install  # Install auto-start
    python -m jarvis.desktop test     # Run validation tests
    python -m jarvis.desktop diagnose # Run system diagnostics
"""

import argparse
import asyncio
import contextlib
import logging
from pathlib import Path

from jarvis.desktop import DesktopAssistant, DesktopConfig
from jarvis.desktop.state import PersistentState, StartupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="JARVIS Desktop Assistant")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=[
            "run",
            "status",
            "stop",
            "restart",
            "install",
            "uninstall",
            "test",
            "diagnose",
            "info",
        ],
    )
    args = parser.parse_args()

    if args.command == "status":
        show_status()
    elif args.command == "stop":
        stop_jarvis()
    elif args.command == "restart":
        restart_jarvis()
    elif args.command == "install":
        install_auto_start()
    elif args.command == "uninstall":
        uninstall_auto_start()
    elif args.command == "test":
        run_tests()
    elif args.command == "diagnose":
        run_diagnostics()
    elif args.command == "info":
        show_info()
    else:
        run_jarvis()


def show_status():
    """Show JARVIS status."""
    state_file = Path.home() / ".jarvis" / "state.json"

    if not state_file.exists():
        print("JARVIS is not installed or has never run")
        return

    state = PersistentState(state_file)

    print("JARVIS Desktop Status")
    print("=" * 40)
    print(f"Version: {state.state.version}")
    print(f"Last start: {state.state.last_start or 'Never'}")
    print(f"Last stop: {state.state.last_stop or 'Running'}")
    print(f"Restart count: {state.state.restart_count}")
    print(f"Crash count: {state.state.crash_count}")
    print(f"Total uptime: {state.state.total_uptime_seconds / 3600:.1f} hours")
    print(f"Plugins: {state.state.plugins_loaded}")
    print(f"Memory entries: {state.state.memory_entries}")
    print(f"Projects: {state.state.project_count}")
    print(f"Wake word: {state.state.wake_word}")

    # Check if running
    pid_file = Path.home() / ".jarvis" / "jarvis.pid"
    if pid_file.exists():
        try:
            import os

            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            print("\nStatus: RUNNING")
        except (ValueError, OSError):
            print("\nStatus: NOT RUNNING (stale PID file)")
    else:
        print("\nStatus: NOT RUNNING")


def stop_jarvis():
    """Stop running JARVIS instance."""
    pid_file = Path.home() / ".jarvis" / "jarvis.pid"

    if not pid_file.exists():
        print("JARVIS is not running")
        return

    try:
        import os
        import signal

        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print("Sent stop signal to JARVIS")

        # Wait for shutdown
        import time

        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                print("JARVIS stopped")
                return

        print("JARVIS did not stop gracefully, forcing...")
        os.kill(pid, signal.SIGKILL)
        print("JARVIS killed")

    except Exception as e:
        print(f"Error stopping JARVIS: {e}")


def restart_jarvis():
    """Restart JARVIS."""
    print("Restarting JARVIS...")
    stop_jarvis()
    import time

    time.sleep(2)
    run_jarvis()


def install_auto_start():
    """Install auto-start."""
    manager = StartupManager()
    if manager.install_auto_start():
        print("Auto-start installed successfully")
    else:
        print("Failed to install auto-start")


def uninstall_auto_start():
    """Uninstall auto-start."""
    manager = StartupManager()
    if manager.uninstall_auto_start():
        print("Auto-start removed successfully")
    else:
        print("Failed to remove auto-start")


def run_jarvis():
    """Run JARVIS desktop assistant."""

    async def main():
        # Initialize persistent state
        state_file = Path.home() / ".jarvis" / "state.json"
        state = PersistentState(state_file)

        # Create assistant
        config = DesktopConfig.from_file(Path.home() / ".jarvis" / "config.json")
        assistant = DesktopAssistant(config)

        # Set up state callbacks
        async def on_start():
            await state.on_start()
            state.update_stats(
                plugins_loaded=assistant.plugins.plugin_count,
                project_count=len(assistant.projects.projects),
                memory_entries=len(assistant.memory.memories),
                wake_word=assistant.config.wake_word,
            )
            await state.save()

        async def on_stop():
            await state.on_stop()

        # Register callbacks (simplified)
        try:
            await assistant.start()
            await on_start()

            # Run until stopped
            while assistant.is_running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error: {e}")
            await state.on_crash(str(e))
        finally:
            await on_stop()
            await assistant.stop()
            logger.info("JARVIS shutdown complete")

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())


def run_tests():
    """Run validation tests."""
    import subprocess
    import sys

    print("Running JARVIS Desktop validation tests...")
    print("=" * 50)

    # Run pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_desktop.py", "-v", "--tb=short"],
        capture_output=False,
    )

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("All validation tests passed!")
    else:
        print("\n" + "=" * 50)
        print("Some tests failed. See output above.")

    return result.returncode


def run_diagnostics():
    """Run system diagnostics."""
    from jarvis.desktop.diagnose import main as diagnose_main

    diagnose_main()


def show_info():
    """Show system information."""
    from jarvis.desktop.platform import get_platform_info

    info = get_platform_info()

    print("=" * 50)
    print("JARVIS Desktop - System Information")
    print("=" * 50)
    print(f"Platform: {info.platform.value}")
    print(f"OS: {info.name}")
    print(f"Version: {info.version}")
    print(f"Machine: {info.machine}")
    print(f"Data Directory: {info.data_dir}")
    print(f"Temp Directory: {info.temp_dir}")
    print(f"Audio Available: {info.audio_available}")
    print(f"Tray Available: {info.tray_available}")
    print(f"Service Available: {info.service_available}")
    print("=" * 50)


if __name__ == "__main__":
    main()
