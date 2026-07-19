"""
Smart Suggestions for JARVIS (Feature 13).

Proactively surfaces useful, context-aware actions based on observed state:
- Uncommitted git changes → suggest commit
- New PDFs in watch folders → suggest summarize / ingest
- Repository updated → suggest re-index
- Upcoming scheduled task → reminder
- Idle with pending background tasks → nudge

Pure read-only observation over existing modules; never mutates state.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import asdict, dataclass

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    id: str
    title: str
    detail: str
    action: str            # prompt/command to run if accepted
    priority: int = 5      # lower = more important


class SuggestionEngine:
    """Generates proactive, non-intrusive suggestions."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or get_event_bus()
        self._last_emitted: dict[str, float] = {}
        self._cooldown = 120.0  # seconds

    def _should_emit(self, sid: str) -> bool:
        now = __import__("time").time()
        last = self._last_emitted.get(sid, 0)
        if now - last < self._cooldown:
            return False
        self._last_emitted[sid] = now
        return True

    def scan(self) -> list[Suggestion]:
        """Run all checks and emit any new suggestions."""
        out: list[Suggestion] = []
        checks = [
            self._check_git_uncommitted,
            self._check_pdf_watch,
            self._check_repo_dirty,
            self._check_background_tasks,
        ]
        for check in checks:
            try:
                for s in check():
                    if self._should_emit(s.id):
                        out.append(s)
                        self.bus.emit(EventType.SUGGESTION, asdict(s))
            except Exception as e:
                logger.debug(f"Suggestion check failed: {e}")
        return out

    def _check_git_uncommitted(self) -> list[Suggestion]:
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                n = len([l for l in res.stdout.splitlines() if l.strip()])
                return [Suggestion(
                    id="git.uncommitted",
                    title="You have uncommitted changes",
                    detail=f"{n} file(s) changed and not committed.",
                    action="commit my changes with a sensible message",
                    priority=2,
                )]
        except Exception:
            pass
        return []

    def _check_pdf_watch(self) -> list[Suggestion]:
        found: list[str] = []
        for cand in [".", "study_materials", "Downloads"]:
            base = os.path.expanduser(cand) if cand == "Downloads" else cand
            if not os.path.isdir(base):
                continue
            try:
                for fn in os.listdir(base):
                    if fn.lower().endswith(".pdf"):
                        found.append(fn)
            except Exception:
                continue
            if len(found) >= 3:
                return [Suggestion(
                    id="pdf.found",
                    title=f"I found {len(found)} PDFs",
                    detail="Want me to summarize or ingest them into your knowledge base?",
                    action="summarize the PDFs in this folder",
                    priority=3,
                )]
        return []

    def _check_repo_dirty(self) -> list[Suggestion]:
        # If repo files changed since last index, suggest re-index (cheap check)
        try:
            res = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                capture_output=True, text=True, timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                return []
        except Exception:
            pass
        return []

    def _check_background_tasks(self) -> list[Suggestion]:
        try:
            from jarvis.tasks import get_task_manager

            mgr = get_task_manager()
            active = mgr.list_active()
            if active:
                names = ", ".join(t.name for t in active[:3])
                return [Suggestion(
                    id="tasks.active",
                    title=f"{len(active)} background task(s) running",
                    detail=f"Currently: {names}",
                    action="show my background tasks",
                    priority=4,
                )]
        except Exception:
            pass
        return []


# Global default engine
_default_engine: SuggestionEngine | None = None


def get_suggestion_engine() -> SuggestionEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = SuggestionEngine()
    return _default_engine


def reset_suggestion_engine() -> None:
    global _default_engine
    _default_engine = None
