"""
JARVIS-V7 Evolution — Benchmarking & Model Promotion System.

Evaluates candidate models across multiple dimensions and promotes
only when objectively superior to the current production model.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSuite:
    name: str = "default"
    tests: list[str] = field(default_factory=lambda: [
        "reasoning",
        "coding",
        "debugging",
        "planning",
        "memory",
        "research",
        "automation",
        "tool_usage",
        "latency",
        "reliability",
    ])
    weights: dict[str, float] = field(default_factory=lambda: {
        "reasoning": 1.5,
        "coding": 1.4,
        "debugging": 1.2,
        "planning": 1.3,
        "memory": 1.0,
        "research": 1.1,
        "automation": 1.2,
        "tool_usage": 1.3,
        "latency": 0.8,
        "reliability": 1.5,
    })

    def compute_weighted_score(self, scores: dict[str, float]) -> float:
        total = 0.0
        weight_sum = 0.0
        for test, score in scores.items():
            w = self.weights.get(test, 1.0)
            total += score * w
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0


@dataclass
class BenchmarkResult:
    model_id: str
    suite_name: str
    scores: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    latency_ms: float = 0.0
    passed: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "suite_name": self.suite_name,
            "scores": self.scores,
            "weighted_score": self.weighted_score,
            "latency_ms": self.latency_ms,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


class BenchmarkEngine:
    def __init__(self):
        self.suite = BenchmarkSuite()
        self.history: list[BenchmarkResult] = []

    def evaluate(self, model_id: str, scores: dict[str, float], latency_ms: float = 0.0) -> BenchmarkResult:
        weighted = self.suite.compute_weighted_score(scores)
        passed = weighted >= 0.75
        result = BenchmarkResult(
            model_id=model_id,
            suite_name=self.suite.name,
            scores=scores,
            weighted_score=weighted,
            latency_ms=latency_ms,
            passed=passed,
        )
        self.history.append(result)
        logger.info("Benchmarked model %s: weighted_score=%.3f, passed=%s", model_id, weighted, passed)
        return result

    def should_promote(self, candidate_result: BenchmarkResult, production_result: BenchmarkResult | None) -> tuple[bool, str]:
        if production_result is None:
            return True, "No production model exists"
        delta = candidate_result.weighted_score - production_result.weighted_score
        if delta > 0.05:
            return True, f"Candidate outperforms production by {delta:.3f}"
        if delta <= -0.05:
            return False, f"Candidate underperforms production by {delta:.3f}"
        if candidate_result.latency_ms < production_result.latency_ms * 0.9:
            return True, f"Candidate is significantly faster ({candidate_result.latency_ms:.0f}ms vs {production_result.latency_ms:.0f}ms)"
        if candidate_result.latency_ms > production_result.latency_ms * 1.2:
            return False, "Candidate is significantly slower"
        return False, "No significant improvement detected"

    def get_history(self, model_id: str | None = None) -> list[BenchmarkResult]:
        if model_id:
            return [r for r in self.history if r.model_id == model_id]
        return list(self.history)


class PromotionGate:
    def __init__(self):
        self.engine = BenchmarkEngine()

    def evaluate_for_promotion(
        self,
        model_id: str,
        scores: dict[str, float],
        latency_ms: float = 0.0,
        production_model_id: str | None = None,
    ) -> tuple[bool, str, BenchmarkResult]:
        candidate = self.engine.evaluate(model_id, scores, latency_ms)
        production = None
        if production_model_id:
            for r in self.engine.history:
                if r.model_id == production_model_id:
                    production = r
                    break
        should_promote, reason = self.engine.should_promote(candidate, production)
        logger.info("Promotion decision for %s: %s (%s)", model_id, should_promote, reason)
        return should_promote, reason, candidate


_promotion_gate: PromotionGate | None = None


def get_promotion_gate() -> PromotionGate:
    global _promotion_gate
    if _promotion_gate is None:
        _promotion_gate = PromotionGate()
    return _promotion_gate


def reset_promotion_gate() -> None:
    global _promotion_gate
    _promotion_gate = None
