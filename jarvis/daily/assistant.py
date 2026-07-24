"""
Daily Assistant Mode for JARVIS.
Provides morning routines, development summaries, and evening summaries.
Generates real briefings from workspace, memory, scheduler, and git.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime

from jarvis.services.scheduler import TaskScheduler

logger = logging.getLogger(__name__)


@dataclass
class DailyRoutine:
    name: str
    time_of_day: str
    items: list[str]


class DailyAssistant:
    def __init__(self, scheduler: TaskScheduler | None = None):
        self.scheduler = scheduler
        self._morning_routine = DailyRoutine(
            name="Morning",
            time_of_day="morning",
            items=[
                "today's schedule",
                "reminders",
                "active tasks",
                "running builds",
                "weather",
                "important emails",
                "research updates",
            ],
        )
        self._development_routine = DailyRoutine(
            name="Development",
            time_of_day="development",
            items=[
                "active tasks",
                "builds",
                "repositories",
                "recent commits",
                "TODOs",
                "test failures",
                "open issues",
            ],
        )
        self._evening_routine = DailyRoutine(
            name="Evening",
            time_of_day="evening",
            items=[
                "work summary",
                "unfinished tasks",
                "tomorrow's priorities",
                "lessons learned",
            ],
        )

    def _get_workspace_section(self) -> str:
        lines: list[str] = []
        try:
            from jarvis.workspace.awareness import WorkspaceAwareness

            workspace = WorkspaceAwareness()
            workspace.refresh()
            state = workspace.get_state()
            if state.repo:
                lines.append(f"Repository: {state.repo}")
            if state.branch:
                lines.append(f"Branch: {state.branch}")
            if state.directory:
                lines.append(f"Directory: {state.directory}")
            if state.recent_files:
                lines.append(f"Recent files: {', '.join(state.recent_files[:5])}")
            if state.running_servers:
                lines.append(f"Running servers: {', '.join(state.running_servers[:5])}")
        except Exception as exc:
            logger.debug("Workspace section failed: %s", exc)
        return "\n".join(lines)

    def _get_git_section(self) -> str:
        lines: list[str] = []
        try:
            cwd = os.getcwd()
            result = subprocess.run(
                ["git", "-C", cwd, "status", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                changes = result.stdout.strip().splitlines()[:10]
                lines.append(f"Changed files ({len(changes)} shown):")
                for change in changes:
                    lines.append(f"  {change}")
            else:
                lines.append("Working tree clean.")
        except Exception as exc:
            logger.debug("Git section failed: %s", exc)
        return "\n".join(lines)

    def _get_todo_section(self) -> str:
        lines: list[str] = []
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-ChildItem -Recurse -Include *.py,*.js,*.ts,*.tsx,*.md | Select-String -Pattern 'TODO|FIXME|HACK' | Select-Object -First 10 -ExpandProperty Line"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines.append("TODOs/FIXMEs:")
                for line in result.stdout.strip().splitlines()[:10]:
                    lines.append(f"  {line.strip()}")
            else:
                lines.append("No TODOs found.")
        except Exception as exc:
            logger.debug("TODO section failed: %s", exc)
        return "\n".join(lines)

    def morning_briefing(self) -> str:
        lines = ["=== Morning Briefing ===", ""]
        workspace = self._get_workspace_section()
        if workspace:
            lines.append(workspace)
            lines.append("")

        try:
            from jarvis.memory.enhanced import get_enhanced_memory

            profile = get_enhanced_memory()
            summary = profile.get_profile_summary()
            if summary and "don't have" not in summary.lower():
                lines.append(f"Profile: {summary[:200]}")
                lines.append("")
        except Exception as exc:
            logger.debug("Profile section failed: %s", exc)

        if self.scheduler:
            due = self.scheduler.get_due_tasks()
            if due:
                lines.append(f"Due tasks ({len(due)}):")
                for t in due[:5]:
                    lines.append(f"  - {t.name}: {t.command}")
                lines.append("")

        lines.append("Ready to help with your day.")
        return "\n".join(lines)

    def development_status(self) -> str:
        lines = ["=== Coding Session ===", ""]
        workspace = self._get_workspace_section()
        if workspace:
            lines.append(workspace)
            lines.append("")

        git = self._get_git_section()
        if git:
            lines.append(git)
            lines.append("")

        todos = self._get_todo_section()
        if todos:
            lines.append(todos)
            lines.append("")

        if self.scheduler:
            summary = self.scheduler.get_daily_summary()
            lines.append(f"Commands executed today: {summary.commands_executed}")
            lines.append(f"Tasks completed: {len(summary.tasks_completed)}")
            lines.append(f"Errors: {summary.errors_encountered}")
            lines.append("")

        lines.append("What would you like to work on?")
        return "\n".join(lines)

    def evening_summary(self) -> str:
        lines = ["=== Evening Summary ===", ""]
        if self.scheduler:
            summary = self.scheduler.get_daily_summary()
            lines.append(f"Date: {summary.date.isoformat()}")
            lines.append(f"Commands executed: {summary.commands_executed}")
            lines.append(f"Tasks completed: {len(summary.tasks_completed)}")
            lines.append(f"Files modified: {len(summary.files_modified)}")
            lines.append(f"Errors encountered: {summary.errors_encountered}")
            lines.append("")

            if summary.tasks_completed:
                lines.append("Tasks completed:")
                for task in summary.tasks_completed[-5:]:
                    lines.append(f"  - {task}")
                lines.append("")

            if summary.learned_facts:
                lines.append("Learned today:")
                for fact in summary.learned_facts[-5:]:
                    lines.append(f"  - {fact}")
                lines.append("")

        git = self._get_git_section()
        if git:
            lines.append("Uncommitted changes:")
            lines.append(git)
            lines.append("")

        lines.append("Good evening!")
        return "\n".join(lines)

    def get_routine_for_time(self, now: datetime | None = None) -> str:
        if now is None:
            now = datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            return self.morning_briefing()
        if 12 <= hour < 17:
            return self.development_status()
        return self.evening_summary()

    def get_routine_by_name(self, name: str) -> str:
        n = name.strip().lower()
        if n in ("morning", "brief", "briefing", "morning_briefing"):
            return self.morning_briefing()
        if n in ("dev", "coding", "development", "coding_session", "development_status"):
            return self.development_status()
        if n in ("evening", "summary", "evening_summary"):
            return self.evening_summary()
        return self.get_routine_for_time()
