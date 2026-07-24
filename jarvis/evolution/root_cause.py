"""
JARVIS Phase 5 — Root Cause Learning.

When mistakes occur:
- Identify the root cause
- Record the lesson
- Apply the lesson to future tasks
- Avoid repeating the same mistake

Builds on:
- SelfReviewEngine (evolution)
- ExperienceCollector (evolution)
- KnowledgeGraphEngine (evolution)
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from jarvis.evolution.experience_collector import get_experience_collector
from jarvis.evolution.knowledge_graph_v2 import get_knowledge_graph
from jarvis.evolution.self_review import get_self_review_engine

logger = logging.getLogger(__name__)


@dataclass
class RootCause:
    cause_id: str
    task_id: str
    category: str
    description: str
    contributing_factors: list[str] = field(default_factory=list)
    severity: str = "low"
    lesson: str = ""
    actionable_fix: str = ""
    occurrences: int = 1
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cause_id": self.cause_id,
            "task_id": self.task_id,
            "category": self.category,
            "description": self.description,
            "contributing_factors": self.contributing_factors,
            "severity": self.severity,
            "lesson": self.lesson,
            "actionable_fix": self.actionable_fix,
            "occurrences": self.occurrences,
            "timestamp": self.timestamp,
        }


@dataclass
class PreventionRule:
    rule_id: str
    condition: str
    action: str
    active: bool = True
    triggered_count: int = 0
    prevented_failures: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "condition": self.condition,
            "action": self.action,
            "active": self.active,
            "triggered_count": self.triggered_count,
            "prevented_failures": self.prevented_failures,
            "timestamp": self.timestamp,
        }


class RootCauseLearner:
    """
    Identifies root causes of failures and creates prevention rules.

    Does NOT modify existing review or experience systems.
    """

    def __init__(self) -> None:
        self._review_engine = get_self_review_engine()
        self._collector = get_experience_collector()
        self._graph = get_knowledge_graph()
        self._root_causes: deque[RootCause] = deque(maxlen=3000)
        self._prevention_rules: dict[str, PreventionRule] = {}

    def analyze_failure(self, task_id: str, description: str, result: Any, duration_ms: float = 0.0) -> RootCause | None:
        text = str(result or "").lower()
        causes: list[str] = []
        category = "unknown"
        contributing: list[str] = []

        if "timeout" in text or duration_ms > 20000:
            category = "latency"
            causes.append("timeout")
            contributing.append("high_latency")
        if "not found" in text or "404" in text:
            category = "resource_missing"
            causes.append("resource_not_found")
            contributing.append("missing_dependency")
        if "permission" in text or "denied" in text or "403" in text:
            category = "permission"
            causes.append("permission_denied")
            contributing.append("access_control")
        if "connection" in text or "network" in text or "unreachable" in text:
            category = "network"
            causes.append("network_failure")
            contributing.append("connectivity")
        if "memory" in text and ("error" in text or "overflow" in text or "oom" in text):
            category = "memory"
            causes.append("memory_error")
            contributing.append("resource_exhaustion")
        if "invalid" in text or "bad request" in text or "400" in text:
            category = "input_validation"
            causes.append("invalid_input")
            contributing.append("bad_parameters")
        if not causes and ("error" in text or "failed" in text):
            category = "general"
            causes.append("unspecified_failure")
            contributing.append("unknown_factor")

        if not causes:
            return None

        existing = next((rc for rc in self._root_causes if rc.category == category and rc.description == causes[0]), None)
        if existing:
            existing.occurrences += 1
            existing.contributing_factors = list(set(existing.contributing_factors + contributing))
            return existing

        cause_id = f"rc_{int(time.time())}_{task_id[:6]}"
        lesson, fix = self._derive_lesson_and_fix(category, causes, contributing)
        root_cause = RootCause(
            cause_id=cause_id,
            task_id=task_id,
            category=category,
            description=causes[0],
            contributing_factors=contributing,
            severity=self._classify_severity(category, duration_ms),
            lesson=lesson,
            actionable_fix=fix,
        )
        self._root_causes.append(root_cause)
        try:
            self._collector.record(
                source="root_cause_learning",
                category="root_cause",
                task_id=task_id,
                input_text=description,
                output_text=fix,
                success=False,
                lessons=[lesson],
                context={"category": category, "severity": root_cause.severity},
            )
        except Exception as exc:
            logger.debug("Root cause persistence failed: %s", exc)
        try:
            pattern_node = self._graph.get_or_create_node("root_cause", category)
            task_node = self._graph.get_or_create_node("task_type", description[:50])
            if pattern_node and task_node:
                self._graph.add_edge(task_node.id, pattern_node.id, "caused_by")
        except Exception as exc:
            logger.debug("Knowledge graph update failed: %s", exc)
        return root_cause

    def get_prevention_rule(self, category: str) -> PreventionRule | None:
        return self._prevention_rules.get(category)

    def get_or_create_prevention_rule(self, category: str, condition: str, action: str) -> PreventionRule:
        if category in self._prevention_rules:
            rule = self._prevention_rules[category]
            rule.condition = condition
            rule.action = action
            return rule
        rule_id = f"pr_{int(time.time())}_{category}"
        rule = PreventionRule(rule_id=rule_id, condition=condition, action=action)
        self._prevention_rules[category] = rule
        return rule

    def trigger_prevention(self, category: str) -> str | None:
        rule = self._prevention_rules.get(category)
        if rule and rule.active:
            rule.triggered_count += 1
            return rule.action
        return None

    def get_recurring_failures(self, limit: int = 10) -> list[dict[str, Any]]:
        ranked = sorted(self._root_causes, key=lambda rc: rc.occurrences, reverse=True)
        return [rc.to_dict() for rc in ranked[:limit]]

    def get_prevention_rules(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._prevention_rules.values()]

    def _derive_lesson_and_fix(self, category: str, causes: list[str], contributing: list[str]) -> tuple[str, str]:
        lessons = {
            "latency": ("Task exceeded acceptable latency", "Add timeout handling and consider faster provider or smaller subtasks"),
            "resource_missing": ("Required resource was not found", "Verify resource availability during capability discovery before planning"),
            "permission": ("Permission was denied for the requested action", "Add pre-flight permission checks and request human approval for sensitive operations"),
            "network": ("Network operation failed", "Add retry with exponential backoff and fallback provider"),
            "memory": ("Memory limit was exceeded", "Reduce batch size, stream data, or add resource monitoring"),
            "input_validation": ("Input validation failed", "Validate inputs before execution and provide clear error messages"),
            "general": ("Task failed for an unspecified reason", "Add detailed error logging and retry logic with fallback strategies"),
        }
        lesson, fix = lessons.get(category, lessons["general"])
        return lesson, fix

    def _classify_severity(self, category: str, duration_ms: float) -> str:
        critical = {"permission", "memory", "network"}
        if category in critical:
            return "high"
        if duration_ms > 30000:
            return "high"
        if duration_ms > 10000:
            return "medium"
        return "low"


_root_cause_learner: RootCauseLearner | None = None


def get_root_cause_learner() -> RootCauseLearner:
    global _root_cause_learner
    if _root_cause_learner is None:
        _root_cause_learner = RootCauseLearner()
    return _root_cause_learner


def reset_root_cause_learner() -> None:
    global _root_cause_learner
    _root_cause_learner = None
