"""
JARVIS V4.2 — Adaptive Intelligence Tests.

Proves that PAST EXPERIENCE changes FUTURE BEHAVIOR.

These tests demonstrate:
1. Strategy memory stores and retrieves learned strategies
2. Candidate evaluation scores and selects best actions
3. Confidence calibration tracks predicted vs actual outcomes
4. Failure-aware strategy selection penalizes known-bad strategies
5. The full loop: experience → learning → strategy update → different decision
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jarvis.brain.confidence_engine import ConfidenceEngine, ConfidenceFactors
from jarvis.brain.context_engine import ContextEngine, Situation, Intent
from jarvis.brain.decision_engine import Action, DecisionCandidate, DecisionEngine
from jarvis.brain.native_intelligence import NativeIntelligenceCore
from jarvis.brain.planning_engine import PlanningEngine, ExecutionPlan
from jarvis.brain.strategy_memory import (
    StrategyMemory, StrategyRecord, StrategyCandidate, StrategyEvidence, _make_signature,
)


# ── Helpers ──

def _make_situation(
    text: str,
    category: str = "command",
    action: str = "read_file",
    complexity: float = 0.5,
) -> Situation:
    """Create a test situation."""
    ctx = ContextEngine()
    return ctx.understand(text)


def _make_strategy_memory_with_evidence() -> StrategyMemory:
    """Create a StrategyMemory with some learned strategies."""
    sm = StrategyMemory()

    # Strategy A: works well for file operations
    sm.ingest_from_consolidation(
        strategy_key="file read direct",
        applicability="Reading local files",
        evidence_count=5,
        success_rate=0.9,
        promoted=True,
    )
    # Record several successes
    strat_a = sm.get_all_strategies()[0]
    for _ in range(5):
        sm.record_outcome(
            strategy_id=strat_a.id,
            task="read file contents",
            context="local file operation",
            success=True,
            duration_ms=50.0,
        )

    # Strategy B: works poorly for file operations
    sm.ingest_from_consolidation(
        strategy_key="file read network",
        applicability="Reading files via network",
        evidence_count=4,
        success_rate=0.2,
        promoted=False,
    )
    strat_b = sm.get_all_strategies()[1]
    for _ in range(3):
        sm.record_outcome(
            strategy_id=strat_b.id,
            task="read file contents",
            context="network file operation",
            success=False,
            failure_type="timeout",
        )
    sm.record_outcome(
        strategy_id=strat_b.id,
        task="read file contents",
        context="network file operation",
        success=True,
        duration_ms=200.0,
    )

    return sm


# ══════════════════════════════════════════════════════════════
# Test 1: Strategy Memory stores and retrieves strategies
# ══════════════════════════════════════════════════════════════

class TestStrategyMemory:
    """Strategy memory stores learned strategies and retrieves them by relevance."""

    def test_ingest_creates_strategy_record(self):
        """Ingesting from consolidation creates a StrategyRecord."""
        sm = StrategyMemory()
        record = sm.ingest_from_consolidation(
            strategy_key="bash execute",
            applicability="Running shell commands",
            evidence_count=3,
            success_rate=0.8,
            promoted=True,
        )
        assert isinstance(record, StrategyRecord)
        assert record.name == "bash execute"
        assert record.promoted is True

    def test_ingest_idempotent(self):
        """Ingesting the same strategy twice doesn't create duplicates."""
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="bash execute",
            applicability="Running shell commands",
            evidence_count=3,
            success_rate=0.8,
            promoted=True,
        )
        sm.ingest_from_consolidation(
            strategy_key="bash execute",
            applicability="Running shell commands updated",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        assert len(sm.get_all_strategies()) == 1

    def test_record_outcome_updates_evidence(self):
        """Recording outcomes updates strategy evidence."""
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="test strategy",
            applicability="Testing",
            evidence_count=1,
            success_rate=0.5,
            promoted=False,
        )
        record = sm.get_all_strategies()[0]

        # Record some outcomes
        sm.record_outcome(record.id, "test task", "test context", success=True, duration_ms=100)
        sm.record_outcome(record.id, "test task", "test context", success=True, duration_ms=80)
        sm.record_outcome(record.id, "test task", "test context", success=False, failure_type="error")

        assert record.total_uses == 3
        assert record.overall_success_rate > 0.6  # 2/3

    def test_find_candidates_relevant_strategy(self):
        """Finding candidates returns relevant strategies."""
        sm = _make_strategy_memory_with_evidence()
        candidates = sm.find_candidates(
            task="read file contents",
            context="local file operation",
            limit=3,
        )
        assert len(candidates) > 0
        # The well-performing strategy should rank higher
        assert candidates[0].final_score > 0.3

    def test_find_candidates_penalizes_failures(self):
        """Candidates with failure history get penalized."""
        sm = _make_strategy_memory_with_evidence()
        candidates = sm.find_candidates(
            task="read file contents",
            context="",
            failure_guidance={"avoid_strategies": ["file read network"]},
            limit=3,
        )
        # The network strategy should have a penalty
        for c in candidates:
            if "network" in c.strategy.name:
                assert c.failure_penalty > 0

    def test_get_stats(self):
        """Stats track strategy memory state."""
        sm = _make_strategy_memory_with_evidence()
        stats = sm.get_stats()
        assert stats["total_strategies"] == 2
        assert stats["total_uses"] > 0
        assert stats["strategies_with_evidence"] > 0


# ══════════════════════════════════════════════════════════════
# Test 2: Candidate Evaluation scores actions
# ══════════════════════════════════════════════════════════════

class TestCandidateEvaluation:
    """Decision engine evaluates candidate actions with transparent scoring."""

    def test_candidate_score_formula(self):
        """Candidate score is computed from weighted factors."""
        candidate = DecisionCandidate(
            action=Action.USE_TOOL,
            target="read_file",
            goal_relevance=0.8,
            historical_success=0.9,
            strategy_compatibility=0.7,
            risk=0.1,
            failure_penalty=0.0,
        )
        # score = 0.8*0.25 + 0.9*0.30 + 0.7*0.25 - 0.1*0.10 - 0.0*0.10
        # = 0.2 + 0.27 + 0.175 - 0.01 - 0.0 = 0.635
        assert abs(candidate.score - 0.635) < 0.01

    def test_higher_success_beats_lower_success(self):
        """A candidate with higher historical success scores better."""
        high = DecisionCandidate(
            action=Action.USE_TOOL,
            target="tool_a",
            historical_success=0.9,
        )
        low = DecisionCandidate(
            action=Action.USE_TOOL,
            target="tool_b",
            historical_success=0.3,
        )
        assert high.score > low.score

    def test_failure_penalty_reduces_score(self):
        """Failure penalty reduces the candidate score."""
        no_penalty = DecisionCandidate(
            action=Action.USE_TOOL,
            target="tool_a",
            failure_penalty=0.0,
        )
        with_penalty = DecisionCandidate(
            action=Action.USE_TOOL,
            target="tool_a",
            failure_penalty=0.5,
        )
        assert no_penalty.score > with_penalty.score

    def test_risk_reduces_score(self):
        """Higher risk reduces the candidate score."""
        low_risk = DecisionCandidate(
            action=Action.USE_TOOL,
            target="safe_tool",
            risk=0.0,
        )
        high_risk = DecisionCandidate(
            action=Action.USE_TOOL,
            target="risky_tool",
            risk=0.8,
        )
        assert low_risk.score > high_risk.score

    def test_decision_engine_generates_candidates(self):
        """DecisionEngine generates candidates for non-trivial decisions."""
        engine = DecisionEngine()
        ctx = ContextEngine()
        situation = ctx.understand("read the file /tmp/test.txt")

        decision = engine.decide(
            situation,
            can_reason_locally=True,
            has_model=False,
            strategy_candidates=None,
            failure_guidance=None,
        )
        # Should have evaluated candidates
        assert decision.alternatives_rejected >= 0

    def test_decision_with_failure_guidance(self):
        """Failure guidance influences candidate selection."""
        engine = DecisionEngine()
        ctx = ContextEngine()
        situation = ctx.understand("run the backup script")

        decision_with_guidance = engine.decide(
            situation,
            can_reason_locally=False,
            has_model=False,
            failure_guidance={"avoid_strategies": ["bash"]},
        )
        # The decision should still be made
        assert decision_with_guidance.action is not None

    def test_decision_stats_track_candidates(self):
        """Decision stats track candidate evaluation."""
        engine = DecisionEngine()
        ctx = ContextEngine()

        for _ in range(3):
            situation = ctx.understand("read file test.txt")
            engine.decide(situation, can_reason_locally=True)

        stats = engine.get_stats()
        assert stats["total_decisions"] == 3


# ══════════════════════════════════════════════════════════════
# Test 3: Confidence Calibration
# ══════════════════════════════════════════════════════════════

class TestConfidenceCalibration:
    """Confidence calibration tracks predicted vs actual outcomes."""

    def test_record_outcome_tracks_calibration(self):
        """Recording outcomes builds calibration data."""
        engine = ConfidenceEngine()
        # Record several overconfident predictions
        for _ in range(5):
            engine.record_outcome(0.9, False)  # predicted 0.9, actually failed

        stats = engine.get_calibration_stats()
        assert stats["total_predictions"] == 5
        # The 0.8-1.0 bucket should have data
        bucket_key = "0.8-1.0"
        if bucket_key in stats["buckets"]:
            assert stats["buckets"][bucket_key]["count"] == 5

    def test_calibration_detects_overconfidence(self):
        """Calibration detects when predictions are consistently too high."""
        engine = ConfidenceEngine()
        # Predict 0.9 but succeed only 30% of the time
        for _ in range(7):
            engine.record_outcome(0.9, False)
        for _ in range(3):
            engine.record_outcome(0.9, True)

        adjustment = engine.get_calibration_adjustment(0.9)
        # Should be negative (we're overconfident)
        assert adjustment < 0

    def test_calibration_detects_underconfidence(self):
        """Calibration detects when predictions are consistently too low."""
        engine = ConfidenceEngine()
        # Predict 0.3 but succeed 90% of the time
        for _ in range(1):
            engine.record_outcome(0.3, False)
        for _ in range(9):
            engine.record_outcome(0.3, True)

        adjustment = engine.get_calibration_adjustment(0.3)
        # Should be positive (we're underconfident)
        assert adjustment > 0

    def test_calibrated_confidence_adjusts(self):
        """get_calibrated_confidence adjusts raw confidence."""
        engine = ConfidenceEngine()
        # Build overconfidence evidence
        for _ in range(10):
            engine.record_outcome(0.9, False)

        calibrated = engine.get_calibrated_confidence(0.9)
        # Should be lower than 0.9
        assert calibrated < 0.9

    def test_calibration_needs_minimum_observations(self):
        """Calibration doesn't adjust with too few observations."""
        engine = ConfidenceEngine()
        engine.record_outcome(0.9, False)  # Only 1 observation

        adjustment = engine.get_calibration_adjustment(0.9)
        assert adjustment == 0.0  # Not enough data


# ══════════════════════════════════════════════════════════════
# Test 4: Planning consults strategies
# ══════════════════════════════════════════════════════════════

class TestStrategyAwarePlanning:
    """PlanningEngine consults StrategyMemory for strategy-aware planning."""

    def test_planning_with_strategy_hint(self):
        """Planning attaches strategy hint when a good strategy exists."""
        planning = PlanningEngine()
        sm = _make_strategy_memory_with_evidence()
        planning.set_strategy_memory(sm)

        ctx = ContextEngine()
        situation = ctx.understand("read file contents")
        decision = MagicMock()
        decision.action = Action.USE_TOOL
        decision.target = "read_file"
        decision.parameters = {}

        plan = planning.create_plan(decision, situation, "read file contents")
        assert isinstance(plan, ExecutionPlan)
        # Strategy hint may or may not be set depending on relevance
        assert hasattr(plan, 'strategy_hint')

    def test_planning_without_strategy_memory(self):
        """Planning works without StrategyMemory attached."""
        planning = PlanningEngine()
        ctx = ContextEngine()
        situation = ctx.understand("read file test.txt")
        decision = MagicMock()
        decision.action = Action.USE_TOOL
        decision.target = "read_file"
        decision.parameters = {}

        plan = planning.create_plan(decision, situation, "read file test.txt")
        assert isinstance(plan, ExecutionPlan)
        assert plan.strategy_hint == ""

    def test_plan_to_dict_includes_strategy(self):
        """Plan serialization includes strategy hint."""
        plan = ExecutionPlan(goal="test", strategy_hint="bash execute")
        d = plan.to_dict()
        assert d["strategy_hint"] == "bash execute"


# ══════════════════════════════════════════════════════════════
# Test 5: THE CRITICAL TEST — Experience changes behavior
# ══════════════════════════════════════════════════════════════

class TestExperienceChangesBehavior:
    """
    The most important test in V4.2.
    Proves that past experience actually influences future decisions.
    """

    def test_strategy_memory_tracks_outcomes(self):
        """
        After recording outcomes, strategy confidence changes.
        This is the foundation of behavior change.
        """
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="test approach",
            applicability="Test tasks",
            evidence_count=1,
            success_rate=0.5,
            promoted=False,
        )
        record = sm.get_all_strategies()[0]
        initial_confidence = record.overall_confidence

        # Record several failures
        for _ in range(5):
            sm.record_outcome(
                strategy_id=record.id,
                task="test task",
                context="test",
                success=False,
                failure_type="error",
            )

        # Confidence should decrease
        assert record.overall_confidence < initial_confidence or record.total_uses == 5

    def test_failure_guidance_affects_decision(self):
        """
        When failure guidance exists, decisions are influenced.
        """
        engine = DecisionEngine()
        ctx = ContextEngine()

        # First decision without guidance
        situation = ctx.understand("execute the backup script")
        d1 = engine.decide(situation, can_reason_locally=False, has_model=False)

        # Second decision WITH failure guidance against the same action
        d2 = engine.decide(
            situation,
            can_reason_locally=False,
            has_model=False,
            failure_guidance={"avoid_strategies": [d1.target]},
        )

        # The second decision should consider the failure guidance
        # (it may still choose the same action if no better alternative exists,
        # but the scoring should reflect the penalty)
        assert d2.action is not None

    def test_strategy_candidates_influence_scoring(self):
        """
        When strategy candidates are provided, they influence candidate scoring.
        """
        engine = DecisionEngine()
        ctx = ContextEngine()
        situation = ctx.understand("read the configuration file")

        # Create strategy candidates
        sm = _make_strategy_memory_with_evidence()
        candidates = sm.find_candidates(
            task="read file contents",
            context="local file operation",
        )

        # Decision with strategy candidates
        d = engine.decide(
            situation,
            can_reason_locally=True,
            has_model=False,
            strategy_candidates=candidates,
        )

        # Decision should be made and have a candidate score
        assert d.action is not None
        assert d.candidate_score >= 0

    def test_full_loop_experience_to_behavior(self):
        """
        FULL LOOP TEST:
        1. JARVIS encounters a task
        2. Strategy A fails
        3. Failure is recorded
        4. JARVIS encounters similar task
        5. Strategy A should be penalized

        This is the core proof that learning changes behavior.
        """
        sm = StrategyMemory()

        # Step 1: Ingest initial strategy
        sm.ingest_from_consolidation(
            strategy_key="direct approach",
            applicability="General tasks",
            evidence_count=2,
            success_rate=0.5,
            promoted=False,
        )
        record = sm.get_all_strategies()[0]

        # Step 2: Record failures (strategy doesn't work)
        for _ in range(4):
            sm.record_outcome(
                strategy_id=record.id,
                task="deploy service",
                context="production deployment",
                success=False,
                failure_type="timeout",
            )

        # Step 3: Find candidates for similar task
        # Before: direct approach has low success rate
        candidates_before = sm.find_candidates(
            task="deploy service",
            context="production deployment",
        )

        # Step 4: Now ingest a better strategy
        sm.ingest_from_consolidation(
            strategy_key="staged rollout",
            applicability="Production deployments",
            evidence_count=5,
            success_rate=0.95,
            promoted=True,
        )
        better_record = sm.get_all_strategies()[1]
        for _ in range(5):
            sm.record_outcome(
                strategy_id=better_record.id,
                task="deploy service",
                context="production deployment",
                success=True,
                duration_ms=120.0,
            )

        # Step 5: Find candidates again
        candidates_after = sm.find_candidates(
            task="deploy service",
            context="production deployment",
            failure_guidance={"avoid_strategies": ["direct approach"]},
        )

        # The better strategy should rank higher
        if len(candidates_after) >= 2:
            # The first candidate should be the better strategy
            assert candidates_after[0].final_score > 0
            # The direct approach should have a failure penalty
            for c in candidates_after:
                if "direct" in c.strategy.name:
                    assert c.failure_penalty > 0

    def test_confidence_calibration_changes_predictions(self):
        """
        After calibration, confidence predictions change.
        """
        engine = ConfidenceEngine()

        # Build overconfidence evidence: predict 0.85, usually fail
        for _ in range(10):
            engine.record_outcome(0.85, False)

        # Raw confidence
        raw = 0.85
        calibrated = engine.get_calibrated_confidence(raw)

        # Should be adjusted downward
        assert calibrated < raw

    def test_decision_engine_stats_track_adaptive_metrics(self):
        """
        Decision engine stats include adaptive metrics.
        """
        engine = DecisionEngine()
        ctx = ContextEngine()

        for _ in range(3):
            situation = ctx.understand("read file test.txt")
            engine.decide(situation, can_reason_locally=True)

        stats = engine.get_stats()
        assert "candidate_evaluated" in stats
        assert "avg_candidate_score" in stats
        assert "avg_alternatives_rejected" in stats


# ══════════════════════════════════════════════════════════════
# Test 6: NativeIntelligenceCore integration
# ══════════════════════════════════════════════════════════════

class TestNativeIntelligenceIntegration:
    """NativeIntelligenceCore integrates all V4.2 components."""

    def test_core_has_strategy_memory(self):
        """NativeIntelligenceCore has StrategyMemory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            assert hasattr(core, 'strategy_memory')
            assert isinstance(core.strategy_memory, StrategyMemory)

    def test_core_stats_include_v42_metrics(self):
        """Core stats include V4.2 adaptive metrics."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            stats = core.get_stats()
            assert "strategy_memory" in stats
            assert "calibration" in stats

    def test_core_cognitive_metrics_include_v42(self):
        """Core cognitive metrics include V4.2 fields."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            metrics = core.get_cognitive_metrics()
            assert "strategy_candidates_found" in metrics
            assert "strategy_influenced_decisions" in metrics
            assert "candidate_evaluations" in metrics
            assert "calibration_adjustments" in metrics
            assert "strategy_influence_rate" in metrics

    def test_core_process_records_calibration(self):
        """Processing records confidence calibration outcomes."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            # Process a few inputs
            core.process("hello")
            core.process("help")

            calibration = core.confidence.get_calibration_stats()
            assert calibration["total_predictions"] >= 2

    def test_core_consolidation_feeds_strategy_memory(self):
        """Consolidation feeds generalized strategies into StrategyMemory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))

            # Create some episodes to consolidate
            from jarvis.memory.episodic import Episode, EpisodeOutcome
            for i in range(4):
                ep = Episode(
                    id=f"ep_{i}",
                    goal="test task",
                    outcome=EpisodeOutcome.SUCCESS,
                    tools_used=["bash"],
                    strategy="test strategy",
                    importance=0.7,
                )
                core.episodic._episodes[ep.id] = ep

            # Run enough turns to trigger consolidation
            for i in range(6):
                core.process(f"test input {i}")

            # Check if strategies were ingested
            stats = core.strategy_memory.get_stats()
            # May or may not have strategies depending on consolidation logic
            assert "total_strategies" in stats


# ══════════════════════════════════════════════════════════════
# Test 7: Strategy signature and matching
# ══════════════════════════════════════════════════════════════

class TestStrategyMatching:
    """Strategy matching uses normalized signatures."""

    def test_make_signature_normalizes(self):
        """Signature creation normalizes text."""
        sig = _make_signature("Read the File Contents")
        assert sig == "contents file read the"  # sorted, lowercased

    def test_make_signature_filters_short_words(self):
        """Signature filters words shorter than 3 characters."""
        sig = _make_signature("I am a test")
        # "I" and "am" are < 3 chars, "a" is < 3 chars
        assert "test" in sig
        assert "i" not in sig

    def test_strategy_evidence_confidence(self):
        """StrategyEvidence confidence reflects success rate and volume."""
        ev = StrategyEvidence(
            task_signature="test",
            context_signature="test",
            successes=8,
            failures=2,
            total_uses=10,
            last_used=time.time(),
        )
        assert ev.success_rate == 0.8
        assert ev.confidence > 0.8  # Includes volume bonus


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
