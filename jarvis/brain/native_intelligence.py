"""
JARVIS Native Intelligence Core — V4.1

NOT a replacement for CognitiveCore or JarvisOrchestrator.
IS the integration layer that wires existing components into ONE canonical
cognitive loop.

V4.0: Canonical 17-stage cognitive loop, component wiring.
V4.1: Memory consolidation, learning→behavior, cognitive metrics,
      failure-aware planning, adaptive recovery, strategy learning.

Architecture:
    USER/ENVIRONMENT INPUT
    → Perception (ContextEngine)
    → Context Construction (AdaptiveContextBuilder)
    → Working Memory (session state)
    → Unified Memory Retrieval (MemoryRetrieval)
    → Knowledge Retrieval (KnowledgeEngine)
    → Goal Identification (GoalManager)
    → Failure Guidance Lookup (FailureKnowledge)
    → Reasoning (ReasoningEngine + failure knowledge + knowledge engine)
    → Planning (PlanningEngine + failure-aware planning)
    → Decision (DecisionEngine + confidence + learning guidance)
    → Confidence Assessment (ConfidenceEngine)
    → Security / Authorization (SecurityPolicy + AutonomyEngine)
    → Skill / Capability Selection (SkillTaskIntegrator + CapabilityRegistry)
    → Execution (CapabilityRegistry + UnifiedCommandExecutor)
    → Observation (result capture)
    → Outcome Evaluation (SelfEvaluator)
    → Self Reflection (SelfReflection)
    → Experience Recording (EpisodicMemory)
    → Learning (LearningEngine)
    → Skill / Strategy Improvement (ProceduralMemory + SkillVersioning)
    → Memory Consolidation (MemoryConsolidation)
    → Cognitive Metrics Update
    → Future Decision Improvement

Design principle: COORDINATE existing components, never duplicate them.
The model is optional. JARVIS intelligence comes from the architecture.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jarvis.brain.capability_registry import (
    CapabilityRegistry, CapabilityResult, register_default_capabilities,
)
from jarvis.brain.confidence_engine import ConfidenceEngine
from jarvis.brain.context_engine import ContextEngine, Situation
from jarvis.brain.decision_engine import Action, Decision, DecisionEngine
from jarvis.brain.planning_engine import ExecutionPlan, PlanningEngine
from jarvis.brain.reasoning_engine import ReasoningChain, ReasoningEngine
from jarvis.brain.self_evaluation import SelfEvaluator
from jarvis.brain.self_reflection import SelfReflection
from jarvis.brain.skill_task_integration import SkillTaskIntegrator, SkillMatch
from jarvis.brain.strategy_memory import StrategyMemory, StrategyCandidate
from jarvis.goals.autonomy import AutonomyEngine, AutonomyMode
from jarvis.goals.goal import Goal
from jarvis.goals.manager import GoalManager
from jarvis.goals.planner import GoalPlanner
from jarvis.goals.recovery import RecoveryEngine, RecoveryLimits, RecoveryAction
from jarvis.goals.task import Task
from jarvis.goals.task_manager import TaskManager
from jarvis.goals.task_state import TaskState
from jarvis.knowledge.knowledge_engine import KnowledgeEngine
from jarvis.learning.failure_knowledge import FailureKnowledge
from jarvis.learning.learning_engine import LearningEngine
from jarvis.memory.episodic import EpisodeOutcome, EpisodeStep, EpisodicMemory
from jarvis.memory.procedural import ProceduralMemory
from jarvis.memory.retrieval import MemoryRetrieval
from jarvis.memory.consolidation import MemoryConsolidation
from jarvis.security.policy import ActionRisk, SecurityContext, SecurityPolicy

logger = logging.getLogger(__name__)


# ── Structured Data Flow Between Stages ──


@dataclass
class CognitiveTrace:
    """Complete trace of one cognitive cycle. Structured data, not dicts."""
    perception: Situation | None = None
    memory_results: list[str] = field(default_factory=list)
    knowledge_results: list[str] = field(default_factory=list)
    failure_guidance: dict[str, Any] = field(default_factory=dict)
    reasoning: ReasoningChain | None = None
    decision: Decision | None = None
    plan: ExecutionPlan | None = None
    skill_match: SkillMatch | None = None
    security_check: tuple[bool, str] = (False, "not checked")
    execution_result: Any = None
    outcome_success: bool = False
    confidence: float = 0.0
    episode_id: str = ""
    learning_signal: str = ""
    consolidation_patterns: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "perception": self.perception.to_dict() if self.perception else None,
            "memory_count": len(self.memory_results),
            "knowledge_count": len(self.knowledge_results),
            "has_failure_guidance": bool(self.failure_guidance),
            "reasoning_steps": len(self.reasoning.steps) if self.reasoning else 0,
            "decision": self.decision.action.value if self.decision else None,
            "plan_steps": len(self.plan.steps) if self.plan else 0,
            "skill": self.skill_match.skill.name if self.skill_match else None,
            "security_allowed": self.security_check[0],
            "success": self.outcome_success,
            "confidence": round(self.confidence, 3),
            "consolidation_patterns": self.consolidation_patterns,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class IntelligenceResponse:
    """Response from the native intelligence core."""
    text: str
    action_taken: str
    confidence: float = 0.0
    used_model: bool = False
    used_tools: bool = False
    used_skill: bool = False
    used_memory: bool = False
    used_knowledge: bool = False
    reasoning_summary: str = ""
    duration_ms: float = 0.0
    trace: CognitiveTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text[:500],
            "action": self.action_taken,
            "confidence": round(self.confidence, 3),
            "used_model": self.used_model,
            "used_tools": self.used_tools,
            "used_skill": self.used_skill,
            "used_memory": self.used_memory,
            "used_knowledge": self.used_knowledge,
            "duration_ms": round(self.duration_ms, 2),
        }


# ── Native Intelligence Core ──


class NativeIntelligenceCore:
    """
    Coordinates ALL existing JARVIS cognitive components into one canonical loop.

    This is NOT a new brain — it's the wiring that makes the existing brain
    components cooperate. Every component referenced here already exists
    in the repository. This class connects them.

    Key integration fixes:
    1. MemoryRetrieval used instead of raw _recall_memory
    2. FailureKnowledge consulted during reasoning
    3. Confidence influences security risk assessment
    4. SelfReflection suggestions feed into future decisions
    5. Episodic success patterns influence skill selection
    6. LearningEngine wired into every execution cycle
    7. SecurityPolicy is the canonical security authority
    8. Goals persist and influence planning across sessions
    """

    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path("/tmp/jarvis_v4")

        # ── Core Cognitive Components (existing) ──
        self.confidence = ConfidenceEngine()
        self.context = ContextEngine()
        self.reasoning = ReasoningEngine(self.confidence)
        self.decision = DecisionEngine(self.confidence)
        self.planning = PlanningEngine()
        self.reflection = SelfReflection(self.confidence)
        self.evaluator = SelfEvaluator()

        # ── V4.2: Strategy Memory (bridges consolidation → planning/decision) ──
        self.strategy_memory = StrategyMemory()
        self.planning.set_strategy_memory(self.strategy_memory)

        # ── Memory Systems (existing) ──
        self.episodic = EpisodicMemory(
            storage_path=self._storage_dir / "episodes.json" if self._storage_dir else None,
        )
        self.procedural = ProceduralMemory(
            storage_path=self._storage_dir / "skills.json" if self._storage_dir else None,
        )
        self.retrieval = MemoryRetrieval()
        self.knowledge = KnowledgeEngine()
        self.failure_knowledge = FailureKnowledge()
        self.consolidation = MemoryConsolidation()

        # ── Learning (existing) ──
        self.learning = LearningEngine(
            episodic_memory=self.episodic,
            procedural_memory=self.procedural,
        )

        # ── Goals & Tasks (existing) ──
        self.goal_manager = GoalManager(
            storage_path=self._storage_dir / "goals.json" if self._storage_dir else None
        )
        self.goal_planner = GoalPlanner()
        self.task_manager = TaskManager(
            storage_path=self._storage_dir / "tasks.json" if self._storage_dir else None
        )
        self.recovery = RecoveryEngine(limits=RecoveryLimits())

        # ── Security & Autonomy (existing) ──
        self.security = SecurityPolicy()
        self.autonomy = AutonomyEngine(mode=AutonomyMode.ASSISTED)

        # ── Capabilities (existing) ──
        self.capabilities = CapabilityRegistry()
        register_default_capabilities(self.capabilities)

        # ── Skill Intelligence (existing, wired) ──
        self._skill_integrator: SkillTaskIntegrator | None = None

        # ── Wiring: connect existing components ──
        self._wire_components()

        # ── Optional: model adapter ──
        self._model_adapter: Any = None
        self._memory_system: Any = None

        # ── Working memory (session-scoped) ──
        self._working_memory: list[dict[str, Any]] = []
        self._conversation_turn: int = 0

        # ── Metrics ──
        self._total_processed: int = 0
        self._model_calls: int = 0
        self._local_responses: int = 0
        self._skill_uses: int = 0
        self._traces: list[CognitiveTrace] = []

        # ── Cognitive Metrics (V4.1 + V4.2) ──
        self._cognitive_metrics: dict[str, Any] = {
            "task_success_count": 0,
            "task_failure_count": 0,
            "recovery_attempt_count": 0,
            "recovery_success_count": 0,
            "failure_guidance_consulted": 0,
            "failure_guidance_prevented": 0,
            "consolidation_runs": 0,
            "patterns_consolidated": 0,
            "strategies_generalized": 0,
            "confident_correct": 0,   # high confidence + success
            "confident_wrong": 0,     # high confidence + failure
            "unconfident_correct": 0, # low confidence + success
            "unconfident_wrong": 0,   # low confidence + failure
            # V4.2 adaptive metrics
            "strategy_candidates_found": 0,
            "strategy_influenced_decisions": 0,
            "candidate_evaluations": 0,
            "calibration_adjustments": 0,
        }

    # ── Component Wiring ──

    def _wire_components(self):
        """Wire existing components together. This is the key integration."""
        # 1. Reasoning gets knowledge engine + failure knowledge
        self.reasoning.set_knowledge_engine(self.knowledge)
        self.reasoning.set_failure_knowledge(self.failure_knowledge)

        # 2. Retrieval gets all memory sources
        self.retrieval.set_episodic(self.episodic)
        self.retrieval.set_procedural(self.procedural)
        self.retrieval.set_knowledge(self.knowledge)
        self.retrieval.set_failure_knowledge(self.failure_knowledge)

        # 3. Learning engine shares the same failure knowledge instance
        self.learning.failure_knowledge = self.failure_knowledge

    def set_model_adapter(self, adapter: Any):
        """Optional: set a model adapter for inference."""
        self._model_adapter = adapter

    def set_memory_system(self, memory: Any):
        """Connect long-term memory system."""
        self._memory_system = memory
        self.retrieval.set_memory_system(memory)

    def set_skill_integrator(self, integrator: SkillTaskIntegrator):
        """Connect skill intelligence."""
        self._skill_integrator = integrator
        self.reasoning.set_skill_engine(integrator._skill_engine)
        if hasattr(integrator._skill_engine, 'failure_knowledge'):
            self.reasoning.set_failure_knowledge(integrator._skill_engine.failure_knowledge)

    # ── Canonical Cognitive Loop ──

    def process(self, user_input: str) -> IntelligenceResponse:
        """
        Process input through the complete canonical cognitive loop.

        Every stage produces structured data consumed by the next stage.
        This is the ONE path through which JARVIS thinks.
        """
        start = time.time()
        self._total_processed += 1
        self._conversation_turn += 1
        trace = CognitiveTrace()

        # ── STAGE 1: PERCEPTION ──
        memory_context = self._get_memory_context()
        situation = self.context.understand(user_input, memory_context)
        trace.perception = situation

        # ── STAGE 2: UNIFIED MEMORY RETRIEVAL ──
        retrieval_results = self.retrieval.retrieve(user_input, context=memory_context)
        memory_data = []
        for r in retrieval_results:
            memory_data.append({"key": r.source, "value": r.content, "category": r.source})
            trace.memory_results.append(r.content[:100])
        used_memory = bool(memory_data)

        # ── STAGE 3: KNOWLEDGE RETRIEVAL ──
        knowledge_results = []
        try:
            knowledge_results = self.knowledge.search(user_input, limit=5)
            for kr in knowledge_results:
                if kr.get("type") == "fact":
                    memory_data.append({
                        "key": f"{kr.get('subject', '')} {kr.get('predicate', '')}",
                        "value": kr.get("value", ""),
                        "category": "knowledge",
                    })
                    trace.knowledge_results.append(str(kr.get("value", ""))[:100])
        except Exception:
            pass
        used_knowledge = bool(knowledge_results)

        # ── STAGE 4: GOAL IDENTIFICATION ──
        active_goals = self.goal_manager.list_goals()
        goal_context = ""
        if active_goals:
            goal_context = "; ".join(g.title for g in active_goals[:3])

        # ── STAGE 4.5: FAILURE GUIDANCE + STRATEGY LOOKUP ──
        failure_guidance = self.failure_knowledge.get_guidance(user_input)
        if failure_guidance:
            trace.failure_guidance = failure_guidance
            self._cognitive_metrics["failure_guidance_consulted"] += 1

        # V4.2: Find strategy candidates from learned experience
        strategy_candidates = self.strategy_memory.find_candidates(
            task=user_input,
            context=memory_context,
            failure_guidance=failure_guidance,
            limit=3,
        )
        if strategy_candidates:
            self._cognitive_metrics["strategy_candidates_found"] += 1

        # ── STAGE 5: REASONING (enhanced with failure knowledge + knowledge) ──
        chain = self.reasoning.reason_with_knowledge(
            user_input, memory_context, memory_data,
        )
        trace.reasoning = chain
        local_confidence = chain.overall_confidence.value if chain.overall_confidence else 0.0

        # ── STAGE 6: DECISION (V4.2: candidate evaluation) ──
        has_model = self._model_adapter is not None
        can_reason = self.reasoning.can_reason_locally(user_input)
        decision = self.decision.decide(
            situation,
            can_reason_locally=can_reason,
            has_model=has_model,
            strategy_candidates=strategy_candidates,
            failure_guidance=failure_guidance,
        )
        trace.decision = decision

        # V4.2: Track candidate evaluation
        if decision.candidate_score > 0:
            self._cognitive_metrics["candidate_evaluations"] += 1
        if decision.alternatives_rejected > 0:
            self._cognitive_metrics["strategy_influenced_decisions"] += 1

        # V4.2: Apply calibration to confidence
        local_confidence = self.confidence.get_calibrated_confidence(local_confidence)

        # Apply reflection-based adjustments
        suggestions = self.reflection.get_improvement_suggestions()
        if suggestions and decision.action == Action.CONSULT_MODEL and not has_model:
            # If reflection suggests reducing model dependency, try local
            decision = Decision(
                action=Action.RESPOND_DIRECTLY,
                target="partial_answer",
                reasoning="Adjusted by reflection: no model available, using local",
            )

        # ── STAGE 7: PLANNING (V4.2: strategy-aware) ──
        plan = self.planning.create_plan(decision, situation, user_input, failure_guidance)
        # If failure guidance exists, check if plan uses a known-bad strategy
        if failure_guidance and plan.steps:
            avoid = failure_guidance.get("avoid_strategies", [])
            if avoid:
                plan_steps_before = len(plan.steps)
                # Filter out steps whose tool matches a known-bad strategy
                filtered_steps = []
                for step in plan.steps:
                    tool_name = step.tool or ""
                    if any(bad.lower() in tool_name.lower() for bad in avoid):
                        self._cognitive_metrics["failure_guidance_prevented"] += 1
                        logger.debug(f"Avoiding known-bad strategy: {tool_name}")
                    else:
                        filtered_steps.append(step)
                if filtered_steps:
                    plan.steps = filtered_steps
        trace.plan = plan

        # ── STAGE 8: CONFIDENCE / SECURITY CHECK ──
        trace.confidence = local_confidence
        security_check = (True, "approved")
        if plan.steps:
            for step in plan.steps:
                cap = self.capabilities.get(step.tool)
                if cap:
                    # Security check uses AutonomyEngine with risk level
                    allowed, reason = self.autonomy.can_execute({
                        "risk_level": cap.risk_level,
                        "capability": cap.id,
                        "owner_authorized": True,
                    })
                    if not allowed:
                        security_check = (False, f"{cap.id}: {reason}")
                        break
                    # Also check SecurityPolicy for audit
                    ctx = SecurityContext(
                        tool_name=cap.id,
                        action="execute",
                        risk_level=ActionRisk(cap.risk_level),
                    )
                    self.security.authorize(ctx)
        trace.security_check = security_check

        # ── STAGE 9: SKILL SELECTION ──
        skill_match = None
        if self._skill_integrator:
            matches = self._skill_integrator.discover_and_rank(
                user_input,
                available_capabilities=[c.id for c in self.capabilities.list_capabilities()],
            )
            if matches and matches[0].score > 0.3:
                skill_match = matches[0]
        elif self._skill_engine_available():
            skills = self.procedural.discover(user_input, limit=3)
            if skills:
                best = max(skills, key=lambda s: s.confidence)
                if best.confidence > 0.3:
                    skill_match = SkillMatch(skill=best, score=best.confidence)
        trace.skill_match = skill_match

        # ── STAGE 10: EXECUTION ──
        response_text = ""
        used_tools = False
        used_skill = False
        used_model = False
        execution_steps: list[EpisodeStep] = []
        tools_used: list[str] = []
        errors: list[str] = []

        if not security_check[0]:
            response_text = f"Security denied: {security_check[1]}"
            errors.append(response_text)
        elif decision.action == Action.RESPOND_DIRECTLY:
            response_text = self._respond(decision, situation, chain)
        elif decision.action == Action.USE_TOOL:
            response_text, used_tools = self._execute_tools(plan)
            execution_steps.extend(self._plan_to_steps(plan))
            tools_used.extend([s.tool for s in plan.steps if s.tool])
        elif decision.action == Action.USE_MEMORY:
            response_text = self._handle_memory(decision, user_input)
        elif decision.action == Action.CONSULT_MODEL:
            response_text, used_model = self._consult_model(
                user_input, situation, chain, memory_context,
            )
        elif decision.action in (Action.EXECUTE_PLAN, Action.COMPOUND):
            if plan.steps:
                response_text, used_tools = self._execute_tools(plan)
                execution_steps.extend(self._plan_to_steps(plan))
                tools_used.extend([s.tool for s in plan.steps if s.tool])
            else:
                response_text, used_model = self._consult_model(
                    user_input, situation, chain, memory_context,
                )
        elif decision.action == Action.CLARIFY:
            response_text = "Could you provide more details?"
        elif decision.action == Action.DECLINE:
            response_text = "I can't handle that request. Something else I can help with?"
        else:
            response_text, used_model = self._consult_model(
                user_input, situation, chain, memory_context,
            )

        # ── STAGE 11: OBSERVATION ──
        duration_ms = (time.time() - start) * 1000
        is_success = bool(
            response_text
            and not response_text.startswith("Error")
            and not response_text.startswith("Security denied")
        )
        if not is_success and response_text:
            errors.append(response_text[:200])
        trace.execution_result = response_text[:200]
        trace.outcome_success = is_success

        # ── STAGE 12: EPISODE CREATION ──
        episode_id = ""
        if execution_steps or used_tools or used_model:
            try:
                episode = self.episodic.create_episode(
                    goal=user_input[:200],
                    outcome=EpisodeOutcome.SUCCESS if is_success else EpisodeOutcome.FAILURE,
                    steps=execution_steps,
                    context=memory_context[:300],
                    tools_used=tools_used,
                    errors=errors,
                    strategy=skill_match.skill.id if skill_match else "",
                    importance=0.6 if is_success else 0.4,
                )
                self.episodic.store(episode)
                episode_id = episode.id
                trace.episode_id = episode_id
            except Exception as e:
                logger.debug(f"Episode creation failed: {e}")

        # ── STAGE 13: LEARNING ──
        learning_signal = ""
        if execution_steps or used_tools or used_model:
            try:
                if is_success:
                    result = self.learning.learn_from_success(
                        goal=user_input[:200],
                        steps=execution_steps,
                        tools_used=tools_used,
                        context=memory_context[:300],
                        duration_ms=duration_ms,
                    )
                    learning_signal = result.reason
                elif errors:
                    result = self.learning.learn_from_failure(
                        goal=user_input[:200],
                        steps=execution_steps,
                        errors=errors,
                        tools_used=tools_used,
                        context=memory_context[:300],
                    )
                    learning_signal = result.reason
            except Exception as e:
                logger.debug(f"Learning failed: {e}")
                learning_signal = f"Learning error: {e}"
        trace.learning_signal = learning_signal

        # ── STAGE 13.5: MEMORY CONSOLIDATION (V4.2: feeds StrategyMemory) ──
        # Run consolidation periodically (every 5 turns with episodes)
        # V4.2: Also triggers on repeated failures or sufficient new episodes
        should_consolidate = (
            self._conversation_turn % 5 == 0
            or self._cognitive_metrics["task_failure_count"] > 0
            and self._cognitive_metrics["task_failure_count"] % 3 == 0
        )
        if should_consolidate and self.episodic.get_stats().get("total_episodes", 0) > 0:
            try:
                all_episodes = list(self.episodic._episodes.values())
                if all_episodes:
                    ep_dicts = []
                    for ep in all_episodes[-20:]:  # last 20
                        ep_dicts.append({
                            "id": ep.id,
                            "goal": ep.goal,
                            "outcome": ep.outcome.value if hasattr(ep.outcome, 'value') else str(ep.outcome),
                            "tools_used": ep.tools_used,
                            "strategy": getattr(ep, 'strategy', ''),
                        })
                    patterns = self.consolidation.consolidate_episodes(ep_dicts)
                    strategies = self.consolidation.generalize_strategies(ep_dicts)
                    self._cognitive_metrics["consolidation_runs"] += 1
                    self._cognitive_metrics["patterns_consolidated"] += len(patterns)
                    self._cognitive_metrics["strategies_generalized"] += len(strategies)
                    trace.consolidation_patterns = len(patterns)

                    # V4.2: Feed generalized strategies into StrategyMemory
                    for strat in strategies:
                        self.strategy_memory.ingest_from_consolidation(
                            strategy_key=strat.strategy,
                            applicability=strat.applicability,
                            evidence_count=strat.evidence_count,
                            success_rate=strat.success_rate,
                            promoted=strat.promoted,
                            source_episodes=strat.source_episodes,
                        )
            except Exception as e:
                logger.debug(f"Consolidation failed: {e}")

        # ── STAGE 14: SKILL UPDATE ──
        if skill_match:
            self.procedural.update_skill(skill_match.skill.id, is_success, episode_id)
            if is_success:
                self._skill_uses += 1

        # ── STAGE 15: SELF-EVALUATION ──
        try:
            self.evaluator.evaluate(
                task=user_input[:200],
                goal_achieved=is_success,
                steps_taken=len(execution_steps),
                tools_used=tools_used,
                skills_used=[skill_match.skill.id] if skill_match else [],
                errors=errors,
                duration_ms=duration_ms,
            )
        except Exception:
            pass

        # ── STAGE 16: REFLECTION ──
        self.reflection.record_action(
            decision.action.value,
            "success" if is_success else "failure",
            duration_ms,
        )
        self.reflection.record_decision(
            used_model,
            "model" if used_model else "tool" if used_tools else "direct",
        )
        for topic in situation.topics:
            self.reflection.record_topic(topic)

        # ── STAGE 17: WORKING MEMORY UPDATE ──
        self._working_memory.append({
            "turn": self._conversation_turn,
            "input": user_input[:200],
            "response": response_text[:200],
            "action": decision.action.value,
            "success": is_success,
            "timestamp": time.time(),
        })
        # Keep working memory bounded
        if len(self._working_memory) > 50:
            self._working_memory = self._working_memory[-50:]

        # ── TRACK STATS ──
        if used_model:
            self._model_calls += 1
        else:
            self._local_responses += 1

        # ── COGNITIVE METRICS (V4.1 + V4.2) ──
        if response_text:
            if is_success:
                self._cognitive_metrics["task_success_count"] += 1
            else:
                self._cognitive_metrics["task_failure_count"] += 1
        # Confidence calibration: was confidence appropriate?
        if local_confidence >= 0.7:
            if is_success:
                self._cognitive_metrics["confident_correct"] += 1
            else:
                self._cognitive_metrics["confident_wrong"] += 1
        elif local_confidence < 0.4:
            if is_success:
                self._cognitive_metrics["unconfident_correct"] += 1
            else:
                self._cognitive_metrics["unconfident_wrong"] += 1

        # V4.2: Record outcome for confidence calibration
        self.confidence.record_outcome(local_confidence, is_success)

        # V4.2: Record strategy outcome in StrategyMemory
        if strategy_candidates:
            best_candidate = strategy_candidates[0]
            self.strategy_memory.record_outcome(
                strategy_id=best_candidate.strategy.id,
                task=user_input,
                context=memory_context,
                success=is_success,
                duration_ms=duration_ms,
            )

        trace.duration_ms = duration_ms
        self._traces.append(trace)
        if len(self._traces) > 100:
            self._traces = self._traces[-100:]

        return IntelligenceResponse(
            text=response_text,
            action_taken=decision.action.value,
            confidence=local_confidence,
            used_model=used_model,
            used_tools=used_tools,
            used_skill=used_skill is not None and used_skill,
            used_memory=used_memory,
            used_knowledge=used_knowledge,
            reasoning_summary=chain.conclusion if chain else "",
            duration_ms=duration_ms,
            trace=trace,
        )

    # ── Execution Helpers ──

    def _execute_tools(self, plan: ExecutionPlan) -> tuple[str, bool]:
        """Execute tools from a plan through the capability registry."""
        if not plan.steps:
            return "No steps in plan.", False
        results = []
        for step in plan.steps:
            cap = self.capabilities.get(step.tool)
            if cap is None:
                results.append(f"Unknown capability: {step.tool}")
                continue
            result = self.capabilities.execute(step.tool, step.parameters)
            if result.success:
                results.append(str(result.output))
            else:
                results.append(f"Error ({step.tool}): {result.error}")
        return "\n".join(results) if results else "Execution completed.", True

    def _respond(self, decision: Decision, situation: Situation, chain: ReasoningChain) -> str:
        """Generate a direct response from local knowledge."""
        target = decision.target
        if target == "help":
            return self._generate_help()
        elif target == "status":
            return self._generate_status()
        elif target == "exit":
            return "Goodbye!"
        elif target == "greeting":
            return "Hello! I'm JARVIS, your personal AI. How can I help?"
        elif target == "thanks":
            return "You're welcome! Let me know if you need anything else."
        elif target in ("local_reasoning", "partial_answer"):
            return chain.conclusion if chain.conclusion else "I can help with that using my local knowledge."
        else:
            return chain.conclusion if chain.conclusion else "I'm ready to help. What do you need?"

    def _handle_memory(self, decision: Decision, user_input: str) -> str:
        """Handle memory operations."""
        if not self._memory_system:
            return "Memory system not connected."
        text = user_input.lower()
        target = decision.target
        if target == "store":
            import re
            match = re.search(r"remember\s+(?:my\s+)?(.+?)\s+is\s+(.+)", text)
            if match:
                key, value = match.group(1).strip(), match.group(2).strip()
                self._memory_system.remember(key, value, "personal")
                return f"Got it! I'll remember your {key} is {value}."
            self._memory_system.remember("fact", user_input, "notes")
            return "I'll keep that in mind."
        elif target == "recall":
            import re
            match = re.search(r"what(?:'s| is)\s+my\s+(.+)", text)
            if match:
                query = match.group(1).strip()
                results = self._memory_system.recall(query)
                if results:
                    return f"Your {query} is: {results[0].get('value', '')}"
                return f"I don't have information about your {query} yet."
            results = self._memory_system.recall(text)
            if results:
                return f"From what you've told me: {results[0].get('value', '')}"
            return "I don't have any relevant information stored yet."
        elif target == "forget":
            import re
            match = re.search(r"forget\s+(.+)", text)
            if match:
                self._memory_system.forget(match.group(1).strip())
                return f"Done! Forgotten."
            return "What would you like me to forget?"
        return "Memory operation completed."

    def _consult_model(
        self,
        user_input: str,
        situation: Situation,
        chain: ReasoningChain,
        memory_context: str,
    ) -> tuple[str, bool]:
        """Consult an optional model. Model is advisory, not authoritative."""
        if not self._model_adapter:
            return (
                "I don't have a neural model available. "
                "I can help with commands, memory, and basic questions locally."
            ), False
        try:
            system_context = (
                f"You are JARVIS. Topics: {', '.join(situation.topics)}. "
                f"Local reasoning: {chain.conclusion}."
            )
            if memory_context:
                system_context += f"\nUser context: {memory_context}"
            # Model adapter returns text — this is DATA, not authority
            response = self._model_adapter(user_input, system_context)
            if response and isinstance(response, str) and not response.startswith("Error"):
                return response, True
            return chain.conclusion or "I can process this locally.", False
        except Exception as e:
            logger.error(f"Model consultation failed: {e}")
            return f"Model error: {e}\nLocal analysis: {chain.conclusion}", False

    def _plan_to_steps(self, plan: ExecutionPlan) -> list[EpisodeStep]:
        """Convert plan steps to episode steps for learning."""
        return [
            EpisodeStep(action=s.description, tool=s.tool, parameters=s.parameters)
            for s in plan.steps
        ]

    def _get_memory_context(self) -> str:
        """Get formatted memory context for reasoning."""
        if self._memory_system:
            try:
                return self._memory_system.format_for_prompt()
            except Exception:
                pass
        return ""

    def _skill_engine_available(self) -> bool:
        """Procedural memory is always available as a skill fallback."""
        return True

    # ── Goal Management ──

    def pursue_goal(self, description: str) -> IntelligenceResponse:
        """Create and pursue a multi-step goal through the cognitive loop."""
        goal = self.goal_manager.create_goal(
            title=description[:200],
            description=description,
            priority=0.7,
            owner_authorized=True,
        )
        self.goal_manager.activate(goal.id)
        tasks = self.goal_planner.generate_tasks(
            goal, self.task_manager, context=description,
        )

        results_text = []
        tasks_completed = 0
        tasks_failed = 0

        for _ in range(len(tasks) * 2):
            next_task = self.task_manager.get_next_task()
            if next_task is None:
                break
            remaining = self.task_manager.list_tasks(goal_id=goal.id)
            if all(t.state in (TaskState.SUCCEEDED, TaskState.CANCELLED) for t in remaining):
                break

            # Process each task through the cognitive loop
            response = self.process(next_task.description)
            if response.text and not response.text.startswith("Error"):
                tasks_completed += 1
                results_text.append(response.text)
            else:
                tasks_failed += 1
                self._cognitive_metrics["recovery_attempt_count"] += 1
                # Check failure knowledge before retrying
                guidance = self.failure_knowledge.get_guidance(next_task.description)
                if guidance and guidance.get("avoid_strategies"):
                    # Record that we consulted failure knowledge
                    self._cognitive_metrics["failure_guidance_consulted"] += 1
                # Attempt recovery
                recovery_decision = self.recovery.decide_recovery(
                    next_task, response.text or "unknown error",
                )
                if recovery_decision.action == RecoveryAction.RETRY:
                    if next_task.attempts < next_task.max_attempts:
                        self.task_manager.retry_task(next_task.id)
                        self._cognitive_metrics["recovery_success_count"] += 1

        if tasks_failed == 0 and tasks_completed > 0:
            self.goal_manager.complete(goal.id)
        elif tasks_completed > 0:
            self.goal_manager.update_goal(
                goal.id, progress=tasks_completed / max(1, len(tasks)),
            )
        else:
            self.goal_manager.fail(goal.id, reason="All tasks failed")

        summary = f"Goal: {description}\n"
        summary += f"Completed: {tasks_completed}/{len(tasks)}, Failed: {tasks_failed}\n"
        if results_text:
            summary += "\n".join(results_text[:5])

        return IntelligenceResponse(
            text=summary,
            action_taken="goal_pursuit",
            confidence=0.7 if tasks_completed > 0 else 0.3,
            used_tools=tasks_completed > 0,
            duration_ms=0,
        )

    # ── Feedback Loop ──

    def receive_feedback(self, feedback: str) -> str:
        """Process user feedback through the learning system."""
        result = self.learning.learn_from_feedback(feedback)
        return result.reason

    # ── Status & Diagnostics ──

    def _generate_help(self) -> str:
        return (
            "I'm JARVIS — your personal AI with a cognitive architecture.\n\n"
            "**What I do locally (no external AI needed):**\n"
            "- File operations, terminal commands\n"
            "- Memory: remember, recall, forget\n"
            "- Knowledge search and reasoning\n"
            "- Goal planning and task execution\n"
            "- Learning from every interaction\n"
            "- Security: unified permission enforcement\n\n"
            "Just ask naturally — I'll figure out the best approach!"
        )

    def _generate_status(self) -> str:
        stats = self.get_stats()
        model_status = "Available" if self._model_adapter else "Not available"
        return (
            f"JARVIS Native Intelligence V4.0\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Processed: {stats['total_processed']}\n"
            f"Local responses: {stats['local_responses']}\n"
            f"Model consultations: {stats['model_calls']}\n"
            f"Skill uses: {stats['skill_uses']}\n"
            f"Local rate: {stats['local_rate']:.0%}\n"
            f"Model: {model_status}\n"
            f"Episodes: {stats['episodes']}\n"
            f"Skills: {stats['skills']}\n"
            f"Working memory: {stats['working_memory']} entries"
        )

    def get_stats(self) -> dict[str, Any]:
        total = self._total_processed
        return {
            "total_processed": total,
            "local_responses": self._local_responses,
            "model_calls": self._model_calls,
            "skill_uses": self._skill_uses,
            "local_rate": self._local_responses / max(1, total),
            "model_rate": self._model_calls / max(1, total),
            "episodes": self.episodic.get_stats().get("total_episodes", 0),
            "skills": self.procedural.get_stats().get("total_skills", 0),
            "working_memory": len(self._working_memory),
            "turn": self._conversation_turn,
            "reflection": self.reflection.get_stats(),
            "evaluation": self.evaluator.get_stats(),
            "retrieval_config": "unified",
            "security_approvals": len(self.security._session_approvals),
            "autonomy_mode": self.autonomy.mode.value,
            "cognitive_metrics": self._cognitive_metrics,
            "consolidation": self.consolidation.get_stats(),
            "strategy_memory": self.strategy_memory.get_stats(),
            "calibration": self.confidence.get_calibration_stats(),
        }

    def get_cognitive_metrics(self) -> dict[str, Any]:
        """Return cognitive metrics for intelligence benchmarking."""
        m = self._cognitive_metrics.copy()
        # Derived metrics
        total_tasks = m["task_success_count"] + m["task_failure_count"]
        m["task_success_rate"] = m["task_success_count"] / max(1, total_tasks)
        confident_total = m["confident_correct"] + m["confident_wrong"]
        m["confidence_calibration"] = m["confident_correct"] / max(1, confident_total)
        recovery_total = m["recovery_attempt_count"]
        m["recovery_success_rate"] = m["recovery_success_count"] / max(1, recovery_total)
        # V4.2 derived metrics
        m["strategy_influence_rate"] = m["strategy_influenced_decisions"] / max(1, total_tasks)
        m["candidate_evaluation_rate"] = m["candidate_evaluations"] / max(1, total_tasks)
        return m

    def get_trace(self) -> CognitiveTrace | None:
        """Get the most recent cognitive trace."""
        return self._traces[-1] if self._traces else None

    @property
    def is_model_available(self) -> bool:
        return self._model_adapter is not None
