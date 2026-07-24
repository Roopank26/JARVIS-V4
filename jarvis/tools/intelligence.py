"""
JARVIS Phase 5 — Tool Intelligence.

Before using any tool:
- Estimate expected usefulness
- Estimate execution cost
- Estimate confidence
- Suggest fallback strategy

After execution:
- Measure success
- Improve future decisions
- Update tool reputation

Integrates with:
- ObservabilityManager (core)
- ToolRegistry (tools)
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.observability import get_observability
from jarvis.tools.registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class ToolEstimate:
    tool_name: str
    expected_usefulness: float = 0.5
    execution_cost: float = 0.5
    confidence: float = 0.5
    fallback_tool: str | None = None
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "expected_usefulness": round(self.expected_usefulness, 3),
            "execution_cost": round(self.execution_cost, 3),
            "confidence": round(self.confidence, 3),
            "fallback_tool": self.fallback_tool,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


@dataclass
class ToolOutcome:
    tool_name: str
    success: bool
    latency_ms: float
    output_quality: float = 0.5
    fallback_used: bool = False
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 2),
            "output_quality": round(self.output_quality, 3),
            "fallback_used": self.fallback_used,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class ToolReputation:
    tool_name: str
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    avg_latency_ms: float = 0.0
    avg_output_quality: float = 0.5
    fallback_count: int = 0
    last_used: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_calls if self.total_calls > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "total_calls": self.total_calls,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_output_quality": round(self.avg_output_quality, 3),
            "fallback_count": self.fallback_count,
            "last_used": self.last_used,
        }


class ToolIntelligenceEngine:
    """
    Rates tools before and after use to improve selection decisions.

    Does NOT replace ToolRegistry or ObservabilityManager.
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or get_registry()
        self._observability = get_observability()
        self._reputations: dict[str, ToolReputation] = {}
        self._history: deque[ToolOutcome] = deque(maxlen=5000)
        self._estimate_cache: dict[str, ToolEstimate] = {}

    def estimate(self, tool_name: str, context: str = "") -> ToolEstimate:
        cache_key = f"{tool_name}:{context.lower().strip()[:80]}"
        if cache_key in self._estimate_cache:
            return self._estimate_cache[cache_key]

        reputation = self._reputations.get(tool_name)
        success_rate = reputation.success_rate if reputation else 0.7
        avg_latency = reputation.avg_latency_ms if reputation else 2000.0

        usefulness = min(1.0, success_rate + 0.1)
        cost = min(1.0, avg_latency / 5000.0)
        confidence = round((usefulness * 0.6 + (1.0 - cost) * 0.4), 3)

        fallback = self._suggest_fallback(tool_name)

        estimate = ToolEstimate(
            tool_name=tool_name,
            expected_usefulness=round(usefulness, 3),
            execution_cost=round(cost, 3),
            confidence=confidence,
            fallback_tool=fallback,
            reasoning=self._build_reasoning(tool_name, reputation, fallback),
        )
        self._estimate_cache[cache_key] = estimate
        return estimate

    def record_outcome(self, outcome: ToolOutcome) -> None:
        self._history.append(outcome)
        rep = self._reputations.get(outcome.tool_name)
        if rep is None:
            rep = ToolReputation(tool_name=outcome.tool_name)
            self._reputations[outcome.tool_name] = rep
        rep.total_calls += 1
        if outcome.success:
            rep.successes += 1
        else:
            rep.failures += 1
        if outcome.fallback_used:
            rep.fallback_count += 1
        rep.avg_latency_ms = (rep.avg_latency_ms * (rep.total_calls - 1) + outcome.latency_ms) / rep.total_calls
        rep.avg_output_quality = (rep.avg_output_quality * (rep.total_calls - 1) + outcome.output_quality) / rep.total_calls
        rep.last_used = outcome.timestamp
        if outcome.error:
            logger.debug("Tool %s recorded failure: %s", outcome.tool_name, outcome.error)

    def get_tool_reputation(self, tool_name: str) -> ToolReputation | None:
        return self._reputations.get(tool_name)

    def get_top_tools(self, limit: int = 10) -> list[dict[str, Any]]:
        ranked = sorted(
            self._reputations.values(),
            key=lambda r: r.success_rate,
            reverse=True,
        )
        return [r.to_dict() for r in ranked[:limit]]

    def get_underperforming_tools(self, threshold: float = 0.5) -> list[dict[str, Any]]:
        return [
            r.to_dict() for r in self._reputations.values()
            if r.total_calls >= 3 and r.success_rate < threshold
        ]

    def _suggest_fallback(self, tool_name: str) -> str | None:
        try:
            names = self._registry.list_names()
            if tool_name in names:
                idx = names.index(tool_name)
                if idx + 1 < len(names):
                    return names[idx + 1]
                if idx - 1 >= 0:
                    return names[idx - 1]
        except Exception:
            pass
        return None

    def _build_reasoning(self, tool_name: str, reputation: ToolReputation | None, fallback: str | None) -> str:
        parts = [f"Tool {tool_name} selected."]
        if reputation:
            parts.append(f"Historical success rate: {reputation.success_rate:.0%}.")
        if fallback:
            parts.append(f"Fallback available: {fallback}.")
        return " ".join(parts)


_tool_intelligence: ToolIntelligenceEngine | None = None


def get_tool_intelligence_engine() -> ToolIntelligenceEngine:
    global _tool_intelligence
    if _tool_intelligence is None:
        _tool_intelligence = ToolIntelligenceEngine()
    return _tool_intelligence


def reset_tool_intelligence_engine() -> None:
    global _tool_intelligence
    _tool_intelligence = None
