"""
JARVIS Confidence Engine

Pure-logic confidence scoring for decisions, memories, and responses.
No external dependencies — entirely local computation.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfidenceFactors:
    """Factors that influence confidence scoring."""
    source_reliability: float = 0.5   # 0-1: how reliable the source is
    recency: float = 0.5             # 0-1: how recent the information is
    corroboration: float = 0.0       # 0-1: how many independent sources agree
    internal_consistency: float = 0.5 # 0-1: consistent with existing knowledge
    completeness: float = 0.5        # 0-1: how complete the information is
    specificity: float = 0.5         # 0-1: how specific vs vague


@dataclass
class ConfidenceScore:
    """A scored confidence result."""
    value: float                      # 0.0-1.0 final confidence
    level: str                        # very_low, low, moderate, high, very_high
    factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "value": round(self.value, 3),
            "level": self.level,
            "reasoning": self.reasoning,
        }


LEVEL_THRESHOLDS = [
    (0.85, "very_high"),
    (0.65, "high"),
    (0.45, "moderate"),
    (0.25, "low"),
    (0.0, "very_low"),
]


class ConfidenceEngine:
    """
    Pure-logic confidence scoring engine.
    Weights multiple factors to produce a single confidence score.
    No LLM needed — entirely local arithmetic.

    V4.2: Adds confidence calibration tracking. If the engine consistently
    predicts 0.9 confidence but outcomes are 0.6, it detects overconfidence
    and adjusts future predictions.
    """

    # Default weights for each factor
    WEIGHTS = {
        "source_reliability": 0.20,
        "recency": 0.15,
        "corroboration": 0.25,
        "internal_consistency": 0.20,
        "completeness": 0.10,
        "specificity": 0.10,
    }

    # Recency decay half-life in seconds (1 hour)
    RECENCY_HALF_LIFE = 3600.0

    # V4.2: Calibration buckets (confidence range → observed outcomes)
    CALIBRATION_BUCKETS = [
        (0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0),
    ]

    def __init__(self) -> None:
        # V4.2: Calibration tracking
        # Each bucket tracks (predicted_sum, actual_sum, count)
        self._calibration: dict[tuple[float, float], list[float]] = {
            bucket: [0.0, 0.0, 0.0] for bucket in self.CALIBRATION_BUCKETS
        }
        self._total_predictions: int = 0

    def record_outcome(self, predicted_confidence: float, actual_success: bool) -> None:
        """
        V4.2: Record an outcome for calibration tracking.
        This is how confidence becomes calibrated over time.
        """
        actual = 1.0 if actual_success else 0.0
        for bucket in self.CALIBRATION_BUCKETS:
            if bucket[0] <= predicted_confidence < bucket[1] or (
                bucket[1] == 1.0 and predicted_confidence == 1.0
            ):
                self._calibration[bucket][0] += predicted_confidence
                self._calibration[bucket][1] += actual
                self._calibration[bucket][2] += 1.0
                break
        self._total_predictions += 1

    def get_calibration_adjustment(self, predicted_confidence: float) -> float:
        """
        V4.2: Get a calibration adjustment for a predicted confidence.
        Returns an adjustment factor (positive = overconfident, negative = underconfident).
        """
        for bucket in self.CALIBRATION_BUCKETS:
            if bucket[0] <= predicted_confidence < bucket[1] or (
                bucket[1] == 1.0 and predicted_confidence == 1.0
            ):
                data = self._calibration[bucket]
                if data[2] >= 3:  # Need at least 3 observations
                    avg_predicted = data[0] / data[2]
                    avg_actual = data[1] / data[2]
                    # If predicted > actual, we're overconfident → negative adjustment
                    return avg_actual - avg_predicted
                break
        return 0.0

    def get_calibrated_confidence(self, raw_confidence: float) -> float:
        """
        V4.2: Adjust raw confidence based on calibration history.
        """
        adjustment = self.get_calibration_adjustment(raw_confidence)
        return max(0.05, min(0.95, raw_confidence + adjustment))

    def get_calibration_stats(self) -> dict[str, Any]:
        """V4.2: Return calibration statistics for monitoring."""
        buckets_data = {}
        for bucket, data in self._calibration.items():
            if data[2] > 0:
                buckets_data[f"{bucket[0]:.1f}-{bucket[1]:.1f}"] = {
                    "avg_predicted": round(data[0] / data[2], 3),
                    "avg_actual": round(data[1] / data[2], 3),
                    "count": int(data[2]),
                    "calibration_error": round(abs(data[0] / data[2] - data[1] / data[2]), 3),
                }
        return {
            "total_predictions": self._total_predictions,
            "buckets": buckets_data,
        }

    def score(self, factors: ConfidenceFactors, context: str = "") -> ConfidenceScore:
        """Compute weighted confidence from factors."""
        weighted_sum = (
            factors.source_reliability * self.WEIGHTS["source_reliability"]
            + factors.recency * self.WEIGHTS["recency"]
            + factors.corroboration * self.WEIGHTS["corroboration"]
            + factors.internal_consistency * self.WEIGHTS["internal_consistency"]
            + factors.completeness * self.WEIGHTS["completeness"]
            + factors.specificity * self.WEIGHTS["specificity"]
        )

        value = max(0.0, min(1.0, weighted_sum))
        level = self._value_to_level(value)
        reasoning = self._explain(factors, value)

        return ConfidenceScore(value=value, level=level, factors=factors, reasoning=reasoning)

    def score_from_recency(self, timestamp: float) -> float:
        """Compute a recency score from a timestamp using exponential decay."""
        age = max(0.0, time.time() - timestamp)
        return math.exp(-age / self.RECENCY_HALF_LIFE)

    def score_memory(self, memory: dict[str, Any], corroboration_count: int = 0) -> ConfidenceScore:
        """Score confidence for a memory entry."""
        now = time.time()
        updated = memory.get("updated_ts", now)
        if isinstance(updated, str):
            updated = now  # fallback

        factors = ConfidenceFactors(
            source_reliability=memory.get("source_reliability", 0.7),
            recency=self.score_from_recency(updated),
            corroboration=min(1.0, corroboration_count / 3.0),
            internal_consistency=memory.get("consistency", 0.5),
            completeness=min(1.0, len(str(memory.get("value", ""))) / 100.0),
            specificity=memory.get("specificity", 0.5),
        )
        return self.score(factors, context="memory")

    def score_reasoning(self, step_count: int, evidence_count: int, contradiction_count: int) -> ConfidenceScore:
        """Score confidence for a reasoning chain."""
        factors = ConfidenceFactors(
            source_reliability=0.7,
            recency=0.9,
            corroboration=min(1.0, evidence_count / 3.0),
            internal_consistency=max(0.0, 1.0 - contradiction_count * 0.3),
            completeness=min(1.0, step_count / 5.0),
            specificity=min(1.0, evidence_count / 5.0),
        )
        return self.score(factors, context="reasoning")

    def compare(self, a: ConfidenceScore, b: ConfidenceScore) -> ConfidenceScore:
        """Return the higher-confidence score."""
        return a if a.value >= b.value else b

    @staticmethod
    def _value_to_level(value: float) -> str:
        for threshold, level in LEVEL_THRESHOLDS:
            if value >= threshold:
                return level
        return "very_low"

    @staticmethod
    def _explain(factors: ConfidenceFactors, value: float) -> str:
        strengths = []
        weaknesses = []
        if factors.source_reliability > 0.7:
            strengths.append("reliable source")
        elif factors.source_reliability < 0.3:
            weaknesses.append("unreliable source")
        if factors.corroboration > 0.5:
            strengths.append("corroborated")
        if factors.internal_consistency < 0.4:
            weaknesses.append("internally inconsistent")
        if factors.recency < 0.3:
            weaknesses.append("outdated")

        parts = []
        if strengths:
            parts.append("Strengths: " + ", ".join(strengths))
        if weaknesses:
            parts.append("Weaknesses: " + ", ".join(weaknesses))
        parts.append(f"Overall: {value:.0%}")
        return "; ".join(parts) if parts else f"Confidence: {value:.0%}"
