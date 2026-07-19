"""
Task scheduler for JARVIS - Cron-like scheduling for recurring tasks.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from croniter import croniter

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of scheduled tasks."""

    COMMAND = "command"
    REMINDER = "reminder"
    CHECK = "check"
    REPORT = "report"


@dataclass
class ScheduledTask:
    """A scheduled task definition."""

    name: str
    schedule: str  # Cron expression
    task_type: TaskType
    command: str
    enabled: bool = True
    description: str = ""
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_due(self, now: datetime = None) -> bool:
        """Check if task is due to run."""
        if not self.enabled or self.next_run is None:
            return False

        if now is None:
            now = datetime.now()

        return now >= self.next_run

    def calculate_next_run(self) -> datetime:
        """Calculate next run time from cron expression."""
        cron = croniter(self.schedule, self.last_run or datetime.now())
        self.next_run = cron.get_next(datetime)
        return self.next_run


@dataclass
class DailySummary:
    """Daily activity summary."""

    date: date
    commands_executed: int = 0
    tasks_completed: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    errors_encountered: int = 0
    knowledge_added: int = 0
    top_interactions: list[str] = field(default_factory=list)
    learned_facts: list[str] = field(default_factory=list)
    project_progress: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "commands_executed": self.commands_executed,
            "tasks_completed": self.tasks_completed,
            "files_modified": self.files_modified,
            "errors_encountered": self.errors_encountered,
            "knowledge_added": self.knowledge_added,
            "top_interactions": self.top_interactions,
            "learned_facts": self.learned_facts,
            "project_progress": self.project_progress,
        }


class TaskScheduler:
    """
    Cron-like task scheduler for JARVIS.
    Handles recurring tasks, reminders, and automated workflows.
    """

    def __init__(self, storage_path: Path = None):
        if storage_path is None:
            storage_path = Path.home() / ".jarvis" / "scheduler.json"

        self.storage_path = storage_path
        self.tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._jarvis = None
        self._callbacks: dict[str, Callable] = {}
        self._daily_summary = DailySummary(date=date.today())
        self._load_tasks()

    def set_jarvis(self, jarvis: Any) -> None:
        """Set reference to main JARVIS instance."""
        self._jarvis = jarvis

    def _load_tasks(self) -> None:
        """Load tasks from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)

                for name, task_data in data.items():
                    task = ScheduledTask(
                        name=name,
                        schedule=task_data["schedule"],
                        task_type=TaskType(task_data.get("type", "command")),
                        command=task_data["command"],
                        enabled=task_data.get("enabled", True),
                        description=task_data.get("description", ""),
                        metadata=task_data.get("metadata", {}),
                    )
                    task.calculate_next_run()
                    self.tasks[name] = task

                logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")

    def _save_tasks(self) -> None:
        """Save tasks to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for name, task in self.tasks.items():
            data[name] = {
                "schedule": task.schedule,
                "type": task.task_type.value,
                "command": task.command,
                "enabled": task.enabled,
                "description": task.description,
                "metadata": task.metadata,
            }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_task(
        self,
        name: str,
        schedule: str,
        command: str,
        task_type: TaskType = TaskType.COMMAND,
        description: str = "",
        enabled: bool = True,
        **metadata,
    ) -> ScheduledTask:
        """
        Add a new scheduled task.

        Args:
            name: Unique task name
            schedule: Cron expression (e.g., "0 9 * * *" for daily at 9 AM)
            command: Command to execute
            task_type: Type of task
            description: Human-readable description
            enabled: Whether task is enabled

        Returns:
            Created ScheduledTask
        """
        task = ScheduledTask(
            name=name,
            schedule=schedule,
            task_type=task_type,
            command=command,
            description=description,
            enabled=enabled,
            metadata=metadata,
        )
        task.calculate_next_run()

        self.tasks[name] = task
        self._save_tasks()

        logger.info(f"Added scheduled task: {name} ({schedule})")
        return task

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            self._save_tasks()
            logger.info(f"Removed scheduled task: {name}")
            return True
        return False

    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self.tasks[name].calculate_next_run()
            self._save_tasks()
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            self._save_tasks()
            return True
        return False

    def get_task(self, name: str) -> ScheduledTask | None:
        """Get a task by name."""
        return self.tasks.get(name)

    def list_tasks(self) -> list[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self.tasks.values())

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get all tasks that are due to run."""
        now = datetime.now()
        return [t for t in self.tasks.values() if t.is_due(now)]

    async def run(self) -> None:
        """Main scheduler loop."""
        self._running = True
        logger.info("Task scheduler started")

        while self._running:
            try:
                due_tasks = self.get_due_tasks()

                for task in due_tasks:
                    await self._execute_task(task)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        logger.info(f"Executing task: {task.name}")

        task.last_run = datetime.now()
        task.run_count += 1
        task.calculate_next_run()
        self._save_tasks()

        try:
            # Check for registered callback
            if task.name in self._callbacks:
                callback = self._callbacks[task.name]
                await callback(task)
            elif self._jarvis:
                # Execute via JARVIS
                result = await self._jarvis.process_command(task.command)
                logger.debug(f"Task result: {result}")

                # Track in daily summary
                self._daily_summary.tasks_completed.append(task.name)

        except Exception as e:
            logger.error(f"Task execution error: {task.name}: {e}")
            self._daily_summary.errors_encountered += 1

    def on_task(self, name: str, callback: Callable) -> None:
        """Register callback for task execution."""
        self._callbacks[name] = callback

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Task scheduler stopped")

    # Daily Summary Methods

    def increment_commands(self) -> None:
        """Increment command counter."""
        self._daily_summary.commands_executed += 1

    def add_file_modified(self, path: str) -> None:
        """Record file modification."""
        if path not in self._daily_summary.files_modified:
            self._daily_summary.files_modified.append(path)

    def add_knowledge(self, fact: str) -> None:
        """Record knowledge added."""
        self._daily_summary.knowledge_added += 1
        if fact not in self._daily_summary.learned_facts:
            self._daily_summary.learned_facts.append(fact)

    def get_daily_summary(self) -> DailySummary:
        """Get today's summary."""
        return self._daily_summary

    async def generate_summary_report(self) -> str:
        """Generate formatted summary report."""
        summary = self._daily_summary

        lines = [
            f"# Daily Summary - {summary.date}",
            "",
            "## Activity",
            f"- Commands executed: {summary.commands_executed}",
            f"- Tasks completed: {len(summary.tasks_completed)}",
            f"- Errors encountered: {summary.errors_encountered}",
            f"- Files modified: {len(summary.files_modified)}",
            "",
        ]

        if summary.tasks_completed:
            lines.append("### Tasks Completed")
            for task in summary.tasks_completed[-5:]:
                lines.append(f"- {task}")
            lines.append("")

        if summary.learned_facts:
            lines.append("### Learned")
            for fact in summary.learned_facts[-5:]:
                lines.append(f"- {fact}")
            lines.append("")

        if summary.project_progress:
            lines.append("### Project Progress")
            for project, status in summary.project_progress.items():
                lines.append(f"- {project}: {status}")

        return "\n".join(lines)

    def save_summary(self) -> Path:
        """Save daily summary to file."""
        summaries_dir = Path.home() / ".jarvis" / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        filename = summaries_dir / f"{self._daily_summary.date}.json"
        with open(filename, "w") as f:
            json.dump(self._daily_summary.to_dict(), f, indent=2)

        return filename

    def new_day(self) -> None:
        """Reset for new day."""
        # Save old summary
        self.save_summary()

        # Create new summary
        self._daily_summary = DailySummary(date=date.today())
        logger.info("New day started, summary reset")
