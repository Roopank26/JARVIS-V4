"""
JARVIS V4.3 — Unified Cognitive State

A single state object that flows through the entire cognitive loop.
Every stage reads from and writes to this state, creating a complete
record of the cognitive process.

This is NOT a replacement for existing components — it's the connective
tissue that makes them share a unified view of the current task.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(Enum):
    """Types of reasoning items — not all information is equally trustworthy."""
    FACT = "fact"                  # Verified, high confidence
    EVIDENCE = "evidence"          # Supporting data, source-dependent
    OBSERVATION = "observation"    # Directly observed, high reliability
    MEMORY = "memory"              # Retrieved from memory, may be stale
    INFERENCE = "inference"        # Deduced from other items
    HYPOTHESIS = "hypothesis"      # Unverified guess, low confidence
    ASSUMPTION = "assumption"      # Taken for granted, may be wrong
    CONSTRAINT = "constraint"      # A rule or limitation
    UNKNOWN = "unknown"            # Missing information


class VerificationStatus(Enum):
    """Whether an execution result has been verified."""
    NOT_VERIFIED = "not_verified"
    VERIFIED_SUCCESS = "verified_success"
    VERIFIED_FAILURE = "verified_failure"
    VERIFICATION_SKIPPED = "verification_skipped"
    VERIFICATION_IMPOSSIBLE = "verification_impossible"


class TaskPhase(Enum):
    """What phase the current task is in."""
    PERCEPTION = "perception"
    REASONING = "reasoning"
    PLANNING = "planning"
    DECISION = "decision"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    LEARNING = "learning"
    COMPLETE = "complete"


@dataclass
class ReasoningItem:
    """
    A single piece of reasoning evidence with full provenance.

    Different types carry different default confidence levels.
    A hypothesis is NOT a fact — the type system enforces this.
    """
    item_type: ItemType
    content: str
    source: str = ""                 # where this came from
    provenance: str = ""             # specific source identifier
    confidence: float = 0.5          # 0-1
    reliability: float = 0.5         # 0-1, how reliable the source is
    timestamp: float = field(default_factory=time.time)
    is_observed: bool = False        # directly observed vs inferred
    supporting_evidence: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_confidence(self) -> float:
        """Confidence adjusted by reliability and contradictions."""
        base = self.confidence * self.reliability
        # Contradictions reduce confidence
        contradiction_penalty = len(self.contradictions) * 0.15
        return max(0.05, min(0.95, base - contradiction_penalty))

    @property
    def is_certain(self) -> bool:
        """Only facts and observations with high confidence are certain."""
        return (
            self.item_type in (ItemType.FACT, ItemType.OBSERVATION)
            and self.effective_confidence > 0.8
            and not self.contradictions
        )

    @property
    def needs_verification(self) -> bool:
        """Hypotheses and inferences need verification."""
        return self.item_type in (
            ItemType.HYPOTHESIS, ItemType.INFERENCE, ItemType.ASSUMPTION
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.item_type.value,
            "content": self.content[:200],
            "source": self.source,
            "confidence": round(self.effective_confidence, 3),
            "is_certain": self.is_certain,
            "needs_verification": self.needs_verification,
            "contradictions": len(self.contradictions),
        }


@dataclass
class EvidenceLink:
    """A link between evidence items showing support or contradiction."""
    source_id: str
    target_id: str
    relation: str  # supports, contradicts, extends, requires
    strength: float = 0.5  # how strongly it supports/contradicts


@dataclass
class UncertainFact:
    """A fact that JARVIS is uncertain about and might need to verify."""
    question: str
    current_best_guess: str = ""
    confidence: float = 0.0
    information_value: float = 0.0  # how much resolving this would help
    verification_cost: float = 0.5  # how expensive to verify
    attempts: int = 0

    @property
    def priority(self) -> float:
        """Priority for information gathering."""
        if self.verification_cost <= 0:
            return self.information_value
        return self.information_value / self.verification_cost


@dataclass
class CognitiveState:
    """
    The unified cognitive state that flows through the entire loop.

    Every major stage reads from and writes to this state.
    At the end of a cycle, this state represents the complete
    record of what JARVIS thought, decided, and learned.
    """

    # ── Identity / Task ──
    task_id: str = ""
    current_task: str = ""
    current_goal: str = ""
    parent_goal: str = ""
    task_phase: TaskPhase = TaskPhase.PERCEPTION
    task_priority: float = 0.5
    task_status: str = "active"

    # ── Environment ──
    observations: list[str] = field(default_factory=list)
    relevant_entities: list[str] = field(default_factory=list)
    available_tools: list[str] = field(default_factory=list)
    environment_facts: dict[str, str] = field(default_factory=dict)

    # ── Knowledge / Evidence ──
    reasoning_items: list[ReasoningItem] = field(default_factory=list)
    evidence_links: list[EvidenceLink] = field(default_factory=list)
    known_facts: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    # ── Uncertainty ──
    uncertain_facts: list[UncertainFact] = field(default_factory=list)
    competing_hypotheses: list[str] = field(default_factory=list)
    overall_confidence: float = 0.5
    unresolved_questions: list[str] = field(default_factory=list)

    # ── Planning ──
    current_plan_description: str = ""
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    blocked_steps: list[str] = field(default_factory=list)
    alternative_plans: list[str] = field(default_factory=list)
    recovery_options: list[str] = field(default_factory=list)
    strategy_hint: str = ""

    # ── Execution ──
    selected_action: str = ""
    action_result: str = ""
    execution_status: str = "not_started"
    errors: list[str] = field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.NOT_VERIFIED

    # ── Learning ──
    previous_experiences: list[str] = field(default_factory=list)
    successful_strategies: list[str] = field(default_factory=list)
    failed_strategies: list[str] = field(default_factory=list)
    learned_constraints: list[str] = field(default_factory=list)
    confidence_calibration: float = 0.0

    # ── Metadata ──
    cycle_start: float = field(default_factory=time.time)
    turn_number: int = 0
    duration_ms: float = 0.0

    def add_reasoning_item(
        self,
        item_type: ItemType,
        content: str,
        source: str = "",
        confidence: float = 0.5,
        reliability: float = 0.5,
        **kwargs: Any,
    ) -> ReasoningItem:
        """Add a typed reasoning item to the state."""
        # Adjust default confidence by type
        type_confidence = {
            ItemType.FACT: 0.95,
            ItemType.OBSERVATION: 0.9,
            ItemType.EVIDENCE: 0.7,
            ItemType.MEMORY: 0.6,
            ItemType.INFERENCE: 0.5,
            ItemType.HYPOTHESIS: 0.3,
            ItemType.ASSUMPTION: 0.4,
            ItemType.CONSTRAINT: 0.9,
            ItemType.UNKNOWN: 0.1,
        }
        if confidence == 0.5:  # only override default
            confidence = type_confidence.get(item_type, 0.5)

        item = ReasoningItem(
            item_type=item_type,
            content=content,
            source=source,
            confidence=confidence,
            reliability=reliability,
            **kwargs,
        )
        self.reasoning_items.append(item)
        return item

    def add_uncertain_fact(
        self,
        question: str,
        information_value: float = 0.5,
        verification_cost: float = 0.5,
    ) -> UncertainFact:
        """Register something JARVIS is uncertain about."""
        fact = UncertainFact(
            question=question,
            information_value=information_value,
            verification_cost=verification_cost,
        )
        self.uncertain_facts.append(fact)
        self.unresolved_questions.append(question)
        return fact

    def find_contradictions(self) -> list[tuple[ReasoningItem, ReasoningItem]]:
        """Find reasoning items that contradict each other."""
        contradictions = []
        facts = [
            item for item in self.reasoning_items
            if item.item_type in (ItemType.FACT, ItemType.OBSERVATION, ItemType.EVIDENCE)
        ]
        for i, a in enumerate(facts):
            for b in facts[i + 1:]:
                # Simple contradiction: same topic, opposite meaning
                a_words = set(a.content.lower().split())
                b_words = set(b.content.lower().split())
                overlap = a_words & b_words
                if len(overlap) >= 2:
                    # Check for negation patterns
                    a_neg = any(n in a.content.lower() for n in ["not", "no", "never", "cannot", "isn't"])
                    b_neg = any(n in b.content.lower() for n in ["not", "no", "never", "cannot", "isn't"])
                    if a_neg != b_neg:
                        contradictions.append((a, b))
                        a.contradictions.append(b.content[:50])
                        b.contradictions.append(a.content[:50])
        return contradictions

    def get_highest_value_uncertainty(self) -> UncertainFact | None:
        """Get the uncertain fact with the highest information value."""
        if not self.uncertain_facts:
            return None
        return max(self.uncertain_facts, key=lambda u: u.priority)

    def should_gather_information(self, threshold: float = 0.6) -> bool:
        """
        V4.4: Determine whether JARVIS should gather information before acting.

        Returns True when the highest-value uncertainty exceeds the threshold
        and the acquisition cost is reasonable.
        """
        best = self.get_highest_value_uncertainty()
        if best is None:
            return False
        # Only gather if uncertainty is significant AND information value is high
        if best.information_value < threshold:
            return False
        # Don't gather if verification cost is prohibitive
        if best.verification_cost > 0.9:
            return False
        # Gather if overall confidence is low and information would help
        if self.get_overall_confidence() < 0.4 and best.priority > 0.5:
            return True
        return best.priority > threshold

    def compute_state_delta(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> dict[str, Any]:
        """
        V4.4: Compute the delta between before and after states.

        Returns a structured delta showing expected vs actual changes.
        """
        delta: dict[str, Any] = {
            "changed_keys": [],
            "added_keys": [],
            "removed_keys": [],
            "unchanged_keys": [],
            "result": "UNKNOWN",
        }

        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            in_before = key in before
            in_after = key in after
            if in_before and in_after:
                if before[key] != after[key]:
                    delta["changed_keys"].append(key)
                else:
                    delta["unchanged_keys"].append(key)
            elif in_after and not in_before:
                delta["added_keys"].append(key)
            elif in_before and not in_after:
                delta["removed_keys"].append(key)

        # Determine result
        if not delta["changed_keys"] and not delta["added_keys"] and not delta["removed_keys"]:
            delta["result"] = "NO_CHANGE"
        elif delta["changed_keys"] or delta["added_keys"]:
            delta["result"] = "EXPECTED_CHANGE"

        return delta

    def get_certain_facts(self) -> list[ReasoningItem]:
        """Get only facts/observations that are certain."""
        return [item for item in self.reasoning_items if item.is_certain]

    def get_hypotheses(self) -> list[ReasoningItem]:
        """Get unverified hypotheses."""
        return [
            item for item in self.reasoning_items
            if item.item_type == ItemType.HYPOTHESIS
        ]

    def get_overall_confidence(self) -> float:
        """Compute overall confidence from all reasoning items."""
        if not self.reasoning_items:
            return 0.5
        # Weight by type: facts count more than hypotheses
        type_weights = {
            ItemType.FACT: 1.0,
            ItemType.OBSERVATION: 0.95,
            ItemType.EVIDENCE: 0.8,
            ItemType.MEMORY: 0.6,
            ItemType.INFERENCE: 0.5,
            ItemType.HYPOTHESIS: 0.3,
            ItemType.ASSUMPTION: 0.35,
            ItemType.CONSTRAINT: 0.9,
            ItemType.UNKNOWN: 0.1,
        }
        total_weight = 0.0
        weighted_sum = 0.0
        for item in self.reasoning_items:
            weight = type_weights.get(item.item_type, 0.5)
            weighted_sum += item.effective_confidence * weight
            total_weight += weight
        return weighted_sum / max(0.01, total_weight)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.current_task[:100],
            "phase": self.task_phase.value,
            "confidence": round(self.get_overall_confidence(), 3),
            "reasoning_items": len(self.reasoning_items),
            "certain_facts": len(self.get_certain_facts()),
            "hypotheses": len(self.get_hypotheses()),
            "uncertainties": len(self.uncertain_facts),
            "contradictions": len(self.find_contradictions()),
            "completed_steps": len(self.completed_steps),
            "pending_steps": len(self.pending_steps),
            "errors": len(self.errors),
            "verification": self.verification_status.value,
        }

    def snapshot(self) -> dict[str, Any]:
        """Create a complete snapshot for debugging/analysis."""
        return {
            "identity": {
                "task": self.current_task,
                "goal": self.current_goal,
                "phase": self.task_phase.value,
                "priority": self.task_priority,
            },
            "knowledge": {
                "items": [i.to_dict() for i in self.reasoning_items],
                "known_facts": self.known_facts,
                "constraints": self.constraints,
            },
            "uncertainty": {
                "overall_confidence": round(self.get_overall_confidence(), 3),
                "uncertain_facts": len(self.uncertain_facts),
                "hypotheses": len(self.get_hypotheses()),
                "unresolved": self.unresolved_questions,
            },
            "planning": {
                "plan": self.current_plan_description,
                "completed": self.completed_steps,
                "pending": self.pending_steps,
                "recovery": self.recovery_options,
            },
            "execution": {
                "action": self.selected_action,
                "status": self.execution_status,
                "errors": self.errors,
                "verification": self.verification_status.value,
            },
            "learning": {
                "experiences": len(self.previous_experiences),
                "successful_strategies": self.successful_strategies,
                "failed_strategies": self.failed_strategies,
            },
        }
