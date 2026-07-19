"""
JARVIS Desktop Assistant - Autonomous Desktop Mode
Unified implementation for persistent, always-on desktop assistant.
"""

import asyncio
import contextlib
import json
import logging
import signal
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from jarvis.memory.knowledge import LocalKnowledgeBase
from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.project import ProjectMemory
from jarvis.memory.self_improve import Outcome, SelfImprovementLogs
from jarvis.plugins.base import PluginManager
from jarvis.services.daemon import JarvisDaemon
from jarvis.services.scheduler import TaskScheduler, TaskType
from jarvis.voice.listener import (
    ContinuousListener,
    ListenerConfig,
    handle_voice_command,
    parse_voice_command,
)

logger = logging.getLogger(__name__)


@dataclass
class DesktopConfig:
    """Configuration for desktop assistant."""

    # Wake word settings
    wake_word: str = "jarvis"
    wake_sensitivity: float = 0.7

    # Audio settings
    silence_timeout: float = 3.0
    command_timeout: float = 30.0

    # Behavior settings
    idle_timeout: float = 300.0
    greeting: str = "Yes?"

    # System settings
    auto_start: bool = True
    minimize_to_tray: bool = True
    show_notifications: bool = True
    crash_recovery: bool = True

    # Features
    auto_index_projects: bool = True
    daily_summary_time: str = "18:00"
    enable_background_tasks: bool = True  # Enable/disable scheduler and indexing

    # Paths
    data_dir: Path = field(default_factory=lambda: Path.home() / ".jarvis")

    @classmethod
    def from_file(cls, path: Path) -> "DesktopConfig":
        """Load config from file."""
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        return cls()

    def save(self, path: Path) -> None:
        """Save config to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2, default=str)


class DesktopAssistant:
    """
    JARVIS Desktop Assistant - Autonomous Mode

    Runs continuously in background with:
    - Wake word detection
    - Continuous microphone monitoring
    - Persistent memory across restarts
    - Scheduled tasks that survive reboot
    - Plugin auto-loading
    - Daily summary generation
    - Local project indexing
    - System tray application
    """

    def __init__(self, config: DesktopConfig | None = None):
        self.config = config or DesktopConfig()

        # Core components
        self.daemon = JarvisDaemon()
        self.memory = LongTermMemory(self.config.data_dir / "memory.json")
        self.projects = ProjectMemory(self.config.data_dir / "projects.json")
        self.knowledge = LocalKnowledgeBase(self.config.data_dir / "knowledge")
        self.improvement = SelfImprovementLogs(self.config.data_dir / "self_improvement.json")
        self.scheduler = TaskScheduler(self.config.data_dir / "scheduler.json")
        self.plugins = PluginManager(self.config.data_dir / "plugins")

        # Voice components
        listener_config = ListenerConfig(
            wake_word=self.config.wake_word,
            wake_sensitivity=self.config.wake_sensitivity,
            silence_threshold=self.config.silence_timeout,
            command_timeout=self.config.command_timeout,
            idle_timeout=self.config.idle_timeout,
            greeting=self.config.greeting,
        )
        self.listener = ContinuousListener(listener_config)

        # System tray
        self.tray = None
        self._tray_icon = None

        # State
        self._running = False
        self._initialized = False
        self._start_time: datetime | None = None

        # Background tasks
        self._scheduler_task: asyncio.Task | None = None
        self._index_task: asyncio.Task | None = None

    async def initialize(self) -> bool:
        """Initialize all components."""
        if self._initialized:
            return True

        logger.info("Initializing JARVIS Desktop Assistant...")

        try:
            # Set up callbacks
            self.plugins.set_jarvis(self)
            self.scheduler.set_jarvis(self)

            # Initialize knowledge base
            await self.knowledge.initialize()

            # Load plugins
            await self.plugins.load_all()
            logger.info(f"Loaded {self.plugins.plugin_count} plugins")

            # Register scheduled tasks
            self._register_default_tasks()

            # Load memory
            self.memory.load()

            self._initialized = True
            logger.info("JARVIS Desktop Assistant initialized")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _register_default_tasks(self) -> None:
        """Register default scheduled tasks."""
        # Daily summary at configured time
        hour, minute = self.config.daily_summary_time.split(":")

        self.scheduler.add_task(
            name="daily_summary",
            schedule=f"{minute} {hour} * * *",
            command="generate_daily_summary",
            task_type=TaskType.REPORT,
            description="Generate daily summary",
        )

        # Project indexing (daily)
        self.scheduler.add_task(
            name="index_projects",
            schedule="0 3 * * *",  # 3 AM daily
            command="index_projects",
            task_type=TaskType.COMMAND,
            description="Index project files for search",
        )

        # Memory cleanup (weekly)
        self.scheduler.add_task(
            name="cleanup_memory",
            schedule="0 4 * * 0",  # Sunday 4 AM
            command="cleanup_memory",
            task_type=TaskType.COMMAND,
            description="Clean up old memory entries",
        )

    async def start(self) -> bool:
        """Start the desktop assistant."""
        if self._running:
            logger.warning("JARVIS is already running")
            return False

        logger.info("Starting JARVIS Desktop Assistant...")

        # Initialize if needed
        if not self._initialized and not await self.initialize():
            return False

        # Start daemon
        self.daemon.config.data_dir = self.config.data_dir
        await self.daemon.start()

        # Set up signal handlers
        self._setup_signal_handlers()

        # Start voice listener
        self.listener.set_command_callback(self._handle_voice_command)
        await self.listener.start()

        if self.config.enable_background_tasks:
            self._scheduler_task = asyncio.create_task(self._run_scheduler())

        # Start system tray
        if self.config.minimize_to_tray:
            await self._start_tray()

        self._running = True
        self._start_time = datetime.now()

        # Index projects if enabled
        if self.config.auto_index_projects and self.config.enable_background_tasks:
            self._index_task = asyncio.create_task(self._index_projects())

        logger.info("JARVIS Desktop Assistant started")

        # Welcome message
        await self._notify("JARVIS is now running")

        return True

    async def stop(self) -> bool:
        """Stop the desktop assistant."""
        if not self._running:
            return True

        logger.info("Stopping JARVIS Desktop Assistant...")

        # Cancel background tasks
        for task in (self._scheduler_task, self._index_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        self._scheduler_task = None
        self._index_task = None

        # Stop components
        await self.listener.stop()
        self.scheduler.stop()
        await self.plugins.unload_all()
        await self.daemon.stop()

        # Stop tray
        if self._tray_icon:
            self._tray_icon.destroy()
            self._tray_icon = None

        # Save state
        self.memory._save()

        self._running = False

        logger.info("JARVIS Desktop Assistant stopped")
        return True

    async def restart(self) -> bool:
        """Restart the desktop assistant."""
        await self.stop()
        await asyncio.sleep(2)
        return await self.start()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig, lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
            except Exception as e:
                logger.warning(f"Could not set signal handler: {e}")

    async def _handle_signal(self, sig) -> None:
        """Handle shutdown signal."""
        logger.info(f"Received signal {sig}")
        await self.stop()

    async def _handle_voice_command(self, text: str) -> str:
        """Handle voice command."""
        start_time = datetime.now()

        try:
            # Parse command
            cmd = await parse_voice_command(text)

            # Check plugins first
            plugin_result = await self.plugins.handle_command(
                cmd.intent, [cmd.raw_text], {"entities": cmd.entities}
            )
            if plugin_result:
                return plugin_result

            # Log interaction
            self.improvement.log_interaction(
                input_text=text, intent=cmd.intent, entities=cmd.entities, outcome=Outcome.SUCCESS
            )

            # Handle command
            response = await handle_voice_command(cmd, self)

            # Track duration
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.improvement.log_interaction(
                input_text=text,
                intent=cmd.intent,
                response=response,
                outcome=Outcome.SUCCESS,
                duration_ms=duration,
            )

            return response

        except Exception as e:
            logger.error(f"Voice command error: {e}")

            # Log failure
            self.improvement.log_interaction(
                input_text=text, intent="unknown", outcome=Outcome.FAILED
            )

            return "Sorry, I encountered an error"

    async def _run_scheduler(self) -> None:
        """Run the task scheduler."""
        try:
            await self.scheduler.run()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    async def _index_projects(self) -> None:
        """Index project files for search."""
        logger.info("Indexing projects...")

        try:
            # Find and add projects

            # Only index from config.data_dir (not user's entire home)
            search_path = self.config.data_dir

            # Skip if no projects directory exists
            if not search_path.exists():
                logger.info("No data directory, skipping indexing")
                return

            # Find and add projects from data_dir only
            detected = await self.projects.auto_detect_projects([search_path])

            # If no projects found, skip
            if not detected:
                logger.info("No projects found in data directory, skipping indexing")
                return

            # Index each project
            for project_name in detected:
                project = self.projects.get_project(project_name)
                if project and project.path.exists():
                    count = await self.knowledge.add_project_context(project.path)
                    logger.info(f"Indexed {count} files for {project_name}")

        except Exception as e:
            logger.error(f"Project indexing error: {e}")

    async def process_command(self, command: str) -> str:
        """Process a text command."""
        command = command.strip().lower()

        if command == "generate_daily_summary":
            return await self._generate_daily_summary()

        elif command == "index_projects":
            await self._index_projects()
            return "Projects indexed"

        elif command == "cleanup_memory":
            self.memory.clear()
            return "Memory cleaned"

        elif command.startswith("remember "):
            fact = command[9:].strip()
            self.memory.remember("fact", fact)
            return f"I'll remember: {fact}"

        elif command.startswith("what do you know about "):
            topic = command[22:].strip()
            facts = self.memory.recall(topic)
            if facts:
                return "I know: " + "; ".join(facts)
            return "I don't have information about that"

        elif command == "status":
            return self._get_status()

        elif command == "projects":
            return self._get_projects()

        elif command == "help":
            return self._get_help()

        else:
            # Search knowledge base
            results = await self.knowledge.search(command)
            if results:
                return f"I found: {results[0]['content'][:200]}"
            return "I'm not sure how to help with that"

    async def _generate_daily_summary(self) -> str:
        """Generate and save daily summary."""
        logger.info("Generating daily summary...")

        # Get stats
        summary = self.improvement.get_stats_summary()
        daily = self.scheduler.get_daily_summary()
        projects = self.projects.list_projects()

        # Generate report
        report = f"""Daily Summary - {date.today()}
=====================

Activity:
- Total interactions: {summary.get("total_interactions", 0)}
- Success rate: {summary.get("success_rate", 0):.1%}
- Commands executed: {daily.commands_executed}

Projects: {len(projects)} tracked
"""

        # Save summary
        summaries_dir = self.config.data_dir / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        summary_file = summaries_dir / f"{date.today()}.md"
        summary_file.write_text(report)

        # Notify
        if self.config.show_notifications:
            await self._notify(
                f"Daily summary generated: {summary.get('total_interactions', 0)} interactions"
            )

        return report

    async def _notify(self, message: str) -> None:
        """Show system notification."""
        if not self.config.show_notifications:
            return

        try:
            from plyer import notification

            notification.notify(title="JARVIS", message=message, timeout=5)
        except ImportError:
            logger.debug("plyer not available for notifications")
        except Exception as e:
            logger.warning(f"Notification failed: {e}")

    def _get_status(self) -> str:
        """Get current status."""
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)

        return f"""JARVIS Status
==============
Uptime: {hours}h {minutes}m
Plugins: {self.plugins.plugin_count} loaded
Projects: {len(self.projects.projects)} tracked
Memory: {len(getattr(self.memory, "_memory", {}).get("categories", {}))} entries
Tasks: {len(self.scheduler.tasks)} scheduled
"""

    def _get_projects(self) -> str:
        """Get project list."""
        projects = self.projects.list_projects()
        if not projects:
            return "No projects tracked"

        lines = ["Tracked Projects:", ""]
        for p in projects:
            lines.append(f"- {p['name']} ({p.get('language', 'unknown')})")

        return "\n".join(lines)

    def _get_help(self) -> str:
        """Get help text."""
        return """JARVIS Commands
===============
Voice: Say "Jarvis" followed by your command

Text commands:
- remember <fact> - Store a memory
- what do you know about <topic> - Search memories
- projects - List tracked projects
- status - Show current status
- help - Show this help
"""

    async def _start_tray(self) -> None:
        """Start system tray application."""
        try:
            from jarvis.desktop.tray import TrayIcon

            self._tray_icon = TrayIcon(self)
            success = await self._tray_icon.create()
            if success:
                logger.info("System tray started")
        except Exception as e:
            logger.warning(f"Failed to start tray: {e}")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def uptime(self) -> float | None:
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return None
