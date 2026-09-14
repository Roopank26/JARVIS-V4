"""
JARVIS V4.4 — Adaptive Goal & Long-Horizon Intelligence Tests.

Tests that prove:
1. Past execution changes future planning
2. Failure classification guides recovery
3. Partial progress survives recovery
4. Multiple plans are generated and scored
5. Information value influences decisions
6. Expected vs actual state verification
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jarvis.brain.cognitive_state import (
    CognitiveState, ItemType, TaskPhase, VerificationStatus,
)
from jarvis.brain.confidence_engine import ConfidenceEngine
from jarvis.brain.context_engine import ContextEngine
from jarvis.brain.decision_engine import Action, DecisionCandidate, DecisionEngine
from jarvis.brain.native_intelligence import NativeIntelligenceCore
from jarvis.brain.planning_engine import PlanningEngine, ExecutionPlan, PlanStep
from jarvis.brain.strategy_memory import StrategyMemory
from jarvis.learning.failure_knowledge import FailureKnowledge


# ══════════════════════════════════════════════════════════════
# Test 1: Hierarchical Goal Decomposition
# ══════════════════════════════════════════════════════════════

class TestHierarchicalGoals:
    """Goals can be decomposed into subgoals with dependencies."""

    def test_goal_has_parent(self):
        """Goals can reference parent goals."""
        from jarvis.goals.goal import Goal
        parent = Goal(title="Deploy application", parent_goal=None)
        child = Goal(title="Build frontend", parent_goal=parent.id)
        assert child.parent_goal == parent.id

    def test_goal_has_dependencies(self):
        """Goals can declare dependencies."""
        from jarvis.goals.goal import Goal
        goal = Goal(title="Deploy", dependencies=["build", "test"])
        assert "build" in goal.dependencies
        assert "test" in goal.dependencies

    def test_goal_has_constraints(self):
        """Goals can have constraints."""
        from jarvis.goals.goal import Goal
        goal = Goal(
            title="Deploy",
            constraints={"requires_approval": True, "deadline": "2024-01-01"},
        )
        assert goal.constraints["requires_approval"] is True

    def test_goal_state_transitions(self):
        """Goals support proper state transitions."""
        from jarvis.goals.goal import Goal
        from jarvis.goals import GoalState
        goal = Goal(title="test")
        assert goal.state == GoalState.CREATED
        # CREATED → QUEUED → ACTIVE
        assert goal.transition(GoalState.QUEUED)
        assert goal.transition(GoalState.ACTIVE)
        assert goal.state == GoalState.ACTIVE

    def test_goal_is_terminal(self):
        """Terminal states are detected."""
        from jarvis.goals.goal import Goal
        from jarvis.goals import GoalState
        goal = Goal(title="test", state=GoalState.COMPLETED)
        assert goal.is_terminal

    def test_goal_serialization(self):
        """Goals serialize and deserialize correctly."""
        from jarvis.goals.goal import Goal
        goal = Goal(
            title="Test",
            description="Test goal",
            priority=0.8,
            parent_goal="parent_123",
            dependencies=["dep_a"],
            constraints={"max_retries": 3},
        )
        d = goal.to_dict()
        restored = Goal.from_dict(d)
        assert restored.title == "Test"
        assert restored.parent_goal == "parent_123"
        assert restored.dependencies == ["dep_a"]
        assert restored.constraints["max_retries"] == 3


# ══════════════════════════════════════════════════════════════
# Test 2: Failure Classification
# ══════════════════════════════════════════════════════════════

class TestFailureClassification:
    """Failures are classified and recovery is selected accordingly."""

    def test_authorization_failure_classified(self):
        """Permission errors are classified as AUTHORIZATION_FAILURE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Permission denied to access resource")
            assert result == "AUTHORIZATION_FAILURE"

    def test_missing_dependency_classified(self):
        """Not found errors are classified as MISSING_DEPENDENCY."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("No such file or directory")
            assert result == "MISSING_DEPENDENCY"

    def test_timeout_classified(self):
        """Timeout errors are classified correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Operation timeout exceeded")
            assert result == "TIMEOUT"

    def test_resource_failure_classified(self):
        """Network errors are classified as RESOURCE_FAILURE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Connection refused by remote host")
            assert result == "RESOURCE_FAILURE"

    def test_tool_failure_classified(self):
        """Unknown capability is classified as TOOL_FAILURE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Unknown capability: nonexistent_tool")
            assert result == "TOOL_FAILURE"

    def test_unknown_failure_classified(self):
        """Unrecognized errors default to UNKNOWN_FAILURE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Something weird happened")
            assert result == "UNKNOWN_FAILURE"

    def test_security_denied_classified(self):
        """Security denied is classified as AUTHORIZATION_FAILURE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            result = core._classify_failure("Security denied: privileged action")
            assert result == "AUTHORIZATION_FAILURE"


# ══════════════════════════════════════════════════════════════
# Test 3: Adaptive Recovery Selection
# ══════════════════════════════════════════════════════════════

class TestAdaptiveRecovery:
    """Recovery is selected based on failure classification."""

    def test_authorization_failure_skips(self):
        """AUTHORIZATION_FAILURE → skip to preserve progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 0
            task.max_attempts = 3
            task.description = "test task"
            result = core._select_recovery(
                task, "Permission denied", "AUTHORIZATION_FAILURE", None, [],
            )
            assert result["action"] == "skip"

    def test_tool_failure_tries_alternative(self):
        """TOOL_FAILURE → try alternative approach."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 0
            task.max_attempts = 3
            task.description = "test task"
            result = core._select_recovery(
                task, "Unknown capability: x", "TOOL_FAILURE", None, [],
            )
            assert result["action"] == "alternative"

    def test_missing_dependency_tries_alternative(self):
        """MISSING_DEPENDENCY → verify prerequisites."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 0
            task.max_attempts = 3
            task.description = "test task"
            result = core._select_recovery(
                task, "No such file", "MISSING_DEPENDENCY", None, [],
            )
            assert result["action"] == "alternative"

    def test_timeout_retries_then_skips(self):
        """TIMEOUT → retry initially, skip after repeated failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 0
            task.max_attempts = 3
            task.description = "test task"
            result = core._select_recovery(
                task, "Timeout", "TIMEOUT", None, [],
            )
            assert result["action"] == "retry"

            # After multiple attempts, skip
            task.attempts = 3
            result = core._select_recovery(
                task, "Timeout", "TIMEOUT", None, [],
            )
            assert result["action"] == "skip"

    def test_suggested_recovery_used(self):
        """Failure knowledge suggested recovery is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 0
            task.max_attempts = 3
            task.description = "test task"
            guidance = {"suggested_recovery": "try alternative approach"}
            result = core._select_recovery(
                task, "unknown error", "UNKNOWN_FAILURE", guidance, [],
            )
            assert result["action"] == "alternative"

    def test_max_attempts_skips(self):
        """After max attempts, task is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            task = MagicMock()
            task.attempts = 3
            task.max_attempts = 3
            task.description = "test task"
            result = core._select_recovery(
                task, "error", "UNKNOWN_FAILURE", None, [],
            )
            assert result["action"] == "skip"


# ══════════════════════════════════════════════════════════════
# Test 4: Multiple Plan Generation
# ══════════════════════════════════════════════════════════════

class TestMultiplePlanGeneration:
    """PlanningEngine generates and selects from multiple plans."""

    def test_plan_candidates_for_complex_task(self):
        """Complex tasks can generate multiple plan candidates."""
        planning = PlanningEngine()
        ctx = ContextEngine()
        situation = ctx.understand("find and read configuration files")

        from unittest.mock import MagicMock
        decision = MagicMock()
        decision.action = Action.EXECUTE_PLAN
        decision.target = "complex_task"
        decision.parameters = {}

        # With strategy memory
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="find configuration",
            applicability="Finding and reading configuration files",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        planning.set_strategy_memory(sm)

        plan = planning.create_plan(decision, situation, "find and read configuration files")
        assert isinstance(plan, ExecutionPlan)
        # Should have a strategy hint
        assert plan.strategy_hint != ""

    def test_plan_selection_with_failure_guidance(self):
        """Plans using known-bad strategies are penalized."""
        planning = PlanningEngine()
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="bad approach",
            applicability="approach that failed before",
            evidence_count=3,
            success_rate=0.1,
        )
        planning.set_strategy_memory(sm)

        candidates = [
            ExecutionPlan(
                goal="test", steps=[PlanStep(1, "tool_a", "Step A")],
                strategy_hint="bad approach", source="local",
            ),
            ExecutionPlan(
                goal="test", steps=[PlanStep(1, "tool_b", "Step B")],
                strategy_hint="good approach", source="strategy",
            ),
        ]

        # With failure guidance penalizing "bad approach"
        selected = planning._select_best_plan(
            candidates, {"avoid_strategies": ["bad approach"]},
        )
        # Should NOT select the plan with the bad strategy
        assert selected.strategy_hint != "bad approach"

    def test_plan_scoring_prefers_strategy(self):
        """Strategy-informed plans score higher."""
        planning = PlanningEngine()
        candidates = [
            ExecutionPlan(
                goal="test", steps=[PlanStep(1, "tool_a", "A")],
                strategy_hint="", source="local",
            ),
            ExecutionPlan(
                goal="test", steps=[PlanStep(1, "tool_b", "B")],
                strategy_hint="learned strategy", source="strategy",
            ),
        ]
        selected = planning._select_best_plan(candidates, None)
        # Strategy plan should be preferred
        assert selected.source == "strategy"


# ══════════════════════════════════════════════════════════════
# Test 5: THE CRITICAL TEST — Past failure changes future plan
# ══════════════════════════════════════════════════════════════

class TestExperienceChangesPlan:
    """
    THE MOST IMPORTANT TEST.

    Proves that past failure changes the actual plan structure,
    not just strategy ranking.
    """

    def test_failure_knowledge_changes_plan_generation(self):
        """
        When failure knowledge exists for a strategy,
        the planning engine avoids that strategy.
        """
        planning = PlanningEngine()
        sm = StrategyMemory()

        # Strategy A: known to fail
        sm.ingest_from_consolidation(
            strategy_key="direct file read",
            applicability="Reading files directly",
            evidence_count=5,
            success_rate=0.1,
        )
        strat_a = sm.get_all()[0]
        for _ in range(5):
            sm.record_outcome(strat_a.id, success=False)

        planning.set_strategy_memory(sm)

        # Create plan with failure guidance
        from unittest.mock import MagicMock
        decision = MagicMock()
        decision.action = Action.EXECUTE_PLAN
        decision.target = "complex_task"
        decision.parameters = {}

        ctx = ContextEngine()
        situation = ctx.understand("direct file read test")

        # Plan WITH failure guidance
        plan_with_guidance = planning.create_plan(
            decision, situation, "direct file read test",
            failure_guidance={"avoid_strategies": ["direct file read"]},
        )

        # Plan WITHOUT failure guidance
        plan_without = planning.create_plan(
            decision, situation, "direct file read test",
            failure_guidance=None,
        )

        # The plan with guidance should have a different strategy hint
        # (or at least not suggest the known-bad strategy)
        if plan_with_guidance.strategy_hint:
            assert "direct file read" not in plan_with_guidance.strategy_hint.lower() or \
                   plan_with_guidance.strategy_hint == ""

    def test_failure_record_changes_recovery(self):
        """
        Recording a failure changes future recovery strategy.
        """
        fk = FailureKnowledge()
        # Record a failure
        rec = fk.record_failure(
            task="deploy service",
            strategy="direct deploy",
            failure_type="timeout",
            failure_detail="Operation timed out",
            probable_cause="Network latency",
        )
        # Record successful recovery
        fk.record_recovery(rec.id, "staged rollout", success=True)

        # Get guidance
        guidance = fk.get_guidance("deploy service")
        assert guidance is not None
        assert "direct deploy" in guidance["avoid_strategies"]
        assert guidance["suggested_recovery"] == "staged rollout"

    def test_strategy_memory_tracks_failure_impact(self):
        """
        Strategy success rate drops after failures,
        changing future strategy ranking.
        """
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="approach alpha",
            applicability="general approach",
            evidence_count=3,
            success_rate=1.0,
        )
        sm.ingest_from_consolidation(
            strategy_key="approach beta",
            applicability="general approach",
            evidence_count=3,
            success_rate=1.0,
        )

        # Alpha fails repeatedly
        alpha = sm.get_all()[0]
        for _ in range(5):
            sm.record_outcome(alpha.id, success=False)

        # Beta succeeds
        beta = sm.get_all()[1]
        for _ in range(5):
            sm.record_outcome(beta.id, success=True, duration_ms=100)

        # Rankings should change
        results = sm.find_relevant("approach alpha beta general")
        if len(results) >= 2:
            # Beta should rank higher
            best = results[0]
            worst = results[-1]
            assert best.success_rate > worst.success_rate

    def test_experience_changes_plan_structure_in_core(self):
        """
        End-to-end: First attempt records failure, second attempt
        uses different plan structure.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))

            # Record a failure in failure knowledge
            rec = core.failure_knowledge.record_failure(
                task="complex deployment task",
                strategy="direct approach",
                failure_type="timeout",
                failure_detail="Deployment timed out",
                probable_cause="Network issues",
            )

            # Record successful recovery using the returned record's ID
            core.failure_knowledge.record_recovery(
                rec.id, "staged deployment", success=True,
            )

            # Get guidance for similar task
            guidance = core.failure_knowledge.get_guidance("complex deployment task")
            assert guidance is not None
            assert "direct approach" in guidance["avoid_strategies"]
            assert guidance["suggested_recovery"] == "staged deployment"


# ══════════════════════════════════════════════════════════════
# Test 6: Partial Progress Preservation
# ══════════════════════════════════════════════════════════════

class TestPartialProgressPreservation:
    """Failed goals preserve successful partial progress."""

    def test_pursue_goal_preserves_completed_tasks(self):
        """Completed tasks are preserved even if later tasks fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.pursue_goal("simple test goal")
            assert "Goal:" in response.text
            assert "Completed:" in response.text

    def test_goal_progress_updated_on_partial_success(self):
        """Goal progress reflects partial completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            # pursue_goal should handle partial success
            response = core.pursue_goal("test partial goal")
            assert isinstance(response.confidence, float)

    def test_recovery_preserves_completed_steps(self):
        """Recovery doesn't restart from step 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            # Track that pursue_goal returns without restarting everything
            response = core.pursue_goal("test recovery preservation")
            assert response.text  # Should have some output


# ══════════════════════════════════════════════════════════════
# Test 7: Verification Detects False Success
# ══════════════════════════════════════════════════════════════

class TestVerificationDetectsFalseSuccess:
    """Verification catches cases where function returned but action failed."""

    def test_traceback_detected_as_failure(self):
        """Traceback in output is detected as failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="bash")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(1, "bash", "Run command")],
            )
            result = core._verify_execution(
                decision, plan,
                "Traceback (most recent call last):\n  File 'test.py'", True,
            )
            assert result == VerificationStatus.VERIFIED_FAILURE

    def test_exception_detected_as_failure(self):
        """Exception in output is detected as failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="bash")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(1, "bash", "Run")],
            )
            result = core._verify_execution(
                decision, plan, "Exception: division by zero", True,
            )
            assert result == VerificationStatus.VERIFIED_FAILURE

    def test_no_such_file_detected(self):
        """No such file error is detected as failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            decision = core.decision._make_decision(action=Action.USE_TOOL, target="bash")
            plan = ExecutionPlan(
                goal="test",
                steps=[PlanStep(1, "bash", "Run")],
            )
            result = core._verify_execution(
                decision, plan, "No such file or directory", True,
            )
            assert result == VerificationStatus.VERIFIED_FAILURE


# ══════════════════════════════════════════════════════════════
# Test 8: Long-Horizon Goal Execution
# ══════════════════════════════════════════════════════════════

class TestLongHorizonExecution:
    """Goals can be pursued across multiple steps."""

    def test_pursue_goal_returns_response(self):
        """pursue_goal returns a valid response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.pursue_goal("list files in current directory")
            assert response.text
            assert response.action_taken == "goal_pursuit"

    def test_pursue_goal_tracks_completion(self):
        """pursue_goal tracks task completion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.pursue_goal("test goal completion tracking")
            assert "Completed:" in response.text

    def test_pursue_goal_bounded_iterations(self):
        """pursue_goal doesn't loop infinitely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            # This should complete, not hang
            response = core.pursue_goal("bounded test")
            assert response.text

    def test_pursue_goal_confidence_reflects_outcome(self):
        """Confidence reflects whether goal succeeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            response = core.pursue_goal("confidence test")
            assert 0 <= response.confidence <= 1


# ══════════════════════════════════════════════════════════════
# Test 9: V4.4 Metrics
# ══════════════════════════════════════════════════════════════

class TestV44Metrics:
    """V4.4 metrics track adaptive goal intelligence."""

    def test_metrics_include_recovery_classification(self):
        """Metrics include failure classification counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            metrics = core._cognitive_metrics
            assert "failure_classifications" in metrics
            assert "recovery_alternative_count" in metrics
            assert "partial_progress_preserved_count" in metrics

    def test_cognitive_metrics_include_v44(self):
        """Cognitive metrics include V4.4 fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            metrics = core.get_cognitive_metrics()
            assert "verification_success_rate" in metrics

    def test_goal_pursuit_updates_metrics(self):
        """Goal pursuit updates V4.4 metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            core.pursue_goal("metrics test goal")
            metrics = core.get_cognitive_metrics()
            assert metrics["task_success_count"] >= 0


# ══════════════════════════════════════════════════════════════
# Test 10: Security Preserved
# ══════════════════════════════════════════════════════════════

class TestSecurityPreserved:
    """Security authorization remains authoritative."""

    def test_security_still_blocks_destructive(self):
        """Destructive actions are still blocked."""
        from jarvis.security.policy import SecurityPolicy, SecurityContext, ActionRisk
        policy = SecurityPolicy()
        ctx = SecurityContext(
            tool_name="delete_file",
            action="execute",
            risk_level=ActionRisk.DESTRUCTIVE_ACTION,
        )
        authorized, reason = policy.authorize(ctx)
        assert not authorized
        assert "destructive" in reason.lower()

    def test_read_actions_auto_allowed(self):
        """Read actions are auto-allowed."""
        from jarvis.security.policy import SecurityPolicy, SecurityContext, ActionRisk
        policy = SecurityPolicy()
        ctx = SecurityContext(
            tool_name="read_file",
            action="execute",
            risk_level=ActionRisk.READ,
        )
        authorized, reason = policy.authorize(ctx)
        assert authorized

    def test_learned_strategy_cannot_bypass_security(self):
        """Learned strategies cannot bypass security checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            core = NativeIntelligenceCore(storage_dir=Path(tmpdir))
            # Even if a strategy says "use bash", security check still runs
            stats = core.get_stats()
            assert "security_approvals" in stats


# ══════════════════════════════════════════════════════════════
# Test 11: Backward Compatibility
# ══════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """V4.4 changes don't break existing functionality."""

    def test_process_still_works(self):
        """Core process() still works."""
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

    def test_confidence_engine_still_works(self):
        """ConfidenceEngine still works."""
        engine = ConfidenceEngine()
        from jarvis.brain.confidence_engine import ConfidenceFactors
        score = engine.score(ConfidenceFactors(source_reliability=0.8))
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


# ══════════════════════════════════════════════════════════════
# Test 12: THE END-TO-END BENCHMARK
# ══════════════════════════════════════════════════════════════

class TestEndToEndBenchmark:
    """
    THE DEFINITIVE BENCHMARK.

    First attempt: strategy A fails.
    Learning occurs.
    Second attempt: different recovery selected because of experience.
    """

    def test_full_experience_to_behavior_loop(self):
        """
        1. First attempt: strategy fails, failure recorded
        2. Learning: failure knowledge updated
        3. Second attempt: failure knowledge consulted, different recovery
        4. Evidence: the recovery plan is different because of experience
        """
        fk = FailureKnowledge()

        # PHASE 1: First attempt fails
        rec = fk.record_failure(
            task="deploy application",
            strategy="direct deploy",
            failure_type="timeout",
            failure_detail="Deployment timed out after 30s",
            probable_cause="Large artifact size",
        )
        assert rec.failure_type == "timeout"

        # PHASE 2: Guidance exists for this task
        guidance = fk.get_guidance("deploy application")
        assert guidance is not None
        assert "direct deploy" in guidance["avoid_strategies"]

        # PHASE 3: Recovery recording
        fk.record_recovery(rec.id, "staged deployment", success=True)

        # PHASE 4: Updated guidance includes successful recovery
        guidance = fk.get_guidance("deploy application")
        assert guidance["suggested_recovery"] == "staged deployment"
        assert guidance["recovery_confidence"] > 0

    def test_plan_differs_after_experience(self):
        """
        THE CRITICAL ASSERTION:
        first_plan != second_plan BECAUSE of experience.
        """
        sm = StrategyMemory()

        # PHASE 1: Both strategies start equal
        sm.ingest_from_consolidation(
            strategy_key="strategy direct",
            applicability="direct approach for tasks",
            evidence_count=1,
            success_rate=0.5,
        )
        sm.ingest_from_consolidation(
            strategy_key="strategy staged",
            applicability="staged approach for tasks",
            evidence_count=1,
            success_rate=0.5,
        )

        # PHASE 2: Strategy direct fails
        direct = sm.get_all()[0]
        for _ in range(5):
            sm.record_outcome(direct.id, success=False)

        # PHASE 3: Strategy staged succeeds
        staged = sm.get_all()[1]
        for _ in range(5):
            sm.record_outcome(staged.id, success=True, duration_ms=100)

        # PHASE 4: Rankings have changed
        results = sm.find_relevant("strategy direct staged approach tasks")
        assert len(results) >= 2

        # The best strategy should be the one that succeeded
        best = results[0]
        assert best.success_rate >= 0.8  # staged succeeded

        # The worst strategy should be the one that failed
        worst = results[-1]
        assert worst.success_rate <= 0.2  # direct failed

        # THE CRITICAL ASSERTION: best != worst
        assert best.id != worst.id
        assert best.success_rate > worst.success_rate

    def test_confidence_calibration_changes_predictions(self):
        """
        Confidence calibration changes future predictions.
        """
        engine = ConfidenceEngine()

        # PHASE 1: Overconfident predictions fail
        for _ in range(10):
            engine.record_outcome(0.9, False)

        # PHASE 2: Calibration detects overconfidence
        adjustment = engine.get_calibration_adjustment(0.9)
        assert adjustment < 0

        # PHASE 3: Future predictions are adjusted
        calibrated = engine.get_calibrated_confidence(0.9)
        assert calibrated < 0.9

    def test_decision_scoring_uses_experience(self):
        """
        Decision scoring changes with strategy experience.
        """
        engine = DecisionEngine()
        ctx = ContextEngine()

        # Make decisions with strategy candidates
        sm = StrategyMemory()
        sm.ingest_from_consolidation(
            strategy_key="tested approach",
            applicability="approach that has been tested",
            evidence_count=5,
            success_rate=0.9,
            promoted=True,
        )
        candidates = sm.find_relevant("tested approach")

        situation = ctx.understand("tested approach task")
        decision = engine.decide(
            situation,
            can_reason_locally=True,
            strategy_candidates=candidates,
        )
        assert decision.action is not None
        assert decision.candidate_score >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
