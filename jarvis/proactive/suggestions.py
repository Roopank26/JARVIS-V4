"""
Adaptive Suggestions for JARVIS.
Observes user behavior patterns and emits non-intrusive suggestions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class BehaviorPattern:
    name: str
    count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    threshold: int = 2
    window_seconds: float = 86400.0
    cooldown_seconds: float = 3600.0
    suggestion: str = ""


class SuggestionEngine:
    def __init__(self, bus: EventBus | None = None):
        self.bus = bus or get_event_bus()
        self._patterns: dict[str, BehaviorPattern] = {}
        self._subs: list[Any] = []
        self._start()

        self._patterns["open_vscode"] = BehaviorPattern(
            name="Open VS Code",
            threshold=3,
            suggestion="Would you like me to launch your usual development workspace?",
        )
        self._patterns["start_ollama"] = BehaviorPattern(
            name="Start Ollama",
            threshold=2,
            suggestion="Ollama is usually started with VS Code. Launch together?",
        )
        self._patterns["open_github"] = BehaviorPattern(
            name="Open GitHub",
            threshold=2,
            suggestion="Want me to also open your project in VS Code?",
        )
        self._patterns["run_tests"] = BehaviorPattern(
            name="Run tests",
            threshold=2,
            suggestion="I noticed you run tests often. Want to auto-run them next time?",
        )

    def _start(self):
        try:
            self._subs.append(self.bus.subscribe(EventType.TOOL, self._on_event))
            self._subs.append(self.bus.subscribe(EventType.USER_MESSAGE, self._on_event))
        except Exception as e:
            logger.debug("Suggestion engine wiring failed: %s", e)

    def _on_event(self, event):
        try:
            data = event.data or {}
            text = ""
            if "content" in data:
                text = str(data.get("content", "")).lower()
            if "tool" in data:
                text = f"{text} {str(data.get('tool', '')).lower()}"
            if "summary" in data:
                text = f"{text} {str(data.get('summary', '')).lower()}"
            self.observe(text)
        except Exception:
            pass

    def observe(self, text: str):
        now = time.time()
        for _, pattern in self._patterns.items():
            tokens = [t.lower() for t in pattern.name.split()]
            if any(t in text for t in tokens):
                if now - pattern.last_seen > pattern.cooldown_seconds:
                    pattern.count = 0
                pattern.count += 1
                pattern.last_seen = now

    def check(self) -> str | None:
        now = time.time()
        for pattern in self._patterns.values():
            if pattern.count >= pattern.threshold and (now - pattern.last_seen) < pattern.window_seconds:
                return pattern.suggestion
        return None

    @property
    def patterns(self) -> dict[str, BehaviorPattern]:
        return self._patterns


_engine: SuggestionEngine | None = None


def get_suggestion_engine(bus: EventBus | None = None) -> SuggestionEngine:
    global _engine
    if _engine is None:
        _engine = SuggestionEngine(bus=bus)
    return _engine
