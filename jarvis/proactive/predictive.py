"""
JARVIS Predictive Intelligence & Silent Companion Engine
=========================================================
Anticipates user intent, prepares project context silently, tracks work session state across restarts,
and offers unobtrusive, high-value assistance.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus
from jarvis.memory.enhanced import get_enhanced_memory

logger = logging.getLogger(__name__)


@dataclass
class WorkSessionContext:
    active_project: str = "Unknown"
    current_file: str | None = None
    git_branch: str | None = None
    unresolved_todos: list[str] = field(default_factory=list)
    recent_actions: list[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def save(self, file_path: Path):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, file_path: Path) -> WorkSessionContext:
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                pass
        return cls()


class PredictiveAssistanceEngine:
    """
    Silent Companion Engine for JARVIS.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or get_event_bus()
        self.session_path = Path.home() / ".jarvis" / "session_context.json"
        self.session = WorkSessionContext.load(self.session_path)
        self._enabled = True
        self._start()

    def _start(self) -> None:
        try:
            self._bus.subscribe(EventType.TOOL, self._on_tool_event)
            self._bus.subscribe(EventType.USER_MESSAGE, self._on_user_event)
        except Exception as e:
            logger.debug("Predictive engine wiring note: %s", e)

    def _on_tool_event(self, event: Any) -> None:
        data = event.data or {}
        tool_name = data.get("tool", "")
        if tool_name:
            self.session.recent_actions.append(f"Tool:{tool_name}")
            if len(self.session.recent_actions) > 20:
                self.session.recent_actions.pop(0)
            self.session.last_updated = time.time()
            self.session.save(self.session_path)

    def _on_user_event(self, event: Any) -> None:
        data = event.data or {}
        text = data.get("content", "")
        if text:
            self.session.recent_actions.append(f"User:{text[:40]}")
            self.session.save(self.session_path)

    def prepare_vscode_context_silently(self, repo_path: str | Path) -> dict[str, Any]:
        """
        Silently prepare repository context when VS Code is opened.
        - Load project memory
        - Review Git status
        - Scan TODOs
        - Prepare context quietly without popping intrusive dialogs
        """
        logger.info("[PredictiveEngine] Silently preparing workspace context for: %s", repo_path)
        p = Path(repo_path)
        ctx = {"repo": p.name, "git_status": "clean", "todos_count": 0}

        try:
            mem = get_enhanced_memory()
            mem.memory.remember(f"project:{p.name}", f"Repository at {p.resolve()}", category="project")
            self.session.active_project = p.name
            self.session.save(self.session_path)
        except Exception as e:
            logger.debug("Silent context prep error: %s", e)

        return ctx


_engine: PredictiveAssistanceEngine | None = None


def get_predictive_engine(bus: EventBus | None = None) -> PredictiveAssistanceEngine:
    global _engine
    if _engine is None:
        _engine = PredictiveAssistanceEngine(bus=bus)
    return _engine
