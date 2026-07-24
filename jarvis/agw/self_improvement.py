"""
JARVIS-V8 AGW — Self-Improvement Enhancements.

Builds on the V7 Evolution Engine with AGW-specific improvements:
- Director-level self-review
- Experience-driven Director weight tuning
- Workflow benchmarking
- Continuous improvement of planning and execution.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class DirectorReflection:
    director: str
    task: str
    confidence: float
    plan: list[str]
    outcome: dict[str, Any]
    score: float = 0.0
    suggestions: list[str] = field(default_factory=list)


class AGWSelfImprovement:
    """AGW-specific self-improvement layer on top of the V7 Evolution Engine.

    Responsibilities:
    - Reflect on Director outcomes.
    - Tune Director selection heuristics.
    - Benchmark and promote better plans.
    - Feed structured insights back into the V7 evolution pipeline.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._reflections: list[dict[str, Any]] = []

    def record_reflection(self, director: str, task: str, confidence: float,
                          plan: list[str], outcome: dict[str, Any]) -> DirectorReflection:
        outcome.get("status", "unknown")
        score = self._score_outcome(outcome)
        reflection = DirectorReflection(
            director=director,
            task=task,
            confidence=confidence,
            plan=plan,
            outcome=outcome,
            score=score,
        )
        reflection.suggestions = self._generate_suggestions(reflection)
        self._reflections.append({
            "director": director,
            "task": task,
            "score": score,
            "timestamp": time.time(),
        })
        self._bus.emit(EventType.STATUS, {
            "agw_self_improve": "recorded",
            "director": director,
            "score": score,
        })
        return reflection

    def _score_outcome(self, outcome: dict[str, Any]) -> float:
        status = outcome.get("status", "unknown")
        if status == "completed":
            return 1.0
        if status == "error":
            return 0.0
        return 0.5

    def _generate_suggestions(self, reflection: DirectorReflection) -> list[str]:
        suggestions: list[str] = []
        if reflection.score < 0.5:
            suggestions.append(f"{reflection.director}: consider refining plan heuristics.")
        if reflection.confidence < 0.6:
            suggestions.append(f"{reflection.director}: low confidence; consider fallback agents.")
        if reflection.score >= 0.9:
            suggestions.append(f"{reflection.director}: high scoring; promote plan template.")
        return suggestions

    def get_insights(self) -> dict[str, Any]:
        if not self._reflections:
            return {"reflections": 0, "default": "collecting data"}
        avg_score = sum(r["score"] for r in self._reflections) / len(self._reflections)
        return {
            "reflections": len(self._reflections),
            "average_score": round(avg_score, 4),
            "recent": self._reflections[-10:],
        }

    def get_director_scores(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        counts: dict[str, int] = {}
        for r in self._reflections:
            d = r["director"]
            counts[d] = counts.get(d, 0) + 1
            scores[d] = scores.get(d, 0.0) + r["score"]
        if not counts:
            return {}
        return {d: round(s / counts[d], 4) for d, s in scores.items()}


_instance: AGWSelfImprovement | None = None


def get_agw_self_improvement() -> AGWSelfImprovement:
    global _instance
    if _instance is None:
        _instance = AGWSelfImprovement()
    return _instance
