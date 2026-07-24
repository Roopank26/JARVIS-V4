"""
Distributed Intelligence for JARVIS.

Allows multiple providers to cooperate, routing sub-tasks to specialist models.
"""

from __future__ import annotations

import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from jarvis.providers.selector import ProviderSelector

logger = logging.getLogger(__name__)


@dataclass
class DistributedResult:
    provider: str
    model: str
    output: Any
    latency_ms: float = 0.0
    tokens: int = 0
    confidence: float = 1.0


class DistributedIntelligence:
    def __init__(self, selector: ProviderSelector | None = None) -> None:
        self._selector = selector or ProviderSelector()

    async def execute(self, tasks: list[dict[str, Any]]) -> list[DistributedResult]:
        results: list[DistributedResult] = []
        for task in tasks:
            try:
                result = await self._execute_single(task)
                results.append(result)
            except Exception as exc:
                logger.debug("Distributed task failed: %s", exc)
                results.append(DistributedResult(
                    provider="none",
                    model="none",
                    output=None,
                    confidence=0.0,
                ))
        return results

    async def _execute_single(self, task: dict[str, Any]) -> DistributedResult:
        task_type = task.get("type", "general")
        requires_vision = task.get("requires_vision", False)
        requires_tools = task.get("requires_tools", False)
        requires_reasoning = task.get("requires_reasoning", False)
        prompt = task.get("prompt", "")

        score = await self._selector.select(
            task_type=task_type,
            context_length=task.get("context_length", 2048),
            requires_vision=requires_vision,
            requires_tools=requires_tools,
            requires_reasoning=requires_reasoning,
        )

        if score is None:
            return DistributedResult(provider="none", model="none", output="No provider available", confidence=0.0)

        provider_manager = self._selector.provider_manager
        if provider_manager is None:
            return DistributedResult(provider=score.provider, model=score.model, output="Provider manager unavailable", confidence=0.0)

        start = time.perf_counter()
        try:
            response = await provider_manager.generate(prompt, provider=score.provider, model=score.model)
            latency = (time.perf_counter() - start) * 1000.0
            return DistributedResult(
                provider=score.provider,
                model=score.model,
                output=getattr(response, "text", str(response)),
                latency_ms=round(latency, 2),
                tokens=getattr(response, "tokens", 0),
                confidence=score.score,
            )
        except Exception:
            latency = (time.perf_counter() - start) * 1000.0
            return DistributedResult(
                provider=score.provider,
                model=score.model,
                output=None,
                latency_ms=round(latency, 2),
                confidence=0.0,
            )

    async def execute_with_fallback(
        self,
        primary_task: dict[str, Any],
        fallback_tasks: list[dict[str, Any]] | None = None,
    ) -> DistributedResult | None:
        result = await self._execute_single(primary_task)
        if result.confidence > 0.3 and result.output:
            return result
        if fallback_tasks:
            for fallback in fallback_tasks:
                result = await self._execute_single(fallback)
                if result.confidence > 0.3 and result.output:
                    return result
        return result

    def health_check(self) -> dict[str, Any]:
        stats = {}
        with suppress(Exception):
            stats = self._selector.get_benchmark_stats()
        return {
            "healthy": self._selector is not None,
            "provider_stats": stats,
        }
