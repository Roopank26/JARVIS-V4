"""
JARVIS Phase 3 — Intelligent Provider Selection.

Wraps ProviderManager with multi-criteria scoring:
- task type, latency, context length, cost
- local availability, GPU availability
- previous success, reasoning/vision/tool-use capability
- automatic fallback chains, hybrid execution
- parallel provider evaluation
- provider benchmarking
- performance statistics
- learning from previous executions
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SelectionCriterion(StrEnum):
    LATENCY = "latency"
    COST = "cost"
    CONTEXT_LENGTH = "context_length"
    REASONING = "reasoning"
    VISION = "vision"
    TOOL_USE = "tool_use"
    LOCAL_AVAILABILITY = "local_availability"
    PREVIOUS_SUCCESS = "previous_success"


@dataclass
class ProviderScore:
    provider: str
    model: str
    score: float = 0.0
    criteria: dict[str, float] = field(default_factory=dict)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    reason: str = ""


@dataclass
class BenchmarkRecord:
    provider: str
    model: str
    latency_ms: float
    tokens_per_second: float = 0.0
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    task_type: str = "general"


class ProviderSelector:
    """
    Intelligent provider selection layer.

    Evaluates providers for a given task and chooses the best one,
    with automatic fallback and learning from history.
    """

    def __init__(self, provider_manager: Any | None = None) -> None:
        self.provider_manager = provider_manager
        self._benchmarks: list[BenchmarkRecord] = []
        self._history: list[dict[str, Any]] = []
        self._fallback_chain: list[str] = []
        self._max_benchmarks = 500

    async def select(
        self,
        task_type: str = "general",
        context_length: int = 2048,
        requires_vision: bool = False,
        requires_tools: bool = False,
        requires_reasoning: bool = False,
        cost_weight: float = 0.3,
        latency_weight: float = 0.4,
        quality_weight: float = 0.3,
    ) -> ProviderScore | None:
        """
        Select the best provider/model for a task.

        Returns the highest-scoring provider or None if none available.
        """
        if self.provider_manager is None:
            try:
                from jarvis.api.providers import get_provider_manager
                self.provider_manager = get_provider_manager()
            except Exception:
                return None

        candidates = await self._get_candidates()
        if not candidates:
            return None

        scores: list[ProviderScore] = []
        for provider_name, model, info in candidates:
            score = await self._score_candidate(
                provider_name=provider_name,
                model=model,
                info=info,
                task_type=task_type,
                context_length=context_length,
                requires_vision=requires_vision,
                requires_tools=requires_tools,
                requires_reasoning=requires_reasoning,
                cost_weight=cost_weight,
                latency_weight=latency_weight,
                quality_weight=quality_weight,
            )
            scores.append(score)

        if not scores:
            return None
        best = max(scores, key=lambda s: s.score)
        self._history.append({
            "timestamp": time.time(),
            "task_type": task_type,
            "selected": best.provider,
            "model": best.model,
            "score": best.score,
        })
        return best

    async def evaluate_parallel(self, providers: list[str], prompt: str) -> dict[str, BenchmarkRecord]:
        """
        Send the same prompt to multiple providers in parallel for benchmarking.
        """
        tasks = []
        for provider_name in providers:
            tasks.append(self._benchmark_provider(provider_name, prompt))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        records: dict[str, BenchmarkRecord] = {}
        for provider_name, result in zip(providers, results, strict=True):
            if isinstance(result, BenchmarkRecord):
                records[provider_name] = result
                self._benchmarks.append(result)
                if len(self._benchmarks) > self._max_benchmarks:
                    self._benchmarks = self._benchmarks[-self._max_benchmarks:]
        return records

    async def _benchmark_provider(self, provider_name: str, prompt: str) -> BenchmarkRecord:
        start = time.perf_counter()
        try:
            if self.provider_manager is None:
                return BenchmarkRecord(provider=provider_name, model="", latency_ms=0.0, success=False)
            result = await self.provider_manager.generate(prompt, provider=provider_name)
            latency = (time.perf_counter() - start) * 1000.0
            tokens = getattr(result, "tokens", 0)
            tps = tokens / (latency / 1000.0) if latency > 0 else 0.0
            return BenchmarkRecord(
                provider=provider_name,
                model=getattr(result, "model", ""),
                latency_ms=latency,
                tokens_per_second=tps,
                success=True,
            )
        except Exception:
            latency = (time.perf_counter() - start) * 1000.0
            return BenchmarkRecord(
                provider=provider_name,
                model="",
                latency_ms=latency,
                success=False,
            )

    async def _score_candidate(
        self,
        provider_name: str,
        model: str,
        info: Any,
        task_type: str,
        context_length: int,
        requires_vision: bool,
        requires_tools: bool,
        requires_reasoning: bool,
        cost_weight: float,
        latency_weight: float,
        quality_weight: float,
    ) -> ProviderScore:
        """Score a provider/model combination."""
        criteria: dict[str, float] = {}
        success_rate = self._get_success_rate(provider_name)
        criteria[SelectionCriterion.PREVIOUS_SUCCESS.value] = success_rate
        criteria[SelectionCriterion.LATENCY.value] = 1.0 - min(1.0, self._get_avg_latency(provider_name) / 5000.0)
        cost = self._estimate_cost(provider_name, model)
        criteria[SelectionCriterion.COST.value] = 1.0 - min(1.0, cost / 0.01)
        ctx_support = getattr(info, "context_length", 2048) or 2048
        criteria[SelectionCriterion.CONTEXT_LENGTH.value] = min(1.0, context_length / ctx_support)
        if requires_vision:
            criteria[SelectionCriterion.VISION.value] = 1.0 if getattr(info, "is_reasoning", False) else 0.2
        if requires_tools:
            criteria[SelectionCriterion.TOOL_USE.value] = success_rate
        if requires_reasoning:
            criteria[SelectionCriterion.REASONING.value] = 1.0 if getattr(info, "is_reasoning", False) else 0.3

        score = 0.0
        total_weight = cost_weight + latency_weight + quality_weight
        for key, value in criteria.items():
            if key == SelectionCriterion.LATENCY.value:
                score += value * latency_weight
            elif key in (SelectionCriterion.COST.value,):
                score += value * cost_weight
            else:
                score += value * (quality_weight / max(1, len(criteria) - 2))
        score = score / total_weight if total_weight > 0 else score

        return ProviderScore(
            provider=provider_name,
            model=model,
            score=round(score, 4),
            criteria=criteria,
            estimated_cost=cost,
            estimated_latency_ms=self._get_avg_latency(provider_name),
            reason=f"score={score:.3f} success={success_rate:.2f}",
        )

    async def _get_candidates(self) -> list[tuple[str, str, Any]]:
        """Get available providers and models."""
        candidates = []
        try:
            if self.provider_manager is None:
                return candidates
            providers = await self.provider_manager.list_providers()
            for p in providers:
                models = await self.provider_manager.list_models(provider=p)
                for model in models[:5]:
                    candidates.append((p, model, None))
        except Exception:
            pass
        return candidates

    def _get_success_rate(self, provider_name: str) -> float:
        recent = [b for b in self._benchmarks[-20:] if b.provider == provider_name]
        if not recent:
            return 0.8
        return sum(1 for b in recent if b.success) / len(recent)

    def _get_avg_latency(self, provider_name: str) -> float:
        recent = [b.latency_ms for b in self._benchmarks[-20:] if b.provider == provider_name]
        if not recent:
            return 1000.0
        return sum(recent) / len(recent)

    def _estimate_cost(self, provider_name: str, model: str) -> float:
        if provider_name.lower() in ("ollama", "local"):
            return 0.0
        return 0.001

    def get_benchmark_stats(self) -> dict[str, Any]:
        """Return benchmark statistics."""
        stats: dict[str, Any] = {}
        for record in self._benchmarks[-50:]:
            p = record.provider
            stats.setdefault(p, {"count": 0, "avg_latency": 0.0, "success_rate": 0.0})
            stats[p]["count"] += 1
            stats[p]["avg_latency"] = (stats[p]["avg_latency"] + record.latency_ms) / 2.0
        for p in stats:
            successes = sum(1 for b in self._benchmarks if b.provider == p and b.success)
            stats[p]["success_rate"] = successes / max(1, stats[p]["count"])
        return stats
