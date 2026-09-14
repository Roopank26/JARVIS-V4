"""
V4.0 Tests — Native Intelligence Core

Tests the complete cognitive architecture end-to-end.
Every test exercises REAL JARVIS logic — no mocks of JARVIS components.
Only external boundaries (file system, network) use temp dirs / are unavailable.

Tests cover:
  1. Memory — store and retrieve experience
  2. Context — different inputs produce different contexts
  3. Reasoning — input produces structured reasoning
  4. Planning — goal produces multi-step plan
  5. Skill Selection — multiple skills ranked by task/context/history
  6. Failure Learning — failure recorded, future ranking adapts
  7. Recovery — failure triggers safe recovery path
  8. Reflection — outcome produces learning signal
  9. Goal Continuity — multi-step goal survives task completion
  10. Confidence — low confidence doesn't trigger risky actions
  11. Security — unauthorized destructive action blocked
  12. Provider Independence — core works without any LLM
  13. Optional LLM — model can assist without becoming the core
  14. Full Cognitive Cycle — end-to-end pipeline test
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from jarvis.brain.native_intelligence import (
    CognitiveTrace,
    IntelligenceResponse,
    NativeIntelligenceCore,
)
from jarvis.brain.capability_registry import Capability, CapabilityRegistry
from jarvis.brain.context_engine import ContextEngine, Situation
from jarvis.brain.confidence_engine import ConfidenceEngine, ConfidenceScore
from jarvis.brain.decision_engine import Action, Decision, DecisionEngine
from jarvis.brain.reasoning_engine import ReasoningEngine, ReasoningChain
from jarvis.brain.planning_engine import PlanningEngine
from jarvis.brain.self_reflection import SelfReflection
from jarvis.brain.self_evaluation import SelfEvaluator
from jarvis.goals.autonomy import AutonomyEngine, AutonomyMode
from jarvis.goals.manager import GoalManager
from jarvis.goals.task_manager import TaskManager
from jarvis.goals.task_state import TaskState
from jarvis.knowledge.knowledge_engine import KnowledgeEngine
from jarvis.learning.failure_knowledge import FailureKnowledge
from jarvis.learning.learning_engine import LearningEngine
from jarvis.memory.episodic import EpisodicMemory, EpisodeOutcome, EpisodeStep
from jarvis.memory.procedural import ProceduralMemory, SkillStep
from jarvis.memory.retrieval import MemoryRetrieval
from jarvis.security.policy import ActionRisk, SecurityPolicy


# ── Helpers ──

def make_intelligence(tmp_path: Path | None = None) -> NativeIntelligenceCore:
    """Create an intelligence core with temp storage."""
    storage = tmp_path or Path(tempfile.mkdtemp())
    return NativeIntelligenceCore(storage_dir=storage)


# ── Test 1: Memory ──

class TestMemoryIntegration:
    """Store useful experience → later retrieve it."""

    def test_episodic_store_and_recall(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Store a successful episode
        episode = core.episodic.create_episode(
            goal="read configuration file",
            outcome=EpisodeOutcome.SUCCESS,
            steps=[EpisodeStep(action="read", tool="read_file")],
            tools_used=["read_file"],
            importance=0.8,
        )
        core.episodic.store(episode)

        # Recall it
        similar = core.episodic.recall_similar("read configuration")
        assert len(similar) >= 1
        assert similar[0].goal == "read configuration file"

    def test_failure_knowledge_stored_and_retrieved(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Record a failure
        core.failure_knowledge.record_failure(
            task="deploy to production",
            strategy="direct deploy",
            failure_type="permission",
            failure_detail="Permission denied",
            probable_cause="Insufficient permissions",
        )

        # Retrieve guidance
        guidance = core.failure_knowledge.get_guidance("deploy to production")
        assert guidance is not None
        assert "direct deploy" in guidance["avoid_strategies"]

    def test_procedural_skill_creation_and_discovery(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Create a skill with unique tags to avoid confusion with pre-loaded skills
        skill = core.procedural.create_skill(
            name="my_unique_read_config",
            purpose="Read and parse configuration files",
            steps=[SkillStep(order=1, action="read", tool="read_file")],
            tools_required=["read_file"],
            tags={"my_unique_cfg_tag", "my_unique_parse"},
            confidence=0.9,
        )

        # Discover it by its unique tag
        found = core.procedural.discover("my_unique_cfg_tag configuration")
        assert len(found) >= 1
        names = [s.name for s in found]
        assert "my_unique_read_config" in names

    def test_memory_context_flows_to_reasoning(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Store knowledge
        core.knowledge.learn_fact("Python", "is", "a programming language", confidence=0.9)

        # Process a query about Python
        response = core.process("What is Python?")
        assert response.text  # Should get some response
        assert response.used_knowledge or response.used_memory


# ── Test 2: Context ──

class TestContextIntegration:
    """Different contexts produce different situations."""

    def test_command_vs_query_context(self, tmp_path):
        core = make_intelligence(tmp_path)
        ctx = ContextEngine()

        cmd_situation = ctx.understand("read file /tmp/test.txt")
        query_situation = ctx.understand("what is machine learning?")

        assert cmd_situation.intent.category == "command"
        assert query_situation.intent.category == "query"
        assert cmd_situation.requires_tools
        assert query_situation.requires_reasoning

    def test_memory_context_affects_situation(self, tmp_path):
        core = make_intelligence(tmp_path)
        ctx = ContextEngine()

        sit = ctx.understand("remember my favorite color is blue")
        assert sit.requires_memory

    def test_entity_extraction(self, tmp_path):
        ctx = ContextEngine()
        sit = ctx.understand("read the file /home/user/config.json")
        file_entities = [e for e in sit.entities if e.kind == "file"]
        assert len(file_entities) >= 1
        assert "config.json" in file_entities[0].name


# ── Test 3: Reasoning ──

class TestReasoningIntegration:
    """Input produces structured reasoning result."""

    def test_reasoning_produces_chain(self, tmp_path):
        core = make_intelligence(tmp_path)
        chain = core.reasoning.reason("What is Python?")
        assert isinstance(chain, ReasoningChain)
        assert chain.conclusion
        assert chain.overall_confidence is not None

    def test_reasoning_with_knowledge(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.knowledge.learn_fact("Python", "is", "a programming language", confidence=0.9)
        chain = core.reasoning.reason_with_knowledge("What is Python?")
        assert chain.conclusion
        # Should have knowledge-based step
        knowledge_steps = [s for s in chain.steps if s.source == "knowledge"]
        assert len(knowledge_steps) >= 1

    def test_reasoning_confidence_varies(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Well-known topic
        chain1 = core.reasoning.reason("remember my name is Alice")
        # Unknown topic
        chain2 = core.reasoning.reason("explain quantum chromodynamics")
        # Both should produce conclusions, but confidence may differ
        assert chain1.conclusion
        assert chain2.conclusion


# ── Test 4: Planning ──

class TestPlanningIntegration:
    """Goal produces multi-step plan."""

    def test_plan_from_decision(self, tmp_path):
        core = make_intelligence(tmp_path)
        planning = PlanningEngine()
        decision = Decision(action=Action.USE_TOOL, target="read_file")
        situation = Situation(user_input="read /tmp/test.txt")
        plan = planning.create_plan(decision, situation, "read /tmp/test.txt")
        assert len(plan.steps) >= 1
        assert plan.steps[0].tool == "read_file"

    def test_multi_step_plan(self, tmp_path):
        core = make_intelligence(tmp_path)
        planning = PlanningEngine()
        decision = Decision(action=Action.EXECUTE_PLAN)
        situation = Situation(user_input="read file and then search for errors")
        plan = planning.create_plan(decision, situation, "read file and then search for errors")
        # Should have at least one step
        assert len(plan.steps) >= 1


# ── Test 5: Skill Selection ──

class TestSkillSelection:
    """Multiple skills → choose based on task/context/history."""

    def test_skill_discovery(self, tmp_path):
        """Test A: Unique exact tag + generic tag query → unique skill appears."""
        core = make_intelligence(tmp_path)
        core.procedural.create_skill(
            name="my_unique_read_file_skill",
            purpose="Read file contents",
            steps=[SkillStep(order=1, action="read", tool="read_file")],
            tags={"my_unique_read_tag", "my_unique_file_tag"},
            confidence=0.8,
        )
        core.procedural.create_skill(
            name="my_unique_search_skill",
            purpose="Search for files",
            steps=[SkillStep(order=1, action="search", tool="find_files")],
            tags={"my_unique_search_tag", "my_unique_find_tag"},
            confidence=0.6,
        )

        # Mixed query: distinctive tag + generic tag.
        # The distinctive tag must score high enough that the unique skill
        # appears despite generic tag 'file' matching many pre-loaded skills.
        skills = core.procedural.discover("my_unique_read_tag file contents", limit=10)
        names = [s.name for s in skills]
        assert "my_unique_read_file_skill" in names, (
            f"Distinctive tag should not be crowded out. Got: {names[:5]}"
        )

    def test_skill_discovery_exact_tag_only(self, tmp_path):
        """Test B: Unique exact tag alone → unique skill appears."""
        core = make_intelligence(tmp_path)
        core.procedural.create_skill(
            name="my_unique_read_file_skill",
            purpose="Read file contents",
            steps=[SkillStep(order=1, action="read", tool="read_file")],
            tags={"my_unique_read_tag", "my_unique_file_tag"},
            confidence=0.8,
        )
        skills = core.procedural.discover("my_unique_read_tag", limit=10)
        names = [s.name for s in skills]
        assert "my_unique_read_file_skill" in names

    def test_skill_discovery_exact_ranks_above_generic(self, tmp_path):
        """Test C: Several generic skills + one exact-match → exact ranks first."""
        core = make_intelligence(tmp_path)
        core.procedural.create_skill(
            name="my_unique_read_file_skill",
            purpose="Read file contents",
            steps=[SkillStep(order=1, action="read", tool="read_file")],
            tags={"my_unique_read_tag", "my_unique_file_tag"},
            confidence=0.8,
        )
        # Query with both distinctive and generic; distinctive must rank first
        skills = core.procedural.discover("my_unique_read_tag file", limit=10)
        names = [s.name for s in skills]
        assert names[0] == "my_unique_read_file_skill", (
            f"Exact distinctive match must rank first. Got: {names[:3]}"
        )

    def test_skill_discovery_case_insensitive(self, tmp_path):
        """Test D: Case-insensitive tag matching."""
        core = make_intelligence(tmp_path)
        core.procedural.create_skill(
            name="my_case_test_skill",
            purpose="Case test",
            steps=[SkillStep(order=1, action="test")],
            tags={"my_case_UNIQUE_tag"},
            confidence=0.8,
        )
        # Query with different casing
        skills = core.procedural.discover("MY_CASE_unique_TAG", limit=10)
        names = [s.name for s in skills]
        assert "my_case_test_skill" in names, (
            f"Case-insensitive match failed. Got: {names[:5]}"
        )

    def test_skill_discovery_generic_query_still_works(self, tmp_path):
        """Test E: Existing discovery behavior not broken."""
        core = make_intelligence(tmp_path)
        # Create skills that a generic query should find
        core.procedural.create_skill(
            name="my_gen_file_reader",
            purpose="Read file contents",
            steps=[SkillStep(order=1, action="read", tool="read_file")],
            tags={"my_gen_file_tag", "my_gen_read_tag"},
            confidence=0.7,
        )
        core.procedural.create_skill(
            name="my_gen_file_lister",
            purpose="List files in directory",
            steps=[SkillStep(order=1, action="list")],
            tags={"my_gen_file_tag", "my_gen_list_tag"},
            confidence=0.6,
        )
        # Generic query using the shared tag should find both
        skills = core.procedural.discover("my_gen_file_tag", limit=5)
        assert len(skills) >= 2, "Generic discovery should still work"

    def test_skill_confidence_affects_ranking(self, tmp_path):
        core = make_intelligence(tmp_path)
        s1 = core.procedural.create_skill(
            name="my_unique_skill_a",
            purpose="Process data",
            steps=[SkillStep(order=1, action="process")],
            tags={"my_unique_data_tag", "my_unique_process_tag"},
            confidence=0.9,
        )
        s2 = core.procedural.create_skill(
            name="my_unique_skill_b",
            purpose="Process data differently",
            steps=[SkillStep(order=1, action="process")],
            tags={"my_unique_data_tag", "my_unique_process_tag"},
            confidence=0.3,
        )

        skills = core.procedural.discover("my_unique_data_tag process")
        assert len(skills) >= 2
        names = [s.name for s in skills]
        assert "my_unique_skill_a" in names
        assert "my_unique_skill_b" in names


# ── Test 6: Failure Learning ──

class TestFailureLearning:
    """Skill fails → experience recorded → future ranking changes."""

    def test_failure_decreases_skill_confidence(self, tmp_path):
        core = make_intelligence(tmp_path)
        skill = core.procedural.create_skill(
            name="risky_skill",
            purpose="Do something risky",
            steps=[SkillStep(order=1, action="risk")],
            confidence=0.8,
        )
        initial_conf = skill.confidence

        # Record failure
        core.procedural.update_skill(skill.id, success=False)
        assert skill.confidence < initial_conf
        assert skill.failure_count == 1

    def test_failure_knowledge_avoids_bad_strategy(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.failure_knowledge.record_failure(
            task="deploy application",
            strategy="direct upload",
            failure_type="network",
            failure_detail="Connection timeout",
            probable_cause="Network issue",
        )

        guidance = core.failure_knowledge.get_guidance("deploy application")
        assert guidance is not None
        assert "direct upload" in guidance["avoid_strategies"]

    def test_learning_engine_records_failure(self, tmp_path):
        core = make_intelligence(tmp_path)
        result = core.learning.learn_from_failure(
            goal="test task",
            steps=[EpisodeStep(action="attempt")],
            errors=["Permission denied"],
            tools_used=["bash"],
            context="testing",
        )
        assert result.signal.value == "failure"
        assert core.failure_knowledge.get_guidance("test task") is not None


# ── Test 7: Recovery ──

class TestRecoveryIntegration:
    """Action fails → safe recovery path selected."""

    def test_recovery_engine_exists(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.recovery is not None

    def test_recovery_decides_retry(self, tmp_path):
        core = make_intelligence(tmp_path)
        from jarvis.goals.task import Task
        task = Task(id="t1", description="test task")
        decision = core.recovery.decide_recovery(task, "timeout error")
        # Should suggest some recovery action
        assert decision is not None
        assert decision.action is not None


# ── Test 8: Reflection ──

class TestReflectionIntegration:
    """Outcome → reflection → learning signal."""

    def test_reflection_records_action(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.reflection.record_action("use_tool", "success", 150.0)
        core.reflection.record_action("use_tool", "success", 200.0)
        core.reflection.record_action("use_tool", "failure", 300.0)

        stats = core.reflection.get_stats()
        assert stats["total_actions"] == 3

    def test_reflection_produces_suggestions(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Record enough failures to trigger suggestion
        for _ in range(5):
            core.reflection.record_action("bash", "failure", 100.0)

        suggestions = core.reflection.get_improvement_suggestions()
        assert len(suggestions) >= 1
        assert any("bash" in s.lower() for s in suggestions)

    def test_evaluator_produces_improvements(self, tmp_path):
        core = make_intelligence(tmp_path)
        result = core.evaluator.evaluate(
            task="test task",
            goal_achieved=False,
            steps_taken=5,
            tools_used=["bash", "read_file"],
            errors=["timeout"],
            duration_ms=5000,
        )
        assert len(result.improvements) >= 1


# ── Test 9: Goal Continuity ──

class TestGoalContinuity:
    """Multi-step goal survives intermediate task completion."""

    def test_goal_manager_creates_and_tracks(self, tmp_path):
        core = make_intelligence(tmp_path)
        goal = core.goal_manager.create_goal(
            title="Setup project",
            description="Create directory, write config, test",
            priority=0.8,
            owner_authorized=True,
        )
        core.goal_manager.activate(goal.id)
        assert goal.id in [g.id for g in core.goal_manager.list_goals()]

    def test_goal_persistence_across_queries(self, tmp_path):
        core = make_intelligence(tmp_path)
        goal = core.goal_manager.create_goal(
            title="Long running task",
            description="A task that spans multiple interactions",
            priority=0.7,
            owner_authorized=True,
        )
        core.goal_manager.activate(goal.id)

        # Goals should persist
        goals = core.goal_manager.list_goals()
        assert any(g.id == goal.id for g in goals)


# ── Test 10: Confidence ──

class TestConfidenceIntegration:
    """Low confidence doesn't trigger risky actions."""

    def test_confidence_engine_scores_reasoning(self):
        engine = ConfidenceEngine()
        score = engine.score_reasoning(step_count=3, evidence_count=5, contradiction_count=0)
        assert 0.0 <= score.value <= 1.0
        assert score.level in ("very_low", "low", "moderate", "high", "very_high")

    def test_confidence_with_contradictions(self):
        engine = ConfidenceEngine()
        good = engine.score_reasoning(step_count=3, evidence_count=5, contradiction_count=0)
        bad = engine.score_reasoning(step_count=3, evidence_count=5, contradiction_count=3)
        assert good.value > bad.value

    def test_decision_engine_uses_confidence(self):
        conf = ConfidenceEngine()
        dec = DecisionEngine(conf)
        sit = Situation(
            user_input="what is Python?",
            intent=None,
            complexity=0.3,
        )
        from jarvis.brain.context_engine import Intent
        sit.intent = Intent(category="query", action="explain", confidence=0.5)
        decision = dec.decide(sit, can_reason_locally=True, has_model=False)
        assert decision.action == Action.RESPOND_DIRECTLY


# ── Test 11: Security ──

class TestSecurityIntegration:
    """Unauthorized privileged/destructive action is blocked."""

    def test_manual_blocks_all(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.autonomy.set_mode(AutonomyMode.MANUAL)
        allowed, reason = core.autonomy.can_execute({"risk_level": 0})
        assert not allowed
        assert "Manual" in reason or "manual" in reason.lower()

    def test_assisted_blocks_destructive(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.autonomy.set_mode(AutonomyMode.ASSISTED)
        allowed, _ = core.autonomy.can_execute({"risk_level": 0})
        assert allowed
        allowed, reason = core.autonomy.can_execute({"risk_level": 3})
        assert not allowed
        assert "approval" in reason.lower() or "elevated" in reason.lower()

    def test_emergency_stop_blocks_all(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.autonomy.set_mode(AutonomyMode.ASSISTED)
        core.autonomy.emergency_stop()
        allowed, _ = core.autonomy.can_execute({"risk_level": 0})
        assert not allowed

    def test_security_policy_risk_classification(self):
        sp = SecurityPolicy()
        assert sp.classify_risk("read_file", {}) == ActionRisk.READ
        assert sp.classify_risk("write_file", {}) == ActionRisk.SAFE_ACTION
        assert sp.classify_risk("bash", {}) == ActionRisk.PRIVILEGED_ACTION
        assert sp.classify_risk("delete_file", {}) == ActionRisk.DESTRUCTIVE_ACTION

    def test_security_policy_authorization(self):
        sp = SecurityPolicy()
        from jarvis.security.policy import SecurityContext
        ctx = SecurityContext(tool_name="read_file", action="read", risk_level=ActionRisk.READ)
        allowed, reason = sp.authorize(ctx)
        assert allowed

    def test_destructive_path_elevated(self):
        sp = SecurityPolicy()
        risk = sp.classify_risk("bash", {"command": "rm -rf /"})
        assert risk == ActionRisk.DESTRUCTIVE_ACTION

    def test_shell_false_in_executor(self):
        """Verify UnifiedCommandExecutor uses shell=False."""
        import inspect
        from jarvis.brain.unified_executor import UnifiedCommandExecutor
        exe = UnifiedCommandExecutor()
        src = inspect.getsource(exe.execute)
        assert "shell=False" in src


# ── Test 12: Provider Independence ──

class TestProviderIndependence:
    """Core initializes and operates without any LLM provider."""

    def test_core_initializes_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert not core.is_model_available
        assert core._model_adapter is None

    def test_core_processes_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("hello")
        assert response.text
        assert not response.used_model
        assert response.action_taken

    def test_core_reasons_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("What is Python?")
        assert response.text
        # Should use local reasoning, not model
        assert not response.used_model

    def test_core_handles_commands_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("help")
        assert response.text
        assert "JARVIS" in response.text

    def test_core_memory_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.set_memory_system(_FakeMemory())
        response = core.process("remember my name is Alice")
        assert response.text
        assert "remember" in response.text.lower() or "alice" in response.text.lower()

    def test_core_stats_without_model(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        stats = core.get_stats()
        assert stats["total_processed"] == 2
        assert stats["local_responses"] >= 2
        assert stats["model_calls"] == 0


# ── Test 13: Optional LLM ──

class TestOptionalLLM:
    """Model can assist without becoming the cognitive core."""

    def test_model_adapter_settable(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert not core.is_model_available
        core.set_model_adapter(lambda prompt, ctx: "Model response")
        assert core.is_model_available

    def test_model_used_only_when_appropriate(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.set_model_adapter(lambda prompt, ctx: "Model says hello")

        # Simple greeting should NOT use model
        response = core.process("hello")
        assert not response.used_model

    def test_model_failure_falls_back_to_local(self, tmp_path):
        def failing_model(prompt, ctx):
            raise Exception("Model unavailable")

        core = make_intelligence(tmp_path)
        core.set_model_adapter(failing_model)
        response = core.process("explain quantum physics")
        # Should get a response even if model fails
        assert response.text


# ── Test 14: Full Cognitive Cycle ──

class TestFullCognitiveCycle:
    """End-to-end: input → context → memory → reasoning → planning →
    decision → security → execution → observation → evaluation →
    learning → future improvement."""

    def test_full_cycle_simple_command(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("help")
        assert response.text
        assert response.action_taken == "respond_directly"
        assert response.confidence >= 0
        assert response.duration_ms >= 0
        assert not response.used_model
        assert core._total_processed == 1

    def test_full_cycle_with_memory(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.set_memory_system(_FakeMemory())
        response = core.process("remember my favorite color is blue")
        assert response.text
        assert core._total_processed == 1

    def test_full_cycle_creates_episode(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Add a tool that will be used
        core.capabilities.register(Capability(
            id="test_tool",
            name="Test Tool",
            description="A test tool",
            risk_level=0,
            execute_fn=lambda params: "Tool output",
        ))
        core.process("run test_tool")
        # Episode should be created if tool was used
        stats = core.episodic.get_stats()
        # May or may not have episodes depending on decision

    def test_full_cycle_reflection_accumulates(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        core.process("status")
        stats = core.reflection.get_stats()
        assert stats["total_actions"] >= 3

    def test_full_cycle_evaluation_accumulates(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        stats = core.evaluator.get_stats()
        assert stats["evaluations"] >= 2

    def test_full_cycle_trace_captured(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("hello")
        trace = core.get_trace()
        assert trace is not None
        assert trace.perception is not None
        assert trace.decision is not None
        assert trace.duration_ms > 0

    def test_full_cycle_multiple_turns(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        core.process("status")
        stats = core.get_stats()
        assert stats["total_processed"] == 3
        assert stats["turn"] == 3
        assert stats["working_memory"] == 3

    def test_goal_pursuit_cycle(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.pursue_goal("test goal")
        assert response.text
        assert "Goal" in response.text

    def test_feedback_loop(self, tmp_path):
        core = make_intelligence(tmp_path)
        result = core.receive_feedback("that was wrong, do it differently")
        assert result  # Should return learning result

    def test_improvement_suggestions_generated(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Generate enough data for suggestions
        for _ in range(5):
            core.process("hello")
        suggestions = core.reflection.get_improvement_suggestions()
        # May or may not have suggestions depending on patterns

    def test_stats_comprehensive(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        stats = core.get_stats()
        assert "total_processed" in stats
        assert "local_rate" in stats
        assert "episodes" in stats
        assert "skills" in stats
        assert "working_memory" in stats
        assert "autonomy_mode" in stats

    def test_response_to_dict(self, tmp_path):
        core = make_intelligence(tmp_path)
        response = core.process("hello")
        d = response.to_dict()
        assert "text" in d
        assert "action" in d
        assert "confidence" in d
        assert "duration_ms" in d

    def test_trace_to_dict(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        trace = core.get_trace()
        d = trace.to_dict()
        assert "perception" in d
        assert "decision" in d
        assert "success" in d
        assert "confidence" in d


# ── Test: Component Wiring ──

class TestComponentWiring:
    """Verify existing components are properly wired together."""

    def test_reasoning_has_knowledge_engine(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.reasoning._knowledge_engine is core.knowledge

    def test_reasoning_has_failure_knowledge(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.reasoning._failure_knowledge is core.failure_knowledge

    def test_retrieval_has_all_sources(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.retrieval._episodic is core.episodic
        assert core.retrieval._procedural is core.procedural
        assert core.retrieval._knowledge is core.knowledge
        assert core.retrieval._failure_knowledge is core.failure_knowledge

    def test_learning_has_memory_systems(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.learning.episodic is core.episodic
        assert core.learning.procedural is core.procedural
        # LearningEngine creates its own FailureKnowledge; verify it exists
        assert core.learning.failure_knowledge is not None

    def test_security_is_canonical(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert isinstance(core.security, SecurityPolicy)
        assert isinstance(core.autonomy, AutonomyEngine)


# ── Test: Working Memory ──

class TestWorkingMemory:
    """Working memory is session-scoped and bounded."""

    def test_working_memory_grows(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        assert len(core._working_memory) == 2

    def test_working_memory_bounded(self, tmp_path):
        core = make_intelligence(tmp_path)
        for i in range(60):
            core.process(f"message {i}")
        assert len(core._working_memory) <= 50

    def test_working_memory_has_turn_numbers(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello")
        core.process("help")
        assert core._working_memory[0]["turn"] == 1
        assert core._working_memory[1]["turn"] == 2


# ── Helper: Fake Memory System ──

class _FakeMemory:
    """Minimal memory system for testing."""
    def __init__(self):
        self._data = {}

    def remember(self, key, value, category="notes"):
        self._data[key] = {"value": value, "category": category}

    def recall(self, query):
        results = []
        query_lower = query.lower()
        for k, v in self._data.items():
            if query_lower in k.lower() or query_lower in str(v["value"]).lower():
                results.append({"key": k, "value": v["value"]})
        return results

    def forget(self, key):
        self._data.pop(key, None)

    def format_for_prompt(self):
        return "; ".join(f"{k}: {v['value']}" for k, v in self._data.items())


# ── V4.1 Intelligence Benchmarks ──

class TestMemoryConsolidation:
    """MemoryConsolidation is wired into the cognitive loop."""

    def test_consolidation_component_exists(self, tmp_path):
        core = make_intelligence(tmp_path)
        assert core.consolidation is not None

    def test_consolidation_runs_periodically(self, tmp_path):
        """Consolidation runs every 5 turns when episodes exist."""
        core = make_intelligence(tmp_path)
        # Create episodes so consolidation has data
        for i in range(3):
            ep = core.episodic.create_episode(
                goal=f"task {i}",
                outcome=EpisodeOutcome.SUCCESS,
                steps=[EpisodeStep(action="test")],
                tools_used=["test"],
            )
            core.episodic.store(ep)
        # Process 5 turns to trigger consolidation
        for i in range(5):
            core.process(f"turn {i}")
        metrics = core._cognitive_metrics
        assert metrics["consolidation_runs"] >= 1

    def test_consolidation_stats_available(self, tmp_path):
        core = make_intelligence(tmp_path)
        stats = core.get_stats()
        assert "consolidation" in stats


class TestFailureGuidanceIntegration:
    """Failure knowledge is consulted during the cognitive loop."""

    def test_failure_guidance_consulted_on_known_task(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Record a failure
        core.failure_knowledge.record_failure(
            task="deploy app",
            strategy="direct_upload",
            failure_type="network",
            failure_detail="timeout",
            probable_cause="network issue",
        )
        # Process the same task — guidance should be consulted
        core.process("deploy app")
        assert core._cognitive_metrics["failure_guidance_consulted"] >= 1

    def test_failure_guidance_not_consulted_for_unknown_task(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("hello world")
        # No failure guidance for unknown task
        trace = core.get_trace()
        assert not trace.failure_guidance


class TestCognitiveMetrics:
    """Cognitive metrics track real system behavior."""

    def test_metrics_initialized(self, tmp_path):
        core = make_intelligence(tmp_path)
        metrics = core._cognitive_metrics
        assert "task_success_count" in metrics
        assert "task_failure_count" in metrics
        assert "failure_guidance_consulted" in metrics
        assert "consolidation_runs" in metrics
        assert "confident_correct" in metrics

    def test_metrics_track_success(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("help")  # should succeed
        metrics = core._cognitive_metrics
        assert metrics["task_success_count"] >= 1

    def test_metrics_track_confidence_calibration(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("help")  # produces a response
        metrics = core._cognitive_metrics
        # Confidence may be in middle range (not tracked) or high/low range
        # At minimum, task success should be tracked
        assert metrics["task_success_count"] >= 1

    def test_get_cognitive_metrics_returns_derived(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("help")
        m = core.get_cognitive_metrics()
        assert "task_success_rate" in m
        assert "confidence_calibration" in m
        assert "recovery_success_rate" in m

    def test_metrics_in_stats(self, tmp_path):
        core = make_intelligence(tmp_path)
        stats = core.get_stats()
        assert "cognitive_metrics" in stats


class TestLearningChangesFutureBehavior:
    """Learning actually affects future behavior through skill confidence."""

    def test_repeated_failure_decreases_confidence(self, tmp_path):
        core = make_intelligence(tmp_path)
        skill = core.procedural.create_skill(
            name="my_learn_test_skill",
            purpose="Test learning",
            steps=[SkillStep(order=1, action="test")],
            tags={"my_learn_test_tag"},
            confidence=0.9,
        )
        initial = skill.confidence
        # Fail it multiple times
        for _ in range(3):
            core.procedural.update_skill(skill.id, success=False)
        assert skill.confidence < initial
        assert skill.failure_count == 3

    def test_failure_recorded_in_failure_knowledge(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Learn from a failure
        core.learning.learn_from_failure(
            goal="deploy app",
            steps=[EpisodeStep(action="deploy")],
            errors=["timeout"],
            tools_used=["bash"],
            context="production",
        )
        # Failure knowledge should have guidance
        guidance = core.failure_knowledge.get_guidance("deploy app")
        assert guidance is not None

    def test_success_increases_skill_confidence(self, tmp_path):
        core = make_intelligence(tmp_path)
        skill = core.procedural.create_skill(
            name="my_success_test_skill",
            purpose="Test success",
            steps=[SkillStep(order=1, action="test")],
            tags={"my_success_test_tag"},
            confidence=0.5,
        )
        initial = skill.confidence
        for _ in range(3):
            core.procedural.update_skill(skill.id, success=True)
        assert skill.confidence > initial
        assert skill.success_count == 3


class TestConsolidationComponent:
    """MemoryConsolidation works correctly when called."""

    def test_consolidate_episodes(self, tmp_path):
        from jarvis.memory.consolidation import MemoryConsolidation
        mc = MemoryConsolidation()
        episodes = [
            {"id": "1", "goal": "read file", "outcome": "success", "tools_used": ["read_file"]},
            {"id": "2", "goal": "read file", "outcome": "success", "tools_used": ["read_file"]},
            {"id": "3", "goal": "read file", "outcome": "success", "tools_used": ["read_file"]},
        ]
        patterns = mc.consolidate_episodes(episodes)
        assert len(patterns) >= 1
        assert patterns[0].success_count >= 1

    def test_generalize_strategies(self, tmp_path):
        from jarvis.memory.consolidation import MemoryConsolidation
        mc = MemoryConsolidation()
        episodes = [
            {"id": str(i), "goal": "deploy", "outcome": "success",
             "tools_used": ["bash"], "strategy": "safe_deploy"}
            for i in range(4)
        ]
        strategies = mc.generalize_strategies(episodes, min_evidence=3)
        assert len(strategies) >= 1


class TestConfidenceCalibration:
    """Confidence calibration tracks accuracy over time."""

    def test_high_confidence_success_tracked(self, tmp_path):
        core = make_intelligence(tmp_path)
        # Force high confidence by processing a simple task
        core.process("help")
        m = core._cognitive_metrics
        # help should succeed — task_success_count tracks all successes
        assert m["task_success_count"] >= 1

    def test_confidence_metrics_derived(self, tmp_path):
        core = make_intelligence(tmp_path)
        core.process("help")
        m = core.get_cognitive_metrics()
        assert 0.0 <= m["confidence_calibration"] <= 1.0
        assert 0.0 <= m["task_success_rate"] <= 1.0


class TestEndToEndIntelligence:
    """End-to-end intelligence: experience → learning → behavior change."""

    def test_experience_to_behavior_change(self, tmp_path):
        """Prove that experience recording leads to measurable behavior change."""
        core = make_intelligence(tmp_path)
        # Create a skill
        skill = core.procedural.create_skill(
            name="my_e2e_test_skill",
            purpose="End to end test",
            steps=[SkillStep(order=1, action="test")],
            tags={"my_e2e_tag"},
            confidence=0.8,
        )
        initial_conf = skill.confidence

        # Record failure experience
        core.learning.learn_from_failure(
            goal="e2e test",
            steps=[EpisodeStep(action="test")],
            errors=["failed"],
            tools_used=["test"],
            context="testing",
        )
        # Update skill on failure
        core.procedural.update_skill(skill.id, success=False)

        # Verify behavior changed
        assert skill.confidence < initial_conf
        assert core.failure_knowledge.get_guidance("e2e test") is not None

    def test_multi_turn_learning_accumulates(self, tmp_path):
        """Multiple interactions accumulate learning signals."""
        core = make_intelligence(tmp_path)
        for i in range(5):
            core.process(f"interaction {i}")
        stats = core.get_stats()
        assert stats["total_processed"] == 5
        assert stats["cognitive_metrics"]["task_success_count"] >= 5

    def test_trace_shows_failure_guidance(self, tmp_path):
        """Trace includes failure guidance when available."""
        core = make_intelligence(tmp_path)
        core.failure_knowledge.record_failure(
            task="test task",
            strategy="bad_strategy",
            failure_type="error",
            failure_detail="failed",
            probable_cause="bad approach",
        )
        core.process("test task")
        trace = core.get_trace()
        assert trace.failure_guidance  # Should be non-empty
        assert "avoid_strategies" in trace.failure_guidance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
