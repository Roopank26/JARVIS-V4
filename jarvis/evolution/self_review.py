"""
JARVIS-V7 Evolution — Self-Review & Self-Improvement Loop.

After every completed task, generates a self-review determining:
  What succeeded, what failed, what could be improved.
Stores lessons and improves future behavior.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.evolution.experience_collector import get_experience_collector
from jarvis.evolution.knowledge_graph_v2 import get_knowledge_graph

logger = logging.getLogger(__name__)


@dataclass
class SelfReview:
    task_id: str
    task_description: str
    success: bool
    succeeded_components: list[str] = field(default_factory=list)
    failed_components: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    severity: str = "low"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "success": self.success,
            "succeeded_components": self.succeeded_components,
            "failed_components": self.failed_components,
            "improvements": self.improvements,
            "lessons": self.lessons,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


def _classify_severity(failures: list[str], duration_ms: float) -> str:
    if not failures:
        return "low"
    critical_keywords = ["security", "data loss", "crash", "fatal", "exception"]
    if any(kw in " ".join(failures).lower() for kw in critical_keywords):
        return "critical"
    if len(failures) > 3 or duration_ms > 30000:
        return "high"
    if len(failures) > 1:
        return "medium"
    return "low"


class SelfReviewEngine:
    def __init__(self):
        self.history: deque[SelfReview] = deque(maxlen=5000)
        self.collector = get_experience_collector()
        self.graph = get_knowledge_graph()

    def review(self, task_id: str, description: str, result: Any, duration_ms: float = 0.0, components: list[str] | None = None) -> SelfReview:
        success = self._is_success(result)
        succeeded: list[str] = []
        failed: list[str] = []

        if components:
            for c in components:
                if success:
                    succeeded.append(c)
                else:
                    failed.append(c)

        if not components:
            if success:
                succeeded = ["overall_execution"]
            else:
                failed = ["overall_execution"]

        improvements = self._derive_improvements(result, success, duration_ms, failed)
        lessons = self._derive_lessons(result, success, duration_ms, failed)

        review = SelfReview(
            task_id=task_id,
            task_description=description,
            success=success,
            succeeded_components=succeeded,
            failed_components=failed,
            improvements=improvements,
            lessons=lessons,
            severity=_classify_severity(failed, duration_ms),
        )
        self.history.append(review)
        self._persist(review)
        logger.debug("Self-review for task %s: success=%s, severity=%s", task_id, success, review.severity)
        return review

    def _is_success(self, result: Any) -> bool:
        if result is None:
            return False
        text = str(result).lower()
        if "error" in text and "no error" not in text:
            return False
        return "failed" not in text

    def _derive_improvements(self, result: Any, success: bool, duration_ms: float, failures: list[str]) -> list[str]:
        improvements: list[str] = []
        if not success:
            if duration_ms > 10000:
                improvements.append("Consider breaking task into smaller subtasks to reduce timeout risk")
            if "not available" in str(result).lower() or "not found" in str(result).lower():
                improvements.append("Verify tool/resource availability before planning")
            if len(failures) > 2:
                improvements.append("Simplify execution plan and add fallback strategies")
        else:
            if duration_ms > 5000:
                improvements.append("Cache frequently used results to improve speed")
            improvements.append("Reuse this successful strategy for similar tasks")
        return improvements

    def _derive_lessons(self, result: Any, success: bool, duration_ms: float, failures: list[str]) -> list[str]:
        lessons: list[str] = []
        if success:
            lessons.append("task_completed_successfully")
            if duration_ms < 1000:
                lessons.append("fast_execution_observed")
        else:
            lessons.append("task_failed")
            for f in failures:
                lessons.append(f"failed_component:{f}")
        return lessons

    def _persist(self, review: SelfReview) -> None:
        self.collector.record(
            source="self_review",
            category="self_review",
            task_id=review.task_id,
            input_text=review.task_description,
            output_text=str(review.to_dict()),
            success=review.success,
            lessons=review.lessons,
            context={
                "succeeded": review.succeeded_components,
                "failed": review.failed_components,
                "improvements": review.improvements,
                "severity": review.severity,
            },
        )
        if review.lessons:
            pattern_node = self.graph.get_or_create_node("lesson", review.lessons[0])
            intent_node = self.graph.get_or_create_node("task_type", review.task_description[:50])
            if pattern_node and intent_node:
                self.graph.add_edge(intent_node.id, pattern_node.id, "yields_lesson")

    def get_recent_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in list(self.history)[-limit:]]

    def get_improvement_suggestions(self) -> list[str]:
        suggestions: list[str] = []
        recent = list(self.history)[-50:]
        if not recent:
            return suggestions
        failure_rate = sum(1 for r in recent if not r.success) / len(recent)
        if failure_rate > 0.3:
            suggestions.append("High failure rate detected; review execution strategies")
        high_severity = [r for r in recent if r.severity in ("high", "critical")]
        if high_severity:
            suggestions.append(f"{len(high_severity)} high-severity reviews in recent history")
        all_improvements: dict[str, int] = {}
        for r in recent:
            for imp in r.improvements:
                all_improvements[imp] = all_improvements.get(imp, 0) + 1
        for imp, count in sorted(all_improvements.items(), key=lambda x: x[1], reverse=True)[:3]:
            suggestions.append(f"Recurring improvement: {imp} ({count}x)")
        return suggestions


_review_instance: SelfReviewEngine | None = None


def get_self_review_engine() -> SelfReviewEngine:
    global _review_instance
    if _review_instance is None:
        _review_instance = SelfReviewEngine()
    return _review_instance


def reset_self_review_engine() -> None:
    global _review_instance
    _review_instance = None
