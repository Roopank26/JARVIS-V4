"""
JARVIS Phase 3 — Continuous Learning Engine.

After every task:
  Analyze result → Identify mistakes → Extract lessons → Update experience →
  Update decision history → Update knowledge graph → Improve future planning
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """A single execution experience."""

    experience_id: str
    task_id: str
    input_text: str
    output_text: str
    success: bool
    duration_ms: float
    mistakes: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    strategy: str = "unknown"
    provider: str | None = None
    model: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class DecisionRecord:
    """A recorded decision with outcome."""

    decision_id: str
    context: str
    choice: str
    outcome: str
    score: float
    timestamp: float = field(default_factory=time.time)


class LearningStore:
    """Persistent store for experiences and decisions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".jarvis" / "learning_store.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_experience(self, experience: Experience) -> None:
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(experience), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Learning store write failed: %s", exc)

    def load_recent(self, limit: int = 500) -> list[Experience]:
        experiences = []
        if not self.path.exists():
            return experiences
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        experiences.append(Experience(**data))
                    except Exception:
                        continue
                    if len(experiences) >= limit:
                        break
        except Exception:
            pass
        return experiences


class ContinuousLearningEngine:
    """
    Continuous self-improvement engine.

    Records every task experience, extracts lessons, maintains decision
    history, and surfaces insights to improve future planning.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self.store = LearningStore(store_path)
        self._history: deque[Experience] = deque(maxlen=5000)
        self._decisions: deque[DecisionRecord] = deque(maxlen=2000)
        self._patterns: dict[str, int] = {}

    async def record_experience(
        self,
        task_id: str,
        input_text: str,
        output_text: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> Experience:
        """Record a completed task experience and extract lessons."""
        logger.warning(
            "jarvis.learning.ContinuousLearningEngine is deprecated; use jarvis.evolution.ExperienceCollector instead."
        )
        mistakes, lessons = await self._analyze(input_text, output_text, success, duration_ms)
        experience = Experience(
            experience_id=uuid.uuid4().hex[:12],
            task_id=task_id,
            input_text=input_text,
            output_text=output_text,
            success=success,
            duration_ms=duration_ms,
            mistakes=mistakes,
            lessons=lessons,
        )
        self._history.append(experience)
        self.store.append_experience(experience)
        self._update_patterns(input_text, success)
        for lesson in lessons:
            logger.debug("Lesson learned: %s", lesson)
        return experience

    async def _analyze(
        self, input_text: str, output_text: str, success: bool, duration_ms: float
    ) -> tuple[list[str], list[str]]:
        """Analyze a result and extract mistakes and lessons."""
        mistakes: list[str] = []
        lessons: list[str] = []
        lowered = input_text.lower()

        if not success:
            if "timeout" in (output_text or "").lower():
                mistakes.append("task_timeout")
                lessons.append("consider_smaller_subtasks_or_fallback_provider")
            if "not found" in (output_text or "").lower() or "error" in (output_text or "").lower():
                mistakes.append("tool_not_available")
                lessons.append("verify_tool_availability_before_planning")
            if duration_ms > 10000:
                mistakes.append("slow_execution")
                lessons.append("prefer_fast_providers_for_time_sensitive_tasks")
        else:
            if duration_ms > 5000:
                lessons.append("task_succeeded_but_slow_consider_caching")

        if "research" in lowered and success:
            lessons.append("research_tasks_benefit_from_citation_verification")
        if "code" in lowered or "coding" in lowered:
            lessons.append("coding_tasks_benefit_from_code_review_agent")
        if "browser" in lowered:
            lessons.append("browser_tasks_benefit_from_persistent_browser_service")

        return mistakes, lessons

    def _update_patterns(self, input_text: str, success: bool) -> None:
        """Update pattern success counts."""
        lowered = input_text.lower()
        if "research" in lowered:
            self._patterns["research"] = self._patterns.get("research", 0) + (1 if success else -1)
        if "code" in lowered:
            self._patterns["coding"] = self._patterns.get("coding", 0) + (1 if success else -1)
        if "browser" in lowered:
            self._patterns["browser"] = self._patterns.get("browser", 0) + (1 if success else -1)

    def record_decision(
        self, context: str, choice: str, outcome: str, score: float = 0.5
    ) -> DecisionRecord:
        """Record a decision and its outcome for future reference."""
        record = DecisionRecord(
            decision_id=uuid.uuid4().hex[:12],
            context=context,
            choice=choice,
            outcome=outcome,
            score=score,
        )
        self._decisions.append(record)
        return record

    def get_decision_suggestions(self, context: str, limit: int = 5) -> list[DecisionRecord]:
        """Suggest past decisions relevant to a context."""
        suggestions = []
        ctx_words = set(context.lower().split())
        for record in reversed(self._decisions):
            record_words = set(record.context.lower().split())
            overlap = len(ctx_words & record_words)
            if overlap > 0:
                suggestions.append(record)
            if len(suggestions) >= limit:
                break
        return suggestions

    def get_pattern_insights(self) -> dict[str, Any]:
        """Return insights from accumulated experiences."""
        total = len(self._history)
        if total == 0:
            return {"total_experiences": 0}
        success_rate = sum(1 for e in self._history if e.success) / total
        avg_duration = sum(e.duration_ms for e in self._history) / total
        common_mistakes: dict[str, int] = {}
        for e in self._history:
            for m in e.mistakes:
                common_mistakes[m] = common_mistakes.get(m, 0) + 1
        return {
            "total_experiences": total,
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": round(avg_duration, 1),
            "common_mistakes": dict(sorted(common_mistakes.items(), key=lambda x: x[1], reverse=True)[:10]),
            "patterns": dict(self._patterns),
        }

    def get_improvement_suggestions(self) -> list[str]:
        """Generate actionable improvement suggestions."""
        insights = self.get_pattern_insights()
        suggestions = []
        if insights.get("success_rate", 1.0) < 0.8:
            suggestions.append("success_rate_below_80_review_failed_patterns")
        avg_ms = insights.get("avg_duration_ms", 0)
        if avg_ms > 3000:
            suggestions.append("consider_caching_and_provider_prefetch")
        mistakes = insights.get("common_mistakes", {})
        if mistakes.get("task_timeout", 0) > 3:
            suggestions.append("increase_timeouts_or_optimize_slow_steps")
        if mistakes.get("tool_not_available", 0) > 2:
            suggestions.append("expand_tool_registry_or_add_fallbacks")
        return suggestions
