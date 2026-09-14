"""
JARVIS V4.2 Strategy Memory Bridge.

Stores generalized strategies from MemoryConsolidation and FailureKnowledge
in a queryable format for DecisionEngine and PlanningEngine to consume.

This is the bridge that connects learned experience to future decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyEntry:
    """A single strategy entry with context conditions and evidence."""
    id: str
    description: str
    conditions: dict[str, Any] = field(default_factory=dict)
    action_pattern: str = ""
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    avg_success_duration: float = 0.0
    source: str = "consolidation"  # consolidation | failure_knowledge | user_feedback

    @property
    def total_uses(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        total = self.total_uses
        if total == 0:
            return 0.5  # uninformative prior
        return self.success_count / total

    @property
    def evidence_strength(self) -> float:
        """How much evidence supports this strategy (0-1)."""
        # More uses → more confidence in the success_rate
        # Uses a simple saturation curve
        return min(1.0, self.total_uses / 10.0)

    def record_outcome(self, success: bool, duration_ms: float = 0.0) -> None:
        """Record a usage outcome."""
        if success:
            self.success_count += 1
            # Running average of successful duration
            n = self.success_count
            self.avg_success_duration = (
                (self.avg_success_duration * (n - 1) + duration_ms) / n
            )
        else:
            self.failure_count += 1
        self.last_used = time.time()


class StrategyMemory:
    """
    Queryable store of generalized strategies.

    Bridges MemoryConsolidation → DecisionEngine/PlanningEngine.
    Stores strategies with context conditions so decisions can be
    informed by what has worked before in similar situations.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyEntry] = {}
        self._next_id: int = 0

    def add_strategy(
        self,
        description: str,
        conditions: dict[str, Any] | None = None,
        action_pattern: str = "",
        source: str = "consolidation",
    ) -> StrategyEntry:
        """Add a new strategy to memory."""
        sid = f"strat_{self._next_id}"
        self._next_id += 1
        entry = StrategyEntry(
            id=sid,
            description=description,
            conditions=conditions or {},
            action_pattern=action_pattern,
            source=source,
        )
        self._strategies[sid] = entry
        return entry

    def get(self, strategy_id: str) -> StrategyEntry | None:
        return self._strategies.get(strategy_id)

    def find_relevant(
        self,
        task_context: str,
        limit: int = 5,
        min_evidence: float = 0.0,
    ) -> list[StrategyEntry]:
        """
        Find strategies relevant to a task context.

        Returns strategies sorted by relevance × success_rate × evidence_strength.
        """
        task_lower = task_context.lower()
        scored: list[tuple[float, StrategyEntry]] = []

        for entry in self._strategies.values():
            if entry.evidence_strength < min_evidence:
                continue

            # Relevance: keyword overlap between task and strategy
            relevance = self._compute_relevance(task_lower, entry)
            if relevance <= 0:
                continue

            combined = relevance * entry.success_rate * (0.5 + 0.5 * entry.evidence_strength)
            scored.append((combined, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def find_by_conditions(self, conditions: dict[str, Any]) -> list[StrategyEntry]:
        """Find strategies whose conditions match the given context."""
        results = []
        for entry in self._strategies.values():
            if self._conditions_match(entry.conditions, conditions):
                results.append(entry)
        return results

    def record_outcome(
        self,
        strategy_id: str,
        success: bool,
        duration_ms: float = 0.0,
    ) -> bool:
        """Record the outcome of using a strategy."""
        entry = self._strategies.get(strategy_id)
        if entry is None:
            return False
        entry.record_outcome(success, duration_ms)
        return True

    def ingest_from_consolidation(
        self,
        strategy_key: str,
        applicability: str,
        evidence_count: int,
        success_rate: float,
        promoted: bool = False,
        source_episodes: list[str] | None = None,
    ) -> StrategyEntry:
        """
        Ingest a generalized strategy from MemoryConsolidation.
        Creates or updates a strategy entry.
        """
        # Check if we already have this strategy
        existing = self._find_by_key(strategy_key)
        if existing:
            # Update with new evidence
            if promoted:
                existing.conditions["promoted"] = True
            return existing

        conditions = {"promoted": promoted} if promoted else {}
        entry = self.add_strategy(
            description=applicability,
            conditions=conditions,
            action_pattern=strategy_key,
            source="consolidation",
        )
        # Seed with the success_rate from consolidation evidence
        if evidence_count > 0:
            success_count = int(evidence_count * success_rate)
            entry.success_count = success_count
            entry.failure_count = evidence_count - success_count
        return entry

    def _find_by_key(self, action_pattern: str) -> StrategyEntry | None:
        """Find an existing strategy by its action pattern (strategy key)."""
        for entry in self._strategies.values():
            if entry.action_pattern == action_pattern:
                return entry
        return None

    def get_all(self) -> list[StrategyEntry]:
        return list(self._strategies.values())

    def get_stats(self) -> dict[str, Any]:
        total = len(self._strategies)
        if total == 0:
            return {"total_strategies": 0}
        successful = sum(1 for s in self._strategies.values() if s.success_rate > 0.6)
        return {
            "total_strategies": total,
            "well_performing": successful,
            "total_uses": sum(s.total_uses for s in self._strategies.values()),
        }

    def _compute_relevance(self, task_lower: str, entry: StrategyEntry) -> float:
        """Compute keyword overlap relevance."""
        desc_lower = entry.description.lower()
        action_lower = entry.action_pattern.lower()
        combined = f"{desc_lower} {action_lower}"

        task_words = set(task_lower.split())
        strat_words = set(combined.split())
        if not task_words or not strat_words:
            return 0.0

        overlap = task_words & strat_words
        return len(overlap) / max(len(task_words), 1)

    def _conditions_match(
        self, entry_conditions: dict[str, Any], given: dict[str, Any]
    ) -> bool:
        """Check if entry conditions are a subset of given conditions."""
        for key, val in entry_conditions.items():
            if key not in given:
                return False
            if isinstance(val, str) and isinstance(given[key], str):
                if val.lower() not in given[key].lower():
                    return False
            elif val != given[key]:
                return False
        return True
