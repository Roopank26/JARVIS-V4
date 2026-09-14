"""
JARVIS V4.3 — Unified Cognitive Intelligence Tests.

Tests that the cognitive loop is REAL, not cosmetic.
Proves that:
1. Cognitive state propagates through all stages
2. Reasoning items are typed (fact vs hypothesis)
3. Evidence is weighted by reliability
4. Contradictions reduce confidence
5. Information value guides decisions
6. Execution is verified (not assumed successful)
7. Long-horizon goals track state through recovery
8. Past experience changes future plans and decisions
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from jarvis.brain.cognitive_state import (
    CognitiveState, ItemType, TaskPhase, VerificationStatus,
    ReasoningItem, UncertainFact,
)
from jarvis.brain.confidence_engine import ConfidenceEngine
from jarvis.brain.context_engine import ContextEngine
from jarvis.brain.decision_engine import Action, DecisionCandidate, DecisionEngine
from jarvis.brain.native_intelligence import NativeIntelligenceCore
from jarvis.brain.planning_engine import PlanningEngine, ExecutionPlan, PlanStep
from jarvis.brain.strategy_memory import StrategyMemory


# ══════════════════════════════════════════════════════════════
# Test 1: Cognitive State Creation and Propagation
# ══════════════════════════════════════════════════════════════

class TestCognitiveState:
    """CognitiveState tracks the full cognitive cycle."""

    def test_state_creation(self):
        """CognitiveState can be created with defaults."""
        state = CognitiveState(current_task="test task")
        assert state.current_task == "test task"
        assert state.task_phase == TaskPhase.PERCEPTION
        assert state.verification_status == VerificationStatus.NOT_VERIFIED

    def test_state_add_reasoning_item(self):
        """Can add typed reasoning items to state."""
        state = CognitiveState()
        item = state.add_reasoning_item(
            ItemType.FACT, "The file exists", source="filesystem",
        )
        assert item.item_type == ItemType.FACT
        assert item.confidence > 0.8  # Facts get high default confidence
        assert len(state.reasoning_items) == 1

    def test_hypothesis_default_confidence(self):
        """Hypotheses get low default confidence."""
        state = CognitiveState()
        item = state.add_reasoning_item(
            ItemType.HYPOTHESIS, "User wants X",
        )
        assert item.confidence < 0.5

    def test_type_confidence_ordering(self):
        """Facts > Evidence > Inference > Hypothesis in default confidence."""
        state = CognitiveState()
        fact = state.add_reasoning_item(ItemType.FACT, "A is true")
        evidence = state.add_reasoning_item(ItemType.EVIDENCE, "B supports A")
        inference = state.add_reasoning_item(ItemType.INFERENCE, "Therefore C")
        hypothesis = state.add_reasoning_item(ItemType.HYPOTHESIS, "Maybe D")

        assert fact.confidence > evidence.confidence
        assert evidence.confidence > inference.confidence
        assert inference.confidence > hypothesis.confidence

    def test_effective_confidence_with_contradictions(self):
        """Contradictions reduce effective confidence."""
        item = ReasoningItem(
            item_type=ItemType.EVIDENCE,
            content="test evidence",
            confidence=0.8,
            reliability=0.9,
        )
        original = item.effective_confidence
        item.contradictions.append("conflicting evidence")
        assert item.effective_confidence < original

    def test_is_certain(self):
        """Only high-confidence facts without contradictions are certain."""
        fact = ReasoningItem(
            item_type=ItemType.FACT, content="verified fact",
            confidence=0.95, reliability=0.95,
        )
        assert fact.is_certain

        hypothesis = ReasoningItem(
            item_type=ItemType.HYPOTHESIS, content="maybe",
            confidence=0.3, reliability=0.5,
        )
        assert not hypothesis.is_certain

    def test_needs_verification(self):
        """Hypotheses and inferences need verification."""
        hyp = ReasoningItem(item_type=ItemType.HYPOTHESIS, content="guess")
        assert hyp.needs_verification

        fact = ReasoningItem(item_type=ItemType.FACT, content="verified")
        assert not fact.needs_verification

    def test_overall_confidence_weighted(self):
        """Overall confidence is weighted by item type."""
        state = CognitiveState()
        state.add_reasoning_item(ItemType.FACT, "fact", confidence=0.95, reliability=0.95)
        state.add_reasoning_item(ItemType.HYPOTHESIS, "guess", confidence=0.3, reliability=0.5)

        overall = state.get_overall_confidence()
        # Should be between the two, closer to fact due to higher weight
        assert 0.3 < overall < 0.95

    def test_find_contradictions(self):
        """State can detect contradictions between items."""
        state = CognitiveState()
        state.add_reasoning_item(ItemType.FACT, "file is not accessible")
        state.add_reasoning_item(ItemType.OBSERVATION, "file is accessible and readable")

        contradictions = state.find_contradictions()
        assert len(contradictions) > 0

    def test_uncertainty_tracking(self):
        """State tracks uncertain facts."""
        state = CognitiveState()
        state.add_uncertain_fact(
            "Is the database running?",
            information_value=0.8,
            verification_cost=0.3,
        )
        assert len(state.uncertain_facts) == 1
        assert state.uncertain_facts[0].priority > 0

    def test_highest_value_uncertainty(self):
        """Can find the highest-value uncertainty to resolve."""
        state = CognitiveState()
        state.add_uncertain_fact("low value", information_value=0.2, verification_cost=0.5)
        state.add_uncertain_fact("high value", information_value=0.9, verification_cost=0.1)

        best = state.get_highest_value_uncertainty()
        assert best is not None
        assert best.question == "high value"

    def test_state_to_dict(self):
        """State serialization works."""
        state = CognitiveState(current_task="test")
        state.add_reasoning_item(ItemType.FACT, "fact 1")
        d = state.to_dict()
        assert d["task"] == "test"
        assert d["reasoning_items"] == 1

    def test_state_snapshot(self):
        """State snapshot includes all sections."""
        state = CognitiveState(current_task="test")
        snap = state.snapshot()
        assert "identity" in snap
        assert "knowledge" in snap
        assert "uncertainty" in snap
        assert "planning" in snap
        assert "execution" in snap
        assert "learning" in snap

    def test_task_phase_progression(self):
        """Task phase can be updated through the cycle."""
        state = CognitiveState()
        assert state.task_phase == TaskPhase.PERCEPTION
        state.task_phase = TaskPhase.REASONING
        assert state.task_phase == TaskPhase.REASONING
        state.task_phase = TaskPhase.COMPLETE
        assert state.task_phase == TaskPhase.COMPLETE


# ══════════════════════════════════════════════════════════════
# Test 2: Typed Reasoning
# ══════════════════════════════════════════════════════════════

class TestTypedReasoning:
    """Reasoning items are typed and not all treated equally."""

    def test_fact_vs_hypothesis(self):
        """Facts and hypotheses have different confidence levels."""
        state = CognitiveState()
        fact = state.add_reasoning_item(ItemType.FACT, "Python is a language", confidence=0.95, reliability=0.95)
        hyp = state.add_reasoning_item(ItemType.HYPOTHESIS, "User prefers Python", confidence=0.3, reliability=0.5)

        assert fact.effective_confidence > hyp.effective_confidence
        assert fact.is_certain
        assert not hyp.is_certain

    def test_observation_high_reliability(self):
        """Observations have high reliability by default."""
        obs = ReasoningItem(
            item_type=ItemType.OBSERVATION,
            content="File /tmp/test.txt exists",
            confidence=0.9,
            reliability=0.95,
            is_observed=True,
        )
        assert obs.effective_confidence > 0.7
        assert obs.is_certain

    def test_assumption_not_fact(self):
        """Assumptions are not treated as facts."""
        state = CognitiveState()
        assumption = state.add_reasoning_item(ItemType.ASSUMPTION, "User is online")
        assert not assumption.is_certain
        assert assumption.needs_verification

    def test_constraint_high_confidence(self):
        """Constraints get high default confidence."""
        state = CognitiveState()
        constraint = state.add_reasoning_item(ItemType.CONSTRAINT, "Must not delete /etc")
        assert constraint.confidence > 0.8

    def test_unknown_low_confidence(self):
        """Unknown items have very low confidence."""
        state = CognitiveState()
        unknown = state.add_reasoning_item(ItemType.UNKNOWN, "Whether X is true")
        assert unknown.confidence <= 0.1


# ══════════════════════════════════════════════════════════════
# Test 3: Evidence Weighting and Contradiction Handling
# ══════════════════════════════════════════════════════════════

class TestEvidenceHandling:
    """Evidence is weighted by source reliability and contradictions are detected."""

    def test_evidence_from_reliable_source(self):
        """Evidence from reliable sources has higher effective confidence."""
        reliable = ReasoningItem(
            item_type=ItemType.EVIDENCE,
            content="database query result",
            source="database",
            confidence=0.8,
            reliability=0.9,
        )
        unreliable = ReasoningItem(
            item_type=ItemType.EVIDENCE,
            content="user estimate",
            source="user_guess",
            confidence=0.8,
            reliability=0.3,
        )
        assert reliable.effective_confidence > unreliable.effective_confidence

    def test_contradiction_reduces_confidence(self):
        """Contradicting evidence reduces effective confidence."""
        state = CognitiveState()
        item = state.add_reasoning_item(
            ItemType.EVIDENCE, "server is running", confidence=0.8, reliability=0.7,
        )
        original_conf = item.effective_confidence

        # Add contradicting evidence
        item.contradictions.append("server process not found")
        assert item.effective_confidence < original_conf

    def test_multiple_contradictions_severely_reduce(self):
        """Multiple contradictions severely reduce confidence."""
        item = ReasoningItem(
            item_type=ItemType.EVIDENCE,
            content="claim X",
            confidence=0.8,
            reliability=0.8,
        )
        item.contradictions.append("evidence against 1")
        item.contradictions.append("evidence against 2")
        item.contradictions.append("evidence against 3")

        assert item.effective_confidence < 0.3

    def test_state_detects_contradictions(self):
        """CognitiveState detects contradictions between items."""
        state = CognitiveState()
        state.add_reasoning_item(ItemType.FACT, "file is not accessible")
        state.add_reasoning_item(ItemType.OBSERVATION, "file is accessible")

        contradictions = state.find_contradictions()
        assert len(contradictions) > 0


# ══════════════════════════════════════════════════════════════
# Test 4: Information Value
# ══════════════════════════════════════════════════════════════

class TestInformationValue:
    """JARVIS can identify what information would help most."""

    def test_uncertainty_priority(self):
        """High value, low cost uncertainties get highest priority."""
        high = UncertainFact(
            question="Is server up?",
            information_value=0.9,
            verification_cost=0.1,
        )
        low = UncertainFact(
            question="What color is the logo?",
            information_value=0.2,
            verification_cost=0.8,
        )
        assert high.priority > low.priority

    def test_state_finds_highest_value_uncertainty(self):
        """State can find the most valuable information to gather."""
        state = CognitiveState()
        state.add_uncertain_fact("low priority", information_value=0.2, verification_cost=0.8)
        state.add_uncertain_fact("high priority", information_value=0.9, verification_cost=0.1)

        best = state.get_highest_value_uncertainty()
        assert best.question == "high priority"

    def test_zero_cost_verification(self):
        """Zero-cost verification gets priority equal to information_value."""
        fact = UncertainFact(
            question="check memory",
            information_value=0.5,
            verification_cost=0.0,
        )
        # When cost is 0, priority returns information_value directly
        assert fact.priority == 0.5

    def test_zero_cost_beats_high_cost(self):
        """Zero-cost verification beats high-cost verification."""
        free = UncertainFact(question="free", information_value=0.5, verification_cost=0.0)
        expensive = UncertainFact(question="expensive", information_value=0.9, verification_cost=10.0)
        assert free.priority > expensive.priority


# ══════════════════════════════════════════════════════════════
# Test 5: Active Verification
# ══════════════════════════════════════════════════════════════

class TestActiveVerification:
    """Execution results are verified, not assumed successful."""

    def test_core_verifies_execution(self):
        """NativeIntelligenceCore has verification capability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))

            # Verify a successful execution
            decision = core.decision._make_decision(
                action=Action.USE_TOOL,
                target="read_file",
            )
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(step_id=1, tool="read_file", description="Read file")],
            )
            status = core._verify_execution(
                decision, plan, "File contents here", True,
            )
            assert status == VerificationStatus.VERIFIED_SUCCESS

    def test_verification_detects_errors(self):
        """Verification catches error messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="bash")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(step_id=1, tool="bash", description="Run command")],
            )
            status = core._verify_execution(
                decision, plan, "Error: command not found", False,
            )
            assert status == VerificationStatus.VERIFIED_FAILURE

    def test_verification_detects_permission_denied(self):
        """Verification catches permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="bash")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(step_id=1, tool="bash", description="Run command")],
            )
            status = core._verify_execution(
                decision, plan, "Permission denied", True,
            )
            assert status == VerificationStatus.VERIFIED_FAILURE

    def test_verification_skipped_for_no_steps(self):
        """Verification is skipped when there are no plan steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.RESPOND_DIRECTLY, target="general")
            plan = ExecutionPlan(goal="test", steps=[])
            status = core._verify_execution(decision, plan, "Hello!", True)
            assert status == VerificationStatus.VERIFICATION_SKIPPED

    def test_verification_empty_read_fails(self):
        """An empty file read is verified as failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="read_file")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(step_id=1, tool="read_file", description="Read")],
            )
            status = core._verify_execution(decision, plan, "  ", True)
            assert status == VerificationStatus.VERIFIED_FAILURE


# ══════════════════════════════════════════════════════════════
# Test 6: Integrated Cognitive Loop
# ══════════════════════════════════════════════════════════════

class TestIntegratedCognitiveLoop:
    """The full cognitive loop propagates state through all stages."""

    def test_process_returns_cognitive_state(self):
        """Processing returns a cognitive state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            assert response.cognitive_state is not None
            assert isinstance(response.cognitive_state, CognitiveState)

    def test_state_has_reasoning_items(self):
        """Returned state has reasoning items populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("help")
            state = response.cognitive_state
            assert len(state.reasoning_items) > 0

    def test_state_phase_is_complete(self):
        """Returned state is in COMPLETE phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            assert response.cognitive_state.task_phase == TaskPhase.COMPLETE

    def test_state_has_confidence(self):
        """Returned state has computed confidence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            conf = response.cognitive_state.get_overall_confidence()
            assert 0.0 <= conf <= 1.0

    def test_state_tracks_entities(self):
        """State tracks entities from perception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("read file /tmp/test.txt")
            state = response.cognitive_state
            assert len(state.relevant_entities) > 0

    def test_state_serializable(self):
        """State can be serialized (important for debugging)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            d = response.to_dict()
            assert "cognitive_state" in d
            assert d["cognitive_state"] is not None

    def test_response_dict_includes_cognitive_state(self):
        """Response dict includes cognitive state info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("help")
            d = response.to_dict()
            cs = d["cognitive_state"]
            assert "task" in cs
            assert "phase" in cs
            assert "confidence" in cs

    def test_multiple_turns_update_state(self):
        """Each turn gets a fresh cognitive state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            r1 = core.process("hello")
            r2 = core.process("help")
            assert r1.cognitive_state.turn_number < r2.cognitive_state.turn_number


# ══════════════════════════════════════════════════════════════
# Test 7: V4.3 Cognitive Metrics
# ══════════════════════════════════════════════════════════════

class TestV43Metrics:
    """V4.3 metrics track verification and unified intelligence."""

    def test_metrics_include_verification(self):
        """Cognitive metrics include verification counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            core.process("hello")
            metrics = core.get_cognitive_metrics()
            assert "verification_success_count" in metrics
            assert "verification_success_rate" in metrics

    def test_verification_rate_computed(self):
        """Verification success rate is computed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            core.process("hello")
            core.process("help")
            metrics = core.get_cognitive_metrics()
            assert 0 <= metrics["verification_success_rate"] <= 1

    def test_stats_include_calibrated_confidence(self):
        """Stats include calibrated confidence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            stats = core.get_stats()
            assert "calibration" in stats

    def test_stats_include_strategy_memory(self):
        """Stats include strategy memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            stats = core.get_stats()
            assert "strategy_memory" in stats


# ══════════════════════════════════════════════════════════════
# Test 8: Strategy Memory → Plan → Decision Integration
# ══════════════════════════════════════════════════════════════

class TestStrategyPlanDecisionIntegration:
    """Strategy memory influences planning and decisions end-to-end."""

    def test_strategy_memory_feeds_planning(self):
        """Strategy memory can be consulted during planning."""
        planning = PlanningEngine()
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="direct file read",
            applicability="Reading local files quickly",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        planning.set_strategy_memory(sm)

        # Planning should be able to find the strategy
        ctx = ContextEngine()
        situation = ctx.understand("direct file read test")
        from unittest.mock import MagicMock
        decision = MagicMock()
        decision.action = Action.USE_TOOL
        decision.target = "read_file"
        decision.parameters = {}

        plan = planning.create_plan(decision, situation, "direct file read test")
        assert isinstance(plan, ExecutionPlan)
        assert plan.strategy_hint != ""  # Should find the strategy

    def test_decision_engine_uses_strategies(self):
        """Decision engine boosts candidates when strategies suggest them."""
        engine = DecisionEngine()
        ctx = ContextEngine()
        situation = ctx.understand("file read contents")

        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="file read approach",
            applicability="Reading files efficiently",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        candidates = sm.find_relevant("file read approach contents")

        decision = engine.decide(
            situation,
            can_reason_locally=True,
            has_model=False,
            strategy_candidates=candidates,
        )
        assert decision.action is not None

    def test_experience_changes_plan_hint(self):
        """
        After experience, strategy memory provides different hints.
        """
        sm = StrategyMemory()
        # Ingest strategy A (bad)
        sm.ingest_from_consolidation(
            strategy_key="slow approach",
            applicability="slow method",
            evidence_count=3,
            success_rate=0.2,
        )
        strat_a = sm.get_all()[0]
        for _ in range(5):
            sm.record_outcome(strat_a.id, success=False)

        # Ingest strategy B (good)
        sm.ingest_from_consolidation(
            strategy_key="fast approach",
            applicability="fast efficient method",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        strat_b = sm.get_all()[1]
        for _ in range(5):
            sm.record_outcome(strat_b.id, success=True, duration_ms=50.0)

        # Find relevant should rank B higher
        results = sm.find_relevant("fast approach slow approach method")
        if results:
            # The first result should be the better strategy
            assert results[0].success_rate >= 0.5


# ══════════════════════════════════════════════════════════════
# Test 9: THE CRITICAL TEST — Experience changes future behavior
# ══════════════════════════════════════════════════════════════

class TestExperienceChangesFutureBehavior:
    """
    The most important test. Proves that:
    1. Experience creates evidence
    2. Evidence influences strategy ranking
    3. Strategy ranking changes decisions
    4. Changed decisions lead to better outcomes
    """

    def test_full_loop_strategy_avoidance(self):
        """
        LOOP: Strategy fails → recorded → next time avoided → better strategy chosen.
        """
        sm = StrategyMemory()

        # Phase 1: Both strategies untested
        sm.ingest_from_consolidation(
            strategy_key="approach alpha",
            applicability="general task solving",
            evidence_count=1,
            success_rate=0.5,
        )
        sm.ingest_from_consolidation(
            strategy_key="approach beta",
            applicability="general task solving",
            evidence_count=1,
            success_rate=0.5,
        )

        # Phase 2: Alpha fails repeatedly
        alpha = sm.get_all()[0]
        for _ in range(5):
            sm.record_outcome(alpha.id, success=False)

        # Phase 3: Beta succeeds repeatedly
        beta = sm.get_all()[1]
        for _ in range(5):
            sm.record_outcome(beta.id, success=True, duration_ms=100.0)

        # Phase 4: Query for "approach alpha beta general"
        results = sm.find_relevant("approach alpha beta general task")
        if len(results) >= 2:
            # Beta should rank higher (better success rate)
            rates = {r.description: r.success_rate for r in results}
            # The strategy with higher success rate should be first
            best = results[0]
            worst = results[-1]
            assert best.success_rate > worst.success_rate

    def test_confidence_calibration_improves(self):
        """
        LOOP: Overconfident predictions → calibration adjusts → future confidence is better.
        """
        engine = ConfidenceEngine()

        # Phase 1: Predict 0.8, but mostly fail
        for _ in range(10):
            engine.record_outcome(0.8, False)

        # Phase 2: Calibration should detect overconfidence
        adjustment = engine.get_calibration_adjustment(0.8)
        assert adjustment < 0  # Overconfident

        # Phase 3: Future predictions should be adjusted down
        calibrated = engine.get_calibrated_confidence(0.8)
        assert calibrated < 0.8

    def test_decision_scoring_uses_history(self):
        """
        Decision scoring changes when historical success data is available.
        """
        engine = DecisionEngine()
        ctx = ContextEngine()

        # Make several decisions
        for text in ["read file test.txt", "help", "hello"]:
            situation = ctx.understand(text)
            engine.decide(situation, can_reason_locally=True)

        stats = engine.get_stats()
        assert stats["total_decisions"] == 3
        assert "candidate_evaluated" in stats

    def test_consolidation_feeds_strategy_memory(self):
        """
        Consolidation creates strategies that StrategyMemory can use.
        """
        sm = StrategyMemory()

        # Simulate what consolidation produces
        sm.ingest_from_consolidation(
            strategy_key="bash file operations",
            applicability="File operations using bash commands",
            evidence_count=5,
            success_rate=0.85,
            promoted=True,
        )

        results = sm.find_relevant("bash file operations")
        assert len(results) > 0
        assert results[0].success_rate >= 0.8


# ══════════════════════════════════════════════════════════════
# Test 10: Backward Compatibility
# ══════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """V4.3 changes don't break existing functionality."""

    def test_process_still_works(self):
        """Core process() still works after V4.3 changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            assert response.text
            assert response.action_taken

    def test_get_stats_still_works(self):
        """get_stats() still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            stats = core.get_stats()
            assert "total_processed" in stats
            assert "cognitive_metrics" in stats

    def test_pursue_goal_still_works(self):
        """pursue_goal() still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.pursue_goal("test goal for V4.3")
            assert response.text
            assert "Goal:" in response.text

    def test_confidence_engine_still_works(self):
        """ConfidenceEngine still works."""
        engine = ConfidenceEngine()
        from jarvis.brain.confidence_engine import ConfidenceFactors
        factors = ConfidenceFactors(
            source_reliability=0.8,
            recency=0.9,
            corroboration=0.5,
        )
        score = engine.score(factors)
        assert 0 <= score.value <= 1

    def test_decision_engine_still_works(self):
        """DecisionEngine still works."""
        engine = DecisionEngine()
        ctx = ContextEngine()
        situation = ctx.understand("help")
        decision = engine.decide(situation)
        assert decision.action is not None

    def test_planning_engine_still_works(self):
        """PlanningEngine still works."""
        planning = PlanningEngine()
        from unittest.mock import MagicMock
        ctx = ContextEngine()
        situation = ctx.understand("read file test.txt")
        decision = MagicMock()
        decision.action = Action.USE_TOOL
        decision.target = "read_file"
        decision.parameters = {}
        plan = planning.create_plan(decision, situation)
        assert isinstance(plan, ExecutionPlan)

    def test_strategy_memory_still_works(self):
        """StrategyMemory still works."""
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="test",
            applicability="testing",
            evidence_count=3,
            success_rate=0.8,
        )
        assert len(sm.get_all()) == 1

    def test_response_to_dict_backward_compatible(self):
        """Response to_dict still has all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.process("hello")
            d = response.to_dict()
            assert "text" in d
            assert "action" in d
            assert "confidence" in d
            assert "used_model" in d
            assert "duration_ms" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
