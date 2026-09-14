"""
JARVIS Decision Engine

Makes autonomous decisions about HOW to handle requests.
Decides between: local processing, tool use, memory operations, model consultation.
Pure local logic — the brain decides, not the model.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jarvis.brain.confidence_engine import ConfidenceEngine, ConfidenceScore
from jarvis.brain.context_engine import Situation


class Action(Enum):
    """Possible high-level actions."""
    RESPOND_DIRECTLY = "respond_directly"      # Answer from local knowledge
    USE_TOOL = "use_tool"                      # Execute a specific tool
    USE_MEMORY = "use_memory"                  # Memory operation
    CONSULT_MODEL = "consult_model"            # Ask model for assistance
    EXECUTE_PLAN = "execute_plan"              # Multi-step plan
    CLARIFY = "clarify"                        # Ask user for more info
    DECLINE = "decline"                        # Cannot handle this request
    COMPOUND = "compound"                      # Multiple actions needed


@dataclass
class DecisionCandidate:
    """A candidate action with scoring attributes for comparison."""
    action: Action
    target: str = ""
    reasoning: str = ""
    requires_authorization: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)
    # Scoring attributes
    goal_relevance: float = 0.5      # 0-1: how relevant to the goal
    historical_success: float = 0.5  # 0-1: historical success rate
    strategy_compatibility: float = 0.5  # 0-1: compatible with learned strategies
    risk: float = 0.0                # 0-1: risk level
    failure_penalty: float = 0.0     # 0-1: penalty from known failures

    @property
    def score(self) -> float:
        """Compute a transparent decision score."""
        return max(0.0, min(1.0,
            self.goal_relevance * 0.25
            + self.historical_success * 0.30
            + self.strategy_compatibility * 0.25
            - self.risk * 0.10
            - self.failure_penalty * 0.10
        ))


@dataclass
class Decision:
    """A decision about how to handle a request."""
    action: Action
    target: str = ""                           # tool name, memory op, etc.
    confidence: ConfidenceScore | None = None
    reasoning: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    fallback_action: Action | None = None
    requires_authorization: bool = False
    estimated_duration_ms: float = 0.0
    candidate_score: float = 0.0               # V4.2: score from candidate evaluation
    alternatives_rejected: int = 0             # V4.2: how many alternatives were considered

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "target": self.target,
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "reasoning": self.reasoning,
            "requires_authorization": self.requires_authorization,
            "candidate_score": round(self.candidate_score, 3),
            "alternatives_rejected": self.alternatives_rejected,
        }


# Decision rules: maps (intent_category, intent_action) → action
_DECISION_RULES: dict[tuple[str, str], dict[str, Any]] = {
    # Commands → tool execution
    ("command", "read_file"): {"action": Action.USE_TOOL, "target": "read_file", "auth": False},
    ("command", "write_file"): {"action": Action.USE_TOOL, "target": "write_file", "auth": False},
    ("command", "list_dir"): {"action": Action.USE_TOOL, "target": "list_directory", "auth": False},
    ("command", "run_command"): {"action": Action.USE_TOOL, "target": "bash", "auth": True},
    ("command", "search_files"): {"action": Action.USE_TOOL, "target": "find_files", "auth": False},
    ("command", "system_info"): {"action": Action.USE_TOOL, "target": "get_system_info", "auth": False},
    ("command", "open_app"): {"action": Action.USE_TOOL, "target": "open_app", "auth": False},
    ("command", "screenshot"): {"action": Action.USE_TOOL, "target": "bash", "auth": False},

    # Memory operations
    ("request", "remember"): {"action": Action.USE_MEMORY, "target": "store", "auth": False},
    ("request", "recall"): {"action": Action.USE_MEMORY, "target": "recall", "auth": False},
    ("request", "forget"): {"action": Action.USE_MEMORY, "target": "forget", "auth": False},

    # Meta
    ("meta", "help"): {"action": Action.RESPOND_DIRECTLY, "target": "help", "auth": False},
    ("meta", "status"): {"action": Action.RESPOND_DIRECTLY, "target": "status", "auth": False},
    ("meta", "exit"): {"action": Action.RESPOND_DIRECTLY, "target": "exit", "auth": False},
    ("meta", "clear"): {"action": Action.RESPOND_DIRECTLY, "target": "clear", "auth": False},

    # Conversation
    ("conversation", "greeting"): {"action": Action.RESPOND_DIRECTLY, "target": "greeting", "auth": False},
    ("conversation", "thanks"): {"action": Action.RESPOND_DIRECTLY, "target": "thanks", "auth": False},
}


class DecisionEngine:
    """
    Makes autonomous decisions about request handling.
    The decision engine is the gatekeeper — it decides what happens,
    not the model.

    Flow:
    1. Check if local knowledge can handle it → RESPOND_DIRECTLY
    2. Check if a tool is needed → USE_TOOL
    3. Check if memory is needed → USE_MEMORY
    4. Check if reasoning is sufficient → RESPOND_DIRECTLY
    5. Only then → CONSULT_MODEL (with authorization)
    """

    def __init__(self, confidence_engine: ConfidenceEngine | None = None):
        self.confidence = confidence_engine or ConfidenceEngine()
        self._decision_history: list[Decision] = []
        self._tool_registry_names: set[str] = set()

    def set_available_tools(self, tool_names: list[str]):
        """Set the list of available tool names."""
        self._tool_registry_names = set(tool_names)

    def decide(
        self,
        situation: Situation,
        can_reason_locally: bool = False,
        has_model: bool = False,
        strategy_candidates: list[Any] | None = None,
        failure_guidance: dict[str, Any] | None = None,
    ) -> Decision:
        """
        Make a decision about how to handle a request.
        Priority: local → tools → memory → model (last resort).

        V4.2: If strategy_candidates are provided, evaluate multiple candidates
        and select the best one based on scoring.
        """
        intent = situation.intent
        if intent is None:
            return self._make_decision(
                action=Action.RESPOND_DIRECTLY,
                target="general",
                reasoning="No specific intent detected — general conversation.",
            )

        # Check decision rules
        rule_key = (intent.category, intent.action)
        if rule_key in _DECISION_RULES:
            rule = _DECISION_RULES[rule_key]
            return self._make_decision(
                action=rule["action"],
                target=rule["target"],
                reasoning=f"Matched rule: {intent.category}/{intent.action}",
                requires_authorization=rule.get("auth", False),
            )

        # V4.2: Generate and evaluate candidates for non-trivial decisions
        candidates = self._generate_candidates(
            situation, can_reason_locally, has_model, strategy_candidates, failure_guidance,
        )
        if candidates:
            best = self._select_best_candidate(candidates)
            # Convert to Decision
            decision = self._make_decision(
                action=best.action,
                target=best.target,
                reasoning=best.reasoning,
                requires_authorization=best.requires_authorization,
                parameters=best.parameters,
            )
            decision.candidate_score = best.score
            decision.alternatives_rejected = len(candidates) - 1
            return decision

        # Query → can we reason locally?
        if intent.category == "query":
            if can_reason_locally:
                return self._make_decision(
                    action=Action.RESPOND_DIRECTLY,
                    target="local_reasoning",
                    reasoning="Query can be answered from local knowledge.",
                )
            elif has_model:
                return self._make_decision(
                    action=Action.CONSULT_MODEL,
                    target="query",
                    reasoning="Query requires model assistance for comprehensive answer.",
                )
            else:
                return self._make_decision(
                    action=Action.RESPOND_DIRECTLY,
                    target="partial_answer",
                    reasoning="No model available — providing best local answer.",
                )

        # Complex requests
        if situation.complexity > 0.7:
            if has_model:
                return self._make_decision(
                    action=Action.EXECUTE_PLAN,
                    target="complex_task",
                    reasoning="Complex request requires multi-step planning.",
                )
            else:
                return self._make_decision(
                    action=Action.USE_TOOL,
                    target="bash",
                    reasoning="Complex request — attempting with tools only.",
                    requires_authorization=True,
                )

        # Research requests
        if intent.action == "research":
            return self._make_decision(
                action=Action.CONSULT_MODEL if has_model else Action.RESPOND_DIRECTLY,
                target="research",
                reasoning="Research request.",
            )

        # Default: try to respond directly
        return self._make_decision(
            action=Action.RESPOND_DIRECTLY,
            target="general",
            reasoning="Default: general conversation response.",
        )

    def _generate_candidates(
        self,
        situation: Situation,
        can_reason_locally: bool,
        has_model: bool,
        strategy_candidates: list[Any] | None,
        failure_guidance: dict[str, Any] | None,
    ) -> list[DecisionCandidate]:
        """Generate candidate actions for evaluation."""
        candidates: list[DecisionCandidate] = []
        avoid_strategies = set()
        if failure_guidance:
            for s in failure_guidance.get("avoid_strategies", []):
                avoid_strategies.add(s.lower())

        intent = situation.intent
        if not intent:
            return candidates

        # Candidate 1: Respond directly (if we can reason locally)
        if can_reason_locally:
            candidates.append(DecisionCandidate(
                action=Action.RESPOND_DIRECTLY,
                target="local_reasoning",
                reasoning="Local knowledge sufficient",
                goal_relevance=0.7,
                historical_success=0.8,
                strategy_compatibility=0.7,
                risk=0.0,
            ))

        # Candidate 2: Use tool (if command-like)
        if intent.category in ("command", "request"):
            tool_target = intent.action
            risk = 0.1 if tool_target in ("read_file", "list_dir", "system_info") else 0.3
            penalty = 0.4 if tool_target in avoid_strategies else 0.0
            candidates.append(DecisionCandidate(
                action=Action.USE_TOOL,
                target=tool_target,
                reasoning=f"Tool execution for {tool_target}",
                goal_relevance=0.8,
                historical_success=0.7,
                strategy_compatibility=0.6,
                risk=risk,
                failure_penalty=penalty,
            ))

        # Candidate 3: Consult model (if available)
        if has_model:
            candidates.append(DecisionCandidate(
                action=Action.CONSULT_MODEL,
                target="query",
                reasoning="Model assistance for comprehensive answer",
                goal_relevance=0.6,
                historical_success=0.7,
                strategy_compatibility=0.5,
                risk=0.05,
            ))

        # Candidate 4: Execute plan (for complex tasks)
        if situation.complexity > 0.5:
            candidates.append(DecisionCandidate(
                action=Action.EXECUTE_PLAN,
                target="complex_task",
                reasoning="Multi-step planning for complex task",
                goal_relevance=0.9,
                historical_success=0.6,
                strategy_compatibility=0.7,
                risk=0.1,
            ))

        # V4.2: Strategy-informed candidates
        if strategy_candidates:
            for strat in strategy_candidates[:2]:  # Top 2 strategy candidates
                strat_name = strat.strategy.name if hasattr(strat, 'strategy') else str(strat)
                score = strat.final_score if hasattr(strat, 'final_score') else 0.5
                if score > 0.3:
                    # Strategy suggests a specific approach — boost compatible candidates
                    for c in candidates:
                        if c.action in (Action.USE_TOOL, Action.EXECUTE_PLAN):
                            c.strategy_compatibility = max(c.strategy_compatibility, score)

        # If no candidates generated, add default
        if not candidates:
            candidates.append(DecisionCandidate(
                action=Action.RESPOND_DIRECTLY,
                target="general",
                reasoning="Default: general conversation response",
                goal_relevance=0.5,
                historical_success=0.6,
                strategy_compatibility=0.5,
            ))

        return candidates

    def _select_best_candidate(self, candidates: list[DecisionCandidate]) -> DecisionCandidate:
        """Select the best candidate based on transparent scoring."""
        if not candidates:
            return DecisionCandidate(action=Action.RESPOND_DIRECTLY, target="general")
        return max(candidates, key=lambda c: c.score)

    def should_use_model(self, situation: Situation, local_confidence: float) -> bool:
        """
        Decide whether to consult the model.
        Only uses model when local confidence is insufficient.
        """
        # Never for simple operations
        if situation.intent and situation.intent.category in ("command", "meta"):
            return False

        # Use model when local confidence is low and complexity is high
        if local_confidence < 0.4 and situation.complexity > 0.5:
            return True

        # Use model for questions we can't answer locally
        if situation.intent and situation.intent.category == "query" and local_confidence < 0.6:
            return True

        return False

    def _make_decision(
        self,
        action: Action,
        target: str = "",
        reasoning: str = "",
        requires_authorization: bool = False,
        parameters: dict[str, Any] | None = None,
    ) -> Decision:
        """Create and record a decision."""
        decision = Decision(
            action=action,
            target=target,
            confidence=self.confidence.score_reasoning(1, 1, 0),
            reasoning=reasoning,
            parameters=parameters or {},
            requires_authorization=requires_authorization,
        )
        self._decision_history.append(decision)
        return decision

    def get_stats(self) -> dict:
        """Get decision engine statistics."""
        if not self._decision_history:
            return {"decisions": 0}
        from collections import Counter
        action_counts = Counter(d.action.value for d in self._decision_history)
        scored = [d for d in self._decision_history if d.candidate_score > 0]
        return {
            "total_decisions": len(self._decision_history),
            "by_action": dict(action_counts),
            "model_consultations": sum(1 for d in self._decision_history if d.action == Action.CONSULT_MODEL),
            "candidate_evaluated": len(scored),
            "avg_candidate_score": (
                sum(d.candidate_score for d in scored) / max(1, len(scored))
            ),
            "avg_alternatives_rejected": (
                sum(d.alternatives_rejected for d in self._decision_history)
                / max(1, len(self._decision_history))
            ),
        }
