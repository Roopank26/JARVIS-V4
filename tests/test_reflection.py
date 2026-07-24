"""
Tests for Phase 2.2 - Reflection Engine.
"""

import pytest

from jarvis.core.reflection import ReflectionEngine, get_reflection_engine


class TestReflectionEngine:
    @pytest.mark.asyncio
    async def test_reflect_success(self):
        engine = ReflectionEngine()
        outcome = await engine.reflect("search for python tutorials", "Found 3 results", duration_ms=1200)
        assert outcome.success is True
        assert outcome.duration_ms == 1200

    @pytest.mark.asyncio
    async def test_reflect_failure(self):
        engine = ReflectionEngine()
        outcome = await engine.reflect("download file", "error: timeout", duration_ms=5000)
        assert outcome.success is False
        assert outcome.error is not None

    @pytest.mark.asyncio
    async def test_reflect_generates_lessons(self):
        engine = ReflectionEngine()
        outcome = await engine.reflect("plan and execute steps", "completed successfully", duration_ms=3000)
        assert len(outcome.lessons) > 0

    @pytest.mark.asyncio
    async def test_reflect_generates_recommendations_on_failure(self):
        engine = ReflectionEngine()
        outcome = await engine.reflect("complex task", "failed: step 2 error", duration_ms=1000)
        assert len(outcome.recommendations) > 0

    @pytest.mark.asyncio
    async def test_reflection_history(self):
        engine = ReflectionEngine()
        await engine.reflect("task1", "result1")
        await engine.reflect("task2", "error: failed")
        history = engine.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_reflection_history_limit(self):
        engine = ReflectionEngine()
        for i in range(25):
            await engine.reflect(f"task{i}", "result")
        history = engine.get_history(limit=10)
        assert len(history) == 10

    def test_get_reflection_engine_singleton(self):
        r1 = get_reflection_engine()
        r2 = get_reflection_engine()
        assert r1 is r2
