"""
Reflection Engine for JARVIS.

After every completed task:
Success Analysis → Failure Analysis → Lessons Learned →
Experience Update → Memory Update → Future Recommendation
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ReflectionOutcome:
    success: bool
    duration_ms: float = 0.0
    steps_completed: int = 0
    steps_failed: int = 0
    error: str | None = None
    lessons: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class ReflectionEngine:
    """
    Post-task analysis and continuous learning.
    """

    def __init__(self, bus: EventBus | None = None):
        self.bus = bus or get_event_bus()
        self._history: list[ReflectionOutcome] = []

    async def reflect(self, task_input: str, result: Any, duration_ms: float = 0.0) -> ReflectionOutcome:
        outcome = ReflectionOutcome(
            success=self._is_success(result),
            duration_ms=duration_ms,
            steps_completed=self._count_completed(result),
            steps_failed=self._count_failed(result),
            error=self._extract_error(result),
        )

        outcome.lessons = self._derive_lessons(task_input, outcome)
        outcome.recommendations = self._derive_recommendations(outcome)

        self._history.append(outcome)

        with contextlib.suppress(Exception):
            self.bus.emit(
                EventType.STAGE,
                {
                    "stage": "reflection",
                    "success": outcome.success,
                    "duration_ms": outcome.duration_ms,
                    "lessons": outcome.lessons[:3],
                    "recommendations": outcome.recommendations[:3],
                },
            )

        return outcome

    def _is_success(self, result: Any) -> bool:
        if result is None:
            return False
        text = str(result).lower()
        if "error" in text and "no error" not in text:
            return False
        return "failed" not in text

    def _count_completed(self, result: Any) -> int:
        text = str(result)
        return text.count("completed") + text.count("success")

    def _count_failed(self, result: Any) -> int:
        text = str(result)
        return text.count("failed") + text.count("error")

    def _extract_error(self, result: Any) -> str | None:
        text = str(result)
        if "error" in text.lower():
            return text[:200]
        return None

    def _derive_lessons(self, task_input: str, outcome: ReflectionOutcome) -> list[str]:
        lessons = []
        lowered = task_input.lower()
        if outcome.success:
            if "search" in lowered or "find" in lowered:
                lessons.append("Search tasks completed successfully")
            if "plan" in lowered:
                lessons.append("Planning flow worked")
        else:
            if "timeout" in (outcome.error or "").lower():
                lessons.append("Task timed out; consider increasing timeout")
            if outcome.steps_failed > 0:
                lessons.append(f"Task had {outcome.steps_failed} failed step(s)")
            if not lessons:
                lessons.append("Task failed for an unknown reason")
        return lessons

    def _derive_recommendations(self, outcome: ReflectionOutcome) -> list[str]:
        recs = []
        if not outcome.success and outcome.steps_failed > 0:
            recs.append("Retry with fewer steps or simpler plan")
        if outcome.duration_ms > 5000:
            recs.append("Consider breaking long tasks into smaller jobs")
        if outcome.success and outcome.lessons:
            recs.append("Remember this approach for similar tasks")
        return recs

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [self._outcome_to_dict(o) for o in self._history[-limit:]]

    def _outcome_to_dict(self, outcome: ReflectionOutcome) -> dict[str, Any]:
        return {
            "success": outcome.success,
            "duration_ms": outcome.duration_ms,
            "steps_completed": outcome.steps_completed,
            "steps_failed": outcome.steps_failed,
            "error": outcome.error,
            "lessons": outcome.lessons,
            "recommendations": outcome.recommendations,
        }


def get_reflection_engine() -> ReflectionEngine:
    global _default_reflection
    if "_default_reflection" not in globals():
        _default_reflection = ReflectionEngine()
    return _default_reflection
