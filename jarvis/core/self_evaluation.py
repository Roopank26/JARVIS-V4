"""
JARVIS Phase 5 — Self Evaluation Engine.

Every response is internally scored on:
- Reasoning quality
- Planning quality
- Memory usage
- Tool selection
- Completeness
- Latency
- Confidence

Stores anonymized metrics for trend analysis.

Extends (does NOT replace) ObservabilityManager.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.observability import get_observability

logger = logging.getLogger(__name__)


@dataclass
class EvaluationScore:
    response_id: str
    reasoning: float = 0.0
    planning: float = 0.0
    memory_usage: float = 0.0
    tool_selection: float = 0.0
    completeness: float = 0.0
    latency_ms: float = 0.0
    confidence: float = 0.0
    overall: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def compute_overall(self) -> None:
        self.overall = round(
            (self.reasoning + self.planning + self.memory_usage + self.tool_selection + self.completeness + self.confidence)
            / 6.0,
            3,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "reasoning": round(self.reasoning, 3),
            "planning": round(self.planning, 3),
            "memory_usage": round(self.memory_usage, 3),
            "tool_selection": round(self.tool_selection, 3),
            "completeness": round(self.completeness, 3),
            "latency_ms": round(self.latency_ms, 2),
            "confidence": round(self.confidence, 3),
            "overall": round(self.overall, 3),
            "timestamp": self.timestamp,
        }


class SelfEvaluationEngine:
    """
    Scores responses across multiple dimensions and tracks trends.

    Integrates with ObservabilityManager for latency/success data.
    Stores anonymized metrics (no user content).
    """

    def __init__(self) -> None:
        self._observability = get_observability()
        self._history: deque[EvaluationScore] = deque(maxlen=10000)
        self._monthly_aggregates: dict[str, dict[str, float]] = {}

    def evaluate_response(
        self,
        response_id: str,
        reasoning_steps: int = 0,
        plan_steps: int = 0,
        memory_hits: int = 0,
        tools_used: int = 0,
        success: bool = True,
        latency_ms: float = 0.0,
        confidence: float = 0.5,
        output_length: int = 0,
        area_scores: dict[str, float] | None = None,
    ) -> EvaluationScore:
        reasoning = self._score_dimension(reasoning_steps, max_steps=5)
        planning = self._score_dimension(plan_steps, max_steps=8)
        memory_usage = min(1.0, memory_hits / 5.0) if memory_hits > 0 else 0.0
        tool_selection = min(1.0, tools_used / 3.0) if tools_used > 0 else 0.0
        completeness = 1.0 if success and output_length > 20 else (0.6 if success else 0.2)

        score = EvaluationScore(
            response_id=response_id,
            reasoning=reasoning,
            planning=planning,
            memory_usage=memory_usage,
            tool_selection=tool_selection,
            completeness=completeness,
            latency_ms=latency_ms,
            confidence=confidence,
        )
        if area_scores:
            for area, value in area_scores.items():
                setattr(score, f"area_{area}", value)
        score.compute_overall()
        self._history.append(score)
        self._update_monthly(score)
        return score

    def get_trend(self, dimension: str = "overall", limit: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-limit:]]

    def get_monthly_summary(self) -> dict[str, Any]:
        if not self._monthly_aggregates:
            return {"status": "no_data"}
        latest = max(self._monthly_aggregates.keys())
        summary = dict(self._monthly_aggregates[latest])
        summary["month"] = latest
        area_keys = [k for k in summary if k.startswith("area_")]
        summary["area_breakdown"] = {k: round(v, 3) for k, v in area_keys}
        return summary

    def get_dimension_stats(self, dimension: str) -> dict[str, Any]:
        values = [getattr(s, dimension, 0.0) for s in self._history]
        if not values:
            return {"status": "no_data"}
        return {
            "count": len(values),
            "avg": round(sum(values) / len(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "latest": round(values[-1], 3),
        }

    def _score_dimension(self, value: int, max_steps: int) -> float:
        return min(1.0, value / max_steps) if max_steps > 0 else 0.0

    def _update_monthly(self, score: EvaluationScore) -> None:
        month_key = time.strftime("%Y-%m", time.gmtime(score.timestamp))
        if month_key not in self._monthly_aggregates:
            self._monthly_aggregates[month_key] = {
                "reasoning": 0.0,
                "planning": 0.0,
                "memory_usage": 0.0,
                "tool_selection": 0.0,
                "completeness": 0.0,
                "latency_ms": 0.0,
                "confidence": 0.0,
                "overall": 0.0,
                "count": 0,
            }
        agg = self._monthly_aggregates[month_key]
        for dim in ["reasoning", "planning", "memory_usage", "tool_selection", "completeness", "confidence", "overall"]:
            current = getattr(score, dim)
            agg[dim] = (agg[dim] * agg["count"] + current) / (agg["count"] + 1)
        agg["latency_ms"] = (agg["latency_ms"] * agg["count"] + score.latency_ms) / (agg["count"] + 1)
        area_prefix = "area_"
        for attr in dir(score):
            if attr.startswith(area_prefix):
                area_name = attr[len(area_prefix):]
                current = getattr(score, attr, 0.0)
                key = f"{area_prefix}{area_name}"
                agg[key] = (agg.get(key, 0.0) * agg["count"] + current) / (agg["count"] + 1)
        agg["count"] += 1
        for dim in ["reasoning", "planning", "memory_usage", "tool_selection", "completeness", "confidence", "overall", "latency_ms"]:
            agg[dim] = round(agg[dim], 3)
        for key in agg:
            if key.startswith(area_prefix):
                agg[key] = round(agg[key], 3)


_self_evaluation: SelfEvaluationEngine | None = None


def get_self_evaluation_engine() -> SelfEvaluationEngine:
    global _self_evaluation
    if _self_evaluation is None:
        _self_evaluation = SelfEvaluationEngine()
    return _self_evaluation


def reset_self_evaluation_engine() -> None:
    global _self_evaluation
    _self_evaluation = None
