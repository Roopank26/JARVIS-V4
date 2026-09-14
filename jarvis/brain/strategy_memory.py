"""
JARVIS Strategy Memory — Bridge between learned strategies and decision-making.

Stores strategies with rich evidence tracking. When a new task arrives,
retrieves relevant strategies ranked by historical success, context similarity,
and failure history.

This is the key component that makes PAST EXPERIENCE change FUTURE BEHAVIOR.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StrategyEvidence:
    """Evidence for a strategy's effectiveness in a specific context."""
    task_signature: str        # normalized task keywords
    context_signature: str     # context keywords (tools, environment, etc.)
    successes: int = 0
    failures: int = 0
    total_uses: int = 0
    last_used: float = 0.0
    avg_duration_ms: float = 0.0
    failure_types: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.total_uses)

    @property
    def confidence(self) -> float:
        """Confidence based on evidence volume and success rate."""
        if self.total_uses == 0:
            return 0.0
        base = self.success_rate
        # Volume bonus: more evidence → more confidence (up to a point)
        volume_bonus = min(0.2, self.total_uses * 0.03)
        # Recency bonus: recent use → slightly higher confidence
        age_hours = (time.time() - self.last_used) / 3600 if self.last_used else 999
        recency_bonus = max(0.0, 0.1 - age_hours * 0.001)
        return min(0.95, base + volume_bonus + recency_bonus)


@dataclass
class StrategyRecord:
    """A learned strategy with evidence across different contexts."""
    id: str
    name: str                  # human-readable strategy name
    description: str           # what this strategy does
    strategy_key: str          # key used for matching (from consolidation)
    applicability: str         # conditions under which this applies
    evidence: dict[str, StrategyEvidence] = field(default_factory=dict)  # context_sig -> evidence
    created_at: float = field(default_factory=time.time)
    promoted: bool = False     # whether this is a validated strategy
    source: str = "consolidation"  # where this came from

    @property
    def total_uses(self) -> int:
        return sum(e.total_uses for e in self.evidence.values())

    @property
    def overall_success_rate(self) -> float:
        total = sum(e.total_uses for e in self.evidence.values())
        if total == 0:
            return 0.0
        return sum(e.successes for e in self.evidence.values()) / total

    @property
    def overall_confidence(self) -> float:
        """Weighted confidence across all evidence."""
        if not self.evidence:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for ev in self.evidence.values():
            weight = ev.total_uses  # More uses → more weight
            weighted_sum += ev.confidence * weight
            total_weight += weight
        return weighted_sum / max(1, total_weight)

    def get_context_keys(self) -> list[str]:
        return list(self.evidence.keys())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_key": self.strategy_key,
            "applicability": self.applicability,
            "total_uses": self.total_uses,
            "overall_success_rate": round(self.overall_success_rate, 3),
            "overall_confidence": round(self.overall_confidence, 3),
            "promoted": self.promoted,
            "source": self.source,
            "evidence_count": len(self.evidence),
        }


@dataclass
class StrategyCandidate:
    """A candidate strategy for a specific task, with a computed score."""
    strategy: StrategyRecord
    relevance_score: float     # how relevant to the current task
    evidence_score: float      # historical success
    failure_penalty: float     # penalty from known failures
    final_score: float         # computed final score
    context_match: str         # which context matched

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.name,
            "relevance": round(self.relevance_score, 3),
            "evidence": round(self.evidence_score, 3),
            "failure_penalty": round(self.failure_penalty, 3),
            "final_score": round(self.final_score, 3),
            "context_match": self.context_match,
        }


def _make_signature(text: str) -> str:
    """Create a normalized signature from text for matching."""
    words = sorted(set(w.lower() for w in text.split() if len(w) >= 3))
    return " ".join(words[:8])


class StrategyMemory:
    """
    Stores and retrieves learned strategies with evidence tracking.

    This is the bridge between MemoryConsolidation (which generalizes strategies)
    and PlanningEngine/DecisionEngine (which need to know what strategies work).

    Flow:
        Experience → Consolidation → StrategyMemory → Planning → Decision → Action
    """

    def __init__(self):
        self._strategies: dict[str, StrategyRecord] = {}
        self._task_index: dict[str, list[str]] = {}  # word -> strategy IDs
        self._update_count: int = 0

    def ingest_from_consolidation(
        self,
        strategy_key: str,
        applicability: str,
        evidence_count: int,
        success_rate: float,
        promoted: bool,
        source_episodes: list[str] | None = None,
    ) -> StrategyRecord:
        """
        Ingest a generalized strategy from MemoryConsolidation.
        Creates or updates a StrategyRecord.
        """
        # Check if we already have this strategy
        existing = self._find_by_key(strategy_key)
        if existing:
            # Update with new evidence
            existing.promoted = existing.promoted or promoted
            return existing

        record = StrategyRecord(
            id=f"strat_{len(self._strategies)}_{int(time.time() * 1000) % 100000}",
            name=strategy_key,
            description=applicability,
            strategy_key=strategy_key,
            applicability=applicability,
            promoted=promoted,
            source="consolidation",
        )
        self._strategies[record.id] = record
        self._index_strategy(record)
        return record

    def record_outcome(
        self,
        strategy_id: str,
        task: str,
        context: str,
        success: bool,
        duration_ms: float = 0.0,
        failure_type: str = "",
    ) -> None:
        """
        Record the outcome of using a strategy.
        This is how experience changes future behavior.
        """
        record = self._strategies.get(strategy_id)
        if not record:
            return

        context_sig = _make_signature(context or task)
        if context_sig not in record.evidence:
            record.evidence[context_sig] = StrategyEvidence(
                task_signature=_make_signature(task),
                context_signature=context_sig,
            )

        ev = record.evidence[context_sig]
        ev.total_uses += 1
        ev.last_used = time.time()
        if success:
            ev.successes += 1
        else:
            ev.failures += 1
            if failure_type:
                ev.failure_types.append(failure_type)
        # Update running average duration
        if duration_ms > 0:
            ev.avg_duration_ms = (
                (ev.avg_duration_ms * (ev.total_uses - 1) + duration_ms) / ev.total_uses
            )
        self._update_count += 1

    def find_candidates(
        self,
        task: str,
        context: str = "",
        failure_guidance: dict[str, Any] | None = None,
        limit: int = 3,
    ) -> list[StrategyCandidate]:
        """
        Find candidate strategies for a task, ranked by score.

        Scoring considers:
        - Task relevance (keyword overlap)
        - Historical success rate
        - Evidence volume
        - Failure penalty (from failure knowledge)
        - Recency
        """
        task_sig = _make_signature(task)
        context_sig = _make_signature(context or task)
        task_words = set(task_sig.split())

        candidates: list[StrategyCandidate] = []
        avoid_strategies = set()
        if failure_guidance:
            for s in failure_guidance.get("avoid_strategies", []):
                avoid_strategies.add(s.lower())

        for record in self._strategies.values():
            # Calculate relevance
            strat_words = set(record.strategy_key.lower().split())
            strat_desc_words = set(record.description.lower().split())
            all_strat_words = strat_words | strat_desc_words

            if not all_strat_words:
                continue

            overlap = task_words & all_strat_words
            relevance = len(overlap) / max(1, len(task_words))
            if relevance < 0.1:
                continue

            # Evidence score from historical success
            evidence_score = record.overall_confidence

            # Context bonus: if we have evidence for similar contexts
            context_bonus = 0.0
            best_context = ""
            for ctx_sig, ev in record.evidence.items():
                ctx_words = set(ctx_sig.split())
                ctx_overlap = len(task_words & ctx_words)
                if ctx_overlap > 0:
                    ctx_score = ev.confidence * (ctx_overlap / max(1, len(task_words)))
                    if ctx_score > context_bonus:
                        context_bonus = ctx_score
                        best_context = ctx_sig

            # Failure penalty
            failure_penalty = 0.0
            if record.name.lower() in avoid_strategies:
                failure_penalty = 0.5  # Known bad strategy
            elif record.overall_success_rate < 0.3 and record.total_uses >= 2:
                failure_penalty = 0.3  # Consistently failing

            # Final score
            final_score = (
                relevance * 0.3
                + evidence_score * 0.4
                + context_bonus * 0.2
                - failure_penalty
            )
            final_score = max(0.0, min(1.0, final_score))

            candidates.append(StrategyCandidate(
                strategy=record,
                relevance_score=relevance,
                evidence_score=evidence_score,
                failure_penalty=failure_penalty,
                final_score=final_score,
                context_match=best_context or context_sig,
            ))

        # Sort by final score descending
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        return candidates[:limit]

    def get_strategy(self, strategy_id: str) -> StrategyRecord | None:
        return self._strategies.get(strategy_id)

    def get_all_strategies(self) -> list[StrategyRecord]:
        return list(self._strategies.values())

    def get_promoted_strategies(self) -> list[StrategyRecord]:
        return [s for s in self._strategies.values() if s.promoted]

    def get_stats(self) -> dict[str, Any]:
        total_uses = sum(s.total_uses for s in self._strategies.values())
        return {
            "total_strategies": len(self._strategies),
            "promoted_strategies": sum(1 for s in self._strategies.values() if s.promoted),
            "total_uses": total_uses,
            "total_outcomes_recorded": self._update_count,
            "strategies_with_evidence": sum(
                1 for s in self._strategies.values() if s.evidence
            ),
        }

    def _find_by_key(self, strategy_key: str) -> StrategyRecord | None:
        for record in self._strategies.values():
            if record.strategy_key == strategy_key:
                return record
        return None

    def _index_strategy(self, record: StrategyRecord):
        words = set(w.lower() for w in record.strategy_key.split() if len(w) >= 3)
        words.update(w.lower() for w in record.description.split() if len(w) >= 3)
        for word in words:
            self._task_index.setdefault(word, [])
            if record.id not in self._task_index[word]:
                self._task_index[word].append(record.id)
