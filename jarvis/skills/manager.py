"""
JARVIS Phase 3 — Skill manager module.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillMetrics:
    skill_id: str
    execution_time_ms: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    confidence: float = 0.0
    preferred_provider: str | None = None
    preferred_tools: list[str] = field(default_factory=list)
    common_errors: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    learning_priority: str = "medium"
    optimized_prompts: list[str] = field(default_factory=list)
    user_satisfaction: float | None = None
    total_executions: int = 0
    successful_executions: int = 0


class SkillManager:
    """Manages skills and their self-improvement."""

    def __init__(self) -> None:
        self._skills: dict[str, Any] = {}
        self._metrics: dict[str, SkillMetrics] = {}
        self._optimization_history: list[dict[str, Any]] = []

    def register(self, skill_id: str, skill: Any) -> None:
        self._skills[skill_id] = skill
        if skill_id not in self._metrics:
            self._metrics[skill_id] = SkillMetrics(skill_id=skill_id)

    def get(self, skill_id: str) -> Any | None:
        return self._skills.get(skill_id)

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())

    def record_execution(self, skill_id: str, result: dict[str, Any]) -> None:
        if skill_id not in self._metrics:
            self._metrics[skill_id] = SkillMetrics(skill_id=skill_id)
        metrics = self._metrics[skill_id]
        metrics.total_executions += 1
        success = bool(result.get("success", False))
        if success:
            metrics.successful_executions += 1
        duration = float(result.get("duration_ms", 0.0))
        if metrics.total_executions == 1:
            metrics.execution_time_ms = duration
        else:
            metrics.execution_time_ms = (metrics.execution_time_ms + duration) / 2.0
        metrics.success_rate = metrics.successful_executions / metrics.total_executions
        metrics.failure_rate = 1.0 - metrics.success_rate
        provider = result.get("provider")
        if provider:
            metrics.preferred_provider = provider
        tools = result.get("tools_used", [])
        if tools:
            for tool in tools:
                if tool not in metrics.preferred_tools:
                    metrics.preferred_tools.append(tool)
        error = result.get("error")
        if error and error not in metrics.common_errors:
            metrics.common_errors.append(error)
        satisfaction = result.get("user_satisfaction")
        if satisfaction is not None:
            metrics.user_satisfaction = satisfaction
        self._update_profile(skill_id)

    def _update_profile(self, skill_id: str) -> None:
        metrics = self._metrics[skill_id]
        if metrics.total_executions < 5:
            metrics.confidence = 0.3
        elif metrics.total_executions < 20:
            metrics.confidence = 0.6 + 0.01 * metrics.total_executions
        else:
            metrics.confidence = min(0.95, 0.7 + 0.005 * metrics.success_rate * metrics.total_executions)
        if metrics.failure_rate > 0.4:
            metrics.weaknesses.append("high_failure_rate")
        elif metrics.failure_rate > 0.2:
            metrics.weaknesses.append("moderate_failure_rate")
        if metrics.execution_time_ms > 3000:
            metrics.weaknesses.append("slow_execution")
        if len(metrics.common_errors) > 3:
            metrics.weaknesses.append("multiple_error_types")
        if metrics.success_rate > 0.8 and metrics.total_executions > 10:
            metrics.strengths.append("reliable")
        if metrics.success_rate > 0.9 and metrics.execution_time_ms < 1000:
            metrics.strengths.append("fast_and_accurate")
        if metrics.failure_rate > 0.3:
            metrics.learning_priority = "high"
        elif metrics.failure_rate > 0.1:
            metrics.learning_priority = "medium"
        else:
            metrics.learning_priority = "low"

    def optimize_prompt(self, skill_id: str) -> str | None:
        if skill_id not in self._metrics:
            return None
        metrics = self._metrics[skill_id]
        if not metrics.optimized_prompts:
            return None
        best = metrics.optimized_prompts[-1]
        self._optimization_history.append({
            "skill_id": skill_id,
            "prompt": best,
            "success_rate": metrics.success_rate,
            "timestamp": time.time(),
        })
        return best

    def get_metrics(self, skill_id: str) -> SkillMetrics | None:
        return self._metrics.get(skill_id)

    def get_all_metrics(self) -> dict[str, SkillMetrics]:
        return dict(self._metrics)

    def get_optimization_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._optimization_history[-limit:]


def get_skill_manager() -> SkillManager:
    global _default_skill_manager
    if "_default_skill_manager" not in globals() or _default_skill_manager is None:
        _default_skill_manager = SkillManager()
    return _default_skill_manager


def reset_skill_manager() -> None:
    global _default_skill_manager
    _default_skill_manager = None
