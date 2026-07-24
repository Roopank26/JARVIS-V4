"""
Phase 3 Continuous Learning Engine Tests
"""


import pytest

from jarvis.learning.engine import ContinuousLearningEngine


@pytest.mark.asyncio
async def test_record_experience():
    engine = ContinuousLearningEngine()
    exp = await engine.record_experience(
        task_id="t1",
        input_text="research AI news",
        output_text="Here is what I found",
        success=True,
        duration_ms=500.0,
    )
    assert exp.success is True
    assert isinstance(exp.lessons, list)


@pytest.mark.asyncio
async def test_record_decision():
    engine = ContinuousLearningEngine()
    rec = engine.record_decision("vision task", "use_gpt4v", "success", 0.9)
    assert rec.choice == "use_gpt4v"
    assert rec.score == 0.9


def test_get_pattern_insights_empty():
    engine = ContinuousLearningEngine()
    insights = engine.get_pattern_insights()
    assert insights["total_experiences"] == 0


def test_get_improvement_suggestions_empty():
    engine = ContinuousLearningEngine()
    suggestions = engine.get_improvement_suggestions()
    assert isinstance(suggestions, list)
