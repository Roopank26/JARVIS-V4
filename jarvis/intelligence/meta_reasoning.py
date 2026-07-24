"""
JARVIS Phase 5 — Meta Reasoning Engine.

Enhances existing SelfReviewEngine and ReflectionEngine with:
- Confidence estimation for decisions and outcomes
- Weakness detection across task history
- Improvement suggestions derived from patterns
- Lesson persistence via ExperienceCollector
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.evolution.experience_collector import get_experience_collector
from jarvis.evolution.self_review import get_self_review_engine

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceEstimate:
    task_id: str
    confidence: float = 0.0
    reasoning_quality: float = 0.0
    planning_quality: float = 0.0
    tool_selection_quality: float = 0.0
    memory_utilization: float = 0.0
    completeness: float = 0.0
    latency_score: float = 0.0
    hallucination_risk: float = 0.0
    calibration_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "confidence": round(self.confidence, 3),
            "reasoning_quality": round(self.reasoning_quality, 3),
            "planning_quality": round(self.planning_quality, 3),
            "tool_selection_quality": round(self.tool_selection_quality, 3),
            "memory_utilization": round(self.memory_utilization, 3),
            "completeness": round(self.completeness, 3),
            "latency_score": round(self.latency_score, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class WeaknessReport:
    task_id: str
    weaknesses: list[str] = field(default_factory=list)
    severity: str = "low"
    affected_dimensions: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "weaknesses": self.weaknesses,
            "severity": self.severity,
            "affected_dimensions": self.affected_dimensions,
            "timestamp": self.timestamp,
        }


@dataclass
class MetaLesson:
    lesson_id: str
    task_id: str
    category: str
    insight: str
    actionable: str
    confidence: float = 0.5
    applied_count: int = 0
    success_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "task_id": self.task_id,
            "category": self.category,
            "insight": self.insight,
            "actionable": self.actionable,
            "confidence": round(self.confidence, 3),
            "applied_count": self.applied_count,
            "success_count": self.success_count,
            "timestamp": self.timestamp,
        }


class MetaReasoningEngine:
    """
    Reasons about JARVIS's own reasoning after every significant task.

    Composes with:
    - SelfReviewEngine (evolution)
    - ReflectionEngine (core)
    - ExperienceCollector (evolution)

    Does NOT replace any existing module.
    """

    def __init__(self) -> None:
        self._review_engine = get_self_review_engine()
        self._collector = get_experience_collector()
        self._confidence_history: deque[ConfidenceEstimate] = deque(maxlen=2000)
        self._weakness_history: deque[WeaknessReport] = deque(maxlen=2000)
        self._meta_lessons: deque[MetaLesson] = deque(maxlen=2000)
        self._improvement_cache: dict[str, list[str]] = {}

    def evaluate_task(
        self,
        task_id: str,
        description: str,
        result: Any,
        duration_ms: float = 0.0,
        components: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConfidenceEstimate:
        review = self._review_engine.review(
            task_id=task_id,
            description=description,
            result=result,
            duration_ms=duration_ms,
            components=components,
        )
        confidence = self._estimate_confidence(task_id, review, duration_ms, metadata or {})
        self._confidence_history.append(confidence)
        return confidence

    def detect_weaknesses(self, task_id: str, result: Any, duration_ms: float = 0.0) -> WeaknessReport:
        weaknesses: list[str] = []
        affected: list[str] = []
        text = str(result or "").lower()

        if "timeout" in text or duration_ms > 15000:
            weaknesses.append("latency_bottleneck")
            affected.append("planning")
        if "not found" in text or "not available" in text or "error" in text:
            weaknesses.append("resource_gap")
            affected.append("tool_selection")
        if "permission" in text or "denied" in text:
            weaknesses.append("permission_issue")
            affected.append("execution")
        if duration_ms > 5000 and not weaknesses:
            weaknesses.append("slow_execution")
            affected.append("performance")
        if not result or (isinstance(result, str) and len(result.strip()) < 10):
            weaknesses.append("empty_or_insufficient_output")
            affected.append("completeness")

        severity = "low"
        if len(weaknesses) >= 3:
            severity = "high"
        elif len(weaknesses) >= 1:
            severity = "medium"

        report = WeaknessReport(
            task_id=task_id,
            weaknesses=weaknesses,
            severity=severity,
            affected_dimensions=affected,
        )
        self._weakness_history.append(report)
        return report

    def suggest_improvements(self, task_id: str, context: str = "") -> list[str]:
        cache_key = context.lower().strip()[:120]
        if cache_key in self._improvement_cache:
            return self._improvement_cache[cache_key]

        suggestions: list[str] = []
        recent = list(self._weakness_history)[-20:]
        weakness_counts: dict[str, int] = {}
        for w in recent:
            for weakness in w.weaknesses:
                weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1

        if weakness_counts.get("latency_bottleneck", 0) >= 2:
            suggestions.append("Introduce caching for repeated lookups and parallelize independent tool calls")
        if weakness_counts.get("resource_gap", 0) >= 2:
            suggestions.append("Expand capability discovery and add fallback providers/tools before planning")
        if weakness_counts.get("permission_issue", 0) >= 1:
            suggestions.append("Review tool permissions and add pre-flight permission checks")
        if weakness_counts.get("slow_execution", 0) >= 3:
            suggestions.append("Optimize prompt size and switch to faster provider for routine tasks")
        if weakness_counts.get("empty_or_insufficient_output", 0) >= 1:
            suggestions.append("Increase response token limits and validate output completeness before returning")

        review_suggestions = self._review_engine.get_improvement_suggestions()
        for s in review_suggestions:
            if s not in suggestions:
                suggestions.append(s)

        self._improvement_cache[cache_key] = suggestions
        return suggestions

    def record_meta_lesson(
        self,
        task_id: str,
        category: str,
        insight: str,
        actionable: str,
        confidence: float = 0.5,
    ) -> MetaLesson:
        lesson = MetaLesson(
            lesson_id=f"ml_{int(time.time())}_{task_id[:6]}",
            task_id=task_id,
            category=category,
            insight=insight,
            actionable=actionable,
            confidence=confidence,
        )
        self._meta_lessons.append(lesson)
        try:
            self._collector.record(
                source="meta_reasoning",
                category="meta_lesson",
                task_id=task_id,
                input_text=category,
                output_text=actionable,
                success=True,
                lessons=[insight],
                context={"confidence": confidence},
            )
        except Exception as exc:
            logger.debug("Meta lesson persistence failed: %s", exc)
        return lesson

    def get_confidence_trend(self, limit: int = 50) -> list[dict[str, Any]]:
        return [c.to_dict() for c in list(self._confidence_history)[-limit:]]

    def get_weakness_summary(self, limit: int = 50) -> dict[str, Any]:
        recent = list(self._weakness_history)[-limit:]
        counts: dict[str, int] = {}
        for report in recent:
            for w in report.weaknesses:
                counts[w] = counts.get(w, 0) + 1
        return {
            "total_reviews": len(recent),
            "weakness_counts": dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)),
            "recent_severity": [r.severity for r in recent[-10:]],
        }

    def get_meta_lessons(self, limit: int = 50) -> list[dict[str, Any]]:
        return [lesson.to_dict() for lesson in list(self._meta_lessons)[-limit:]]

    def get_autonomous_insights(self) -> dict[str, Any]:
        total = len(self._confidence_history)
        if total == 0:
            return {"status": "insufficient_data"}
        avg_confidence = sum(c.confidence for c in self._confidence_history) / total
        avg_reasoning = sum(c.reasoning_quality for c in self._confidence_history) / total
        avg_planning = sum(c.planning_quality for c in self._confidence_history) / total
        avg_tools = sum(c.tool_selection_quality for c in self._confidence_history) / total
        avg_calibration = sum(c.calibration_score for c in self._confidence_history) / total
        avg_hallucination = sum(c.hallucination_risk for c in self._confidence_history) / total
        weakness_summary = self.get_weakness_summary()
        top_weaknesses = list(weakness_summary.get("weakness_counts", {}).keys())[:5]
        return {
            "total_evaluated": total,
            "avg_confidence": round(avg_confidence, 3),
            "avg_reasoning_quality": round(avg_reasoning, 3),
            "avg_planning_quality": round(avg_planning, 3),
            "avg_tool_selection_quality": round(avg_tools, 3),
            "avg_calibration": round(avg_calibration, 3),
            "avg_hallucination_risk": round(avg_hallucination, 3),
            "top_weaknesses": top_weaknesses,
            "improvement_suggestions": self.suggest_improvements("", "global"),
            "meta_lessons_count": len(self._meta_lessons),
        }

    def _estimate_confidence(
        self, task_id: str, review: Any, duration_ms: float, metadata: dict[str, Any]
    ) -> ConfidenceEstimate:
        success = getattr(review, "success", False)
        severity = getattr(review, "severity", "low")

        base = 0.5 if success else 0.1
        if severity == "critical":
            base -= 0.3
        elif severity == "high":
            base -= 0.2
        elif severity == "medium":
            base -= 0.1

        reasoning = base + (0.1 if metadata.get("reasoning_steps", 0) > 2 else 0.0)
        planning = base + (0.1 if metadata.get("plan_steps", 0) > 0 else 0.0)
        tools = base + (0.1 if metadata.get("tools_used", 0) > 0 else 0.0)
        memory = base + (0.05 if metadata.get("memory_hits", 0) > 0 else 0.0)
        completeness = base + (0.05 if success else 0.0)
        latency = 1.0 if duration_ms < 2000 else (0.7 if duration_ms < 8000 else 0.4)

        confidence = round(
            max(0.0, min(1.0, (reasoning + planning + tools + memory + completeness + latency) / 6.0)),
            3,
        )
        hallucination_risk = self._estimate_hallucination_risk(review, metadata)
        calibration = self._estimate_calibration(confidence, duration_ms, success)

        return ConfidenceEstimate(
            task_id=task_id,
            confidence=confidence,
            reasoning_quality=round(max(0.0, min(1.0, reasoning)), 3),
            planning_quality=round(max(0.0, min(1.0, planning)), 3),
            tool_selection_quality=round(max(0.0, min(1.0, tools)), 3),
            memory_utilization=round(max(0.0, min(1.0, memory)), 3),
            completeness=round(max(0.0, min(1.0, completeness)), 3),
            latency_score=round(max(0.0, min(1.0, latency)), 3),
            hallucination_risk=round(hallucination_risk, 3),
            calibration_score=round(calibration, 3),
        )

    def _estimate_hallucination_risk(self, review: Any, metadata: dict[str, Any]) -> float:
        risk = 0.0
        text = str(review).lower() if review else ""
        if "uncertain" in text or "maybe" in text or "possibly" in text:
            risk += 0.2
        if "not sure" in text or "i think" in text:
            risk += 0.15
        if metadata.get("reasoning_steps", 0) < 2 and not metadata.get("plan_steps", 0):
            risk += 0.2
        if metadata.get("memory_hits", 0) == 0:
            risk += 0.1
        return min(1.0, risk)

    def _estimate_calibration(self, confidence: float, duration_ms: float, success: bool) -> float:
        if success and confidence > 0.7:
            return 0.9
        if success and confidence > 0.4:
            return 0.7
        if not success and confidence < 0.3:
            return 0.8
        if not success and confidence > 0.5:
            return 0.4
        return 0.6


_meta_reasoning: MetaReasoningEngine | None = None


def get_meta_reasoning_engine() -> MetaReasoningEngine:
    global _meta_reasoning
    if _meta_reasoning is None:
        _meta_reasoning = MetaReasoningEngine()
    return _meta_reasoning


def reset_meta_reasoning_engine() -> None:
    global _meta_reasoning
    _meta_reasoning = None
