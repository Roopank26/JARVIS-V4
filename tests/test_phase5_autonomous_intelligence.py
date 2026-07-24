"""
Tests for JARVIS Phase 5 — Autonomous Intelligence.
"""

from __future__ import annotations

import pytest

from jarvis.benchmarks.tracker import get_benchmark_tracker
from jarvis.core.self_evaluation import get_self_evaluation_engine
from jarvis.evolution.root_cause import get_root_cause_learner
from jarvis.goals import get_goal_engine, get_long_horizon_planner
from jarvis.intelligence.autonomous_engine import get_autonomous_intelligence_engine
from jarvis.intelligence.context_fusion import (
    SourceWeight,
    UnifiedContext,
    get_context_fusion_engine,
)
from jarvis.intelligence.meta_reasoning import (
    get_meta_reasoning_engine,
)
from jarvis.tools.intelligence import (
    ToolOutcome,
    get_tool_intelligence_engine,
)


class TestMetaReasoning:
    def test_get_meta_reasoning_singleton(self):
        r1 = get_meta_reasoning_engine()
        r2 = get_meta_reasoning_engine()
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_evaluate_task_success(self):
        engine = get_meta_reasoning_engine()
        confidence = engine.evaluate_task(
            task_id="task_1",
            description="search for python",
            result="Found 3 results",
            duration_ms=1200,
            components=["search", "format"],
        )
        assert confidence.confidence > 0.0
        assert confidence.reasoning_quality >= 0.0

    @pytest.mark.asyncio
    async def test_evaluate_task_failure(self):
        engine = get_meta_reasoning_engine()
        confidence = engine.evaluate_task(
            task_id="task_2",
            description="download file",
            result="error: timeout",
            duration_ms=15000,
            components=["download"],
        )
        assert confidence.confidence < 0.5

    @pytest.mark.asyncio
    async def test_detect_weaknesses(self):
        engine = get_meta_reasoning_engine()
        report = engine.detect_weaknesses("task_3", "error: not found", duration_ms=2000)
        assert "resource_gap" in report.weaknesses
        assert report.severity in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_suggest_improvements(self):
        engine = get_meta_reasoning_engine()
        engine.detect_weaknesses("t1", "timeout", duration_ms=20000)
        suggestions = engine.suggest_improvements("t2", "global")
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_record_meta_lesson(self):
        engine = get_meta_reasoning_engine()
        lesson = engine.record_meta_lesson(
            task_id="task_4",
            category="performance",
            insight="Slow execution detected",
            actionable="Use caching",
            confidence=0.7,
        )
        assert lesson.insight == "Slow execution detected"
        assert lesson.actionable == "Use caching"

    @pytest.mark.asyncio
    async def test_get_autonomous_insights(self):
        engine = get_meta_reasoning_engine()
        insights = engine.get_autonomous_insights()
        assert "total_evaluated" in insights or insights.get("status") == "insufficient_data"


class TestLongHorizonPlanning:
    def test_get_long_horizon_singleton(self):
        p1 = get_long_horizon_planner()
        p2 = get_long_horizon_planner()
        assert p1 is p2

    def test_analyze_goal(self):
        planner = get_long_horizon_planner()
        engine = get_goal_engine()
        goal = engine.create_goal("Learn Rust", "Complete Rust book", goal_type="learning")
        analysis = planner.analyze_goal(goal.goal_id)
        assert analysis is not None
        assert analysis["goal_id"] == goal.goal_id

    def test_decompose_milestone(self):
        planner = get_long_horizon_planner()
        engine = get_goal_engine()
        goal = engine.create_goal("Build API", "Build REST API", goal_type="project")
        tasks = planner.decompose_milestone(goal.goal_id, "Setup", ["Design schema", "Create models"])
        assert len(tasks) == 2

    def test_get_progress_trend(self):
        planner = get_long_horizon_planner()
        engine = get_goal_engine()
        goal = engine.create_goal("Test Trend", "Test")
        trend = planner.get_progress_trend(goal.goal_id)
        assert "goal_id" in trend


class TestContextFusion:
    def test_get_context_fusion_singleton(self):
        c1 = get_context_fusion_engine()
        c2 = get_context_fusion_engine()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_fuse_returns_context(self):
        engine = get_context_fusion_engine()
        ctx = await engine.fuse("What is my favorite color?")
        assert isinstance(ctx, UnifiedContext)
        assert ctx.query == "What is my favorite color?"
        assert isinstance(ctx.fused_summary, str)

    @pytest.mark.asyncio
    async def test_fuse_with_extra_context(self):
        engine = get_context_fusion_engine()
        ctx = await engine.fuse("test query", extra_context={"summary": "extra info"})
        assert "EXTRA CONTEXT" in ctx.fused_summary

    def test_source_weight(self):
        sw = SourceWeight(source="test", weight=0.5, max_items=3, enabled=True)
        assert sw.source == "test"
        assert sw.weight == 0.5


class TestToolIntelligence:
    def test_get_tool_intelligence_singleton(self):
        t1 = get_tool_intelligence_engine()
        t2 = get_tool_intelligence_engine()
        assert t1 is t2

    def test_estimate_tool(self):
        engine = get_tool_intelligence_engine()
        estimate = engine.estimate("search_web", context="find python tutorials")
        assert estimate.tool_name == "search_web"
        assert 0.0 <= estimate.confidence <= 1.0
        assert estimate.expected_usefulness >= 0.0

    def test_record_outcome(self):
        engine = get_tool_intelligence_engine()
        engine.record_outcome(
            ToolOutcome(tool_name="test_tool", success=True, latency_ms=500.0)
        )
        rep = engine.get_tool_reputation("test_tool")
        assert rep is not None
        assert rep.total_calls == 1
        assert rep.success_rate == 1.0

    def test_get_top_tools(self):
        engine = get_tool_intelligence_engine()
        tops = engine.get_top_tools(limit=5)
        assert isinstance(tops, list)

    def test_get_underperforming_tools(self):
        engine = get_tool_intelligence_engine()
        under = engine.get_underperforming_tools(threshold=0.5)
        assert isinstance(under, list)


class TestSelfEvaluation:
    def test_get_self_evaluation_singleton(self):
        s1 = get_self_evaluation_engine()
        s2 = get_self_evaluation_engine()
        assert s1 is s2

    def test_evaluate_response(self):
        engine = get_self_evaluation_engine()
        score = engine.evaluate_response(
            response_id="resp_1",
            reasoning_steps=3,
            plan_steps=2,
            memory_hits=2,
            tools_used=1,
            success=True,
            latency_ms=800.0,
            confidence=0.8,
            output_length=200,
        )
        assert score.overall > 0.0
        assert score.reasoning > 0.0
        assert score.completeness > 0.0

    def test_get_trend(self):
        engine = get_self_evaluation_engine()
        trend = engine.get_trend(dimension="overall", limit=10)
        assert isinstance(trend, list)

    def test_get_monthly_summary(self):
        engine = get_self_evaluation_engine()
        summary = engine.get_monthly_summary()
        assert "status" in summary or "month" in summary

    def test_get_dimension_stats(self):
        engine = get_self_evaluation_engine()
        stats = engine.get_dimension_stats("overall")
        assert "count" in stats or stats.get("status") == "no_data"


class TestRootCauseLearning:
    def test_get_root_cause_learner_singleton(self):
        r1 = get_root_cause_learner()
        r2 = get_root_cause_learner()
        assert r1 is r2

    def test_analyze_failure_timeout(self):
        learner = get_root_cause_learner()
        rc = learner.analyze_failure("task_1", "download", "error: timeout", duration_ms=20000)
        assert rc is not None
        assert rc.category == "latency"

    def test_analyze_failure_permission(self):
        learner = get_root_cause_learner()
        rc = learner.analyze_failure("task_2", "write file", "error: permission denied", duration_ms=1000)
        assert rc is not None
        assert rc.category == "permission"

    def test_get_prevention_rule(self):
        learner = get_root_cause_learner()
        rule = learner.get_or_create_prevention_rule("network", "network failure", "retry with backoff")
        assert rule.condition == "network failure"
        assert rule.action == "retry with backoff"
        triggered = learner.trigger_prevention("network")
        assert triggered == "retry with backoff"

    def test_get_recurring_failures(self):
        learner = get_root_cause_learner()
        learner.analyze_failure("t1", "desc", "error: timeout", duration_ms=20000)
        recurring = learner.get_recurring_failures(limit=10)
        assert isinstance(recurring, list)


class TestBenchmarkTracker:
    def test_get_benchmark_tracker_singleton(self):
        b1 = get_benchmark_tracker()
        b2 = get_benchmark_tracker()
        assert b1 is b2

    def test_record_monthly_scores(self):
        tracker = get_benchmark_tracker()
        tracker.record_monthly_scores({
            "reasoning_quality": 0.8,
            "planning_quality": 0.7,
        })
        summary = tracker.get_summary()
        assert "latest_month" in summary or summary.get("status") == "no_data"

    def test_get_trend(self):
        tracker = get_benchmark_tracker()
        trend = tracker.get_trend("reasoning_quality", months=6)
        assert isinstance(trend, list)

    def test_get_all_trends(self):
        tracker = get_benchmark_tracker()
        trends = tracker.get_all_trends(months=1)
        assert isinstance(trends, dict)

    def test_get_deltas(self):
        tracker = get_benchmark_tracker()
        deltas = tracker.get_deltas(months=2)
        assert isinstance(deltas, dict)


class TestAutonomousEngine:
    def test_get_autonomous_engine_singleton(self):
        a1 = get_autonomous_intelligence_engine()
        a2 = get_autonomous_intelligence_engine()
        assert a1 is a2

    def test_estimate_tool(self):
        engine = get_autonomous_intelligence_engine()
        estimate = engine.estimate_tool("search_web", "find info")
        assert "tool_name" in estimate
        assert estimate["tool_name"] == "search_web"

    def test_record_tool_outcome(self):
        engine = get_autonomous_intelligence_engine()
        engine.record_tool_outcome("search_web", success=True, latency_ms=1200.0)
        rep = engine._tool_intel.get_tool_reputation("search_web")
        assert rep is not None
        assert rep.total_calls >= 1

    def test_get_autonomous_insights(self):
        engine = get_autonomous_intelligence_engine()
        insights = engine.get_autonomous_insights()
        assert "meta_reasoning" in insights
        assert "tool_intelligence" in insights
        assert "benchmarks" in insights
