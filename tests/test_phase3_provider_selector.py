"""
Phase 3 Provider Selector Tests
"""

import pytest

from jarvis.providers.selector import ProviderScore, ProviderSelector


@pytest.mark.asyncio
async def test_select_no_manager():
    selector = ProviderSelector(provider_manager=None)
    score = await selector.select(task_type="general")
    assert score is None


@pytest.mark.asyncio
async def test_benchmark_stats_empty():
    selector = ProviderSelector()
    stats = selector.get_benchmark_stats()
    assert stats == {}


@pytest.mark.asyncio
async def test_score_candidate_values():
    selector = ProviderSelector()
    score = await selector._score_candidate(
        provider_name="ollama",
        model="llama3",
        info=None,
        task_type="general",
        context_length=2048,
        requires_vision=False,
        requires_tools=False,
        requires_reasoning=False,
        cost_weight=0.3,
        latency_weight=0.4,
        quality_weight=0.3,
    )
    assert isinstance(score, ProviderScore)
    assert score.provider == "ollama"
