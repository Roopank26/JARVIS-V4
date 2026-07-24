"""
JARVIS Phase 5 — Long-Horizon Planning.

Enhances AutonomousGoalEngine with:
- Milestone auto-decomposition
- Progress trend analysis
- Blocked-task detection
- Replanning triggers
- Deadline risk prediction
- Milestone health scoring
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus
from jarvis.goals import (
    AutonomousGoalEngine,
    Goal,
    GoalProgress,
    Milestone,
    TaskPriority,
    TaskStatus,
    get_goal_engine,
)
from jarvis.goals.engine import GoalTask

logger = logging.getLogger(__name__)


@dataclass
class MilestoneHealth:
    milestone_name: str
    goal_id: str
    completion_ratio: float = 0.0
    is_blocked: bool = False
    blockers: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    recommended_action: str = "continue"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_name": self.milestone_name,
            "goal_id": self.goal_id,
            "completion_ratio": round(self.completion_ratio, 3),
            "is_blocked": self.is_blocked,
            "blockers": self.blockers,
            "risk_score": round(self.risk_score, 3),
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


@dataclass
class ReplanSuggestion:
    goal_id: str
    reason: str
    suggested_milestones: list[dict[str, Any]]
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "reason": self.reason,
            "suggested_milestones": self.suggested_milestones,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }


class LongHorizonPlanner:
    """
    Adds long-horizon intelligence on top of AutonomousGoalEngine.

    Does NOT modify or replace the goal engine. Only observes and suggests.
    """

    def __init__(self, goal_engine: AutonomousGoalEngine | None = None, bus: EventBus | None = None):
        self._engine = goal_engine or get_goal_engine()
        self._bus = bus or get_event_bus()
        self._milestone_health: dict[str, MilestoneHealth] = {}
        self._replan_history: list[ReplanSuggestion] = []

    def analyze_goal(self, goal_id: str) -> dict[str, Any] | None:
        goal = self._engine.get_goal(goal_id)
        if goal is None:
            return None
        progress = self._engine.get_progress(goal_id)
        if progress is None:
            return None

        health_reports: list[dict[str, Any]] = []
        for ms in goal.milestones:
            health = self._assess_milestone_health(goal_id, ms, progress)
            self._milestone_health[f"{goal_id}:{ms.name}"] = health
            health_reports.append(health.to_dict())

        blocked_tasks = self._detect_blocked_tasks(goal_id)
        deadline_risk = self._assess_deadline_risk(goal, progress)
        replan = self._should_replan(goal_id, progress, deadline_risk, blocked_tasks)

        return {
            "goal_id": goal_id,
            "title": goal.title,
            "status": goal.status.value,
            "progress": {
                "percent_complete": progress.percent_complete,
                "total_tasks": progress.total_tasks,
                "completed_tasks": progress.completed_tasks,
                "failed_tasks": progress.failed_tasks,
                "blocked_tasks": progress.blocked_tasks,
                "on_track": progress.on_track,
            },
            "milestone_health": health_reports,
            "blocked_tasks": blocked_tasks,
            "deadline_risk": deadline_risk,
            "replan_suggestion": replan.to_dict() if replan else None,
        }

    def decompose_milestone(self, goal_id: str, milestone_name: str, task_descriptions: list[str]) -> list[GoalTask]:
        goal = self._engine.get_goal(goal_id)
        if goal is None:
            return []
        ms = next((m for m in goal.milestones if m.name == milestone_name), None)
        if ms is None:
            ms = Milestone(name=milestone_name, description=f"Auto-created milestone for {goal_id}")
            self._engine.add_milestone(goal_id, ms)
        created: list[GoalTask] = []
        for desc in task_descriptions:
            task = self._engine.create_task(
                goal_id=goal_id,
                name=desc[:80],
                description=desc,
                priority=TaskPriority.MEDIUM,
            )
            if task:
                ms.tasks.append(task.task_id)
                ms.total_tasks += 1
                created.append(task)
        if created:
            self._bus.emit(EventType.STATUS, {
                "goal": goal_id,
                "milestone": milestone_name,
                "state": "decomposed",
                "tasks_created": len(created),
            })
        return created

    def get_progress_trend(self, goal_id: str, window: int = 10) -> dict[str, Any]:
        goal = self._engine.get_goal(goal_id)
        if goal is None:
            return {"error": "goal_not_found"}
        progress = self._engine.get_progress(goal_id)
        if progress is None:
            return {"error": "no_progress"}
        return {
            "goal_id": goal_id,
            "window": window,
            "current_percent": progress.percent_complete,
            "completed": progress.completed_tasks,
            "failed": progress.failed_tasks,
            "blocked": progress.blocked_tasks,
            "on_track": progress.on_track,
        }

    def _assess_milestone_health(self, goal_id: str, ms: Milestone, progress: GoalProgress) -> MilestoneHealth:
        ratio = ms.completed_tasks / ms.total_tasks if ms.total_tasks > 0 else 0.0
        blocked_count = sum(1 for t in self._engine.list_tasks(goal_id) if t.status == TaskStatus.BLOCKED)
        risk = 0.0
        if blocked_count > 0:
            risk += 0.3 * min(blocked_count / max(progress.total_tasks, 1), 1.0)
        if progress.failed_tasks > progress.total_tasks * 0.3:
            risk += 0.3
        if ratio < 0.2 and progress.total_tasks > 5:
            risk += 0.2
        if ms.estimated_completion and datetime.now().date() > ms.estimated_completion.date():
            risk += 0.3

        action = "continue"
        if risk >= 0.7:
            action = "replan"
        elif risk >= 0.4 or blocked_count > 0:
            action = "monitor"

        return MilestoneHealth(
            milestone_name=ms.name,
            goal_id=goal_id,
            completion_ratio=ratio,
            is_blocked=blocked_count > 0,
            blockers=[f"{blocked_count} blocked task(s)"],
            risk_score=min(1.0, risk),
            recommended_action=action,
        )

    def _detect_blocked_tasks(self, goal_id: str) -> list[dict[str, Any]]:
        blocked = [
            {
                "task_id": t.task_id,
                "name": t.name,
                "error": t.error,
                "updated_at": t.updated_at,
            }
            for t in self._engine.list_tasks(goal_id)
            if t.status == TaskStatus.BLOCKED
        ]
        return blocked

    def _assess_deadline_risk(self, goal: Goal, progress: GoalProgress) -> dict[str, Any]:
        if goal.deadline is None:
            return {"risk": "unknown", "reason": "no_deadline"}
        now = datetime.now()
        remaining = (goal.deadline - now).total_seconds()
        total = progress.total_tasks
        if total == 0:
            return {"risk": "low", "reason": "no_tasks"}
        if remaining <= 0:
            return {"risk": "overdue", "reason": "deadline_passed", "remaining_seconds": remaining}
        if progress.percent_complete < 20 and remaining < 86400:
            return {"risk": "high", "reason": "low_progress_near_deadline", "remaining_seconds": remaining}
        if progress.percent_complete < 50 and remaining < 43200:
            return {"risk": "medium", "reason": "moderate_progress_near_deadline", "remaining_seconds": remaining}
        return {"risk": "low", "reason": "on_track", "remaining_seconds": remaining}

    def predict_progress(
        self, goal_id: str, days_ahead: int = 7
    ) -> dict[str, Any]:
        goal = self._engine.get_goal(goal_id)
        if goal is None:
            return {"error": "goal_not_found"}
        progress = self._engine.get_progress(goal_id)
        if progress is None:
            return {"error": "no_progress"}
        total = progress.total_tasks
        completed = progress.completed_tasks
        if total == 0:
            return {"predicted_completion": 100.0, "days_to_complete": 0}
        rate = completed / total
        if rate >= 1.0:
            return {"predicted_completion": 100.0, "days_to_complete": 0}
        if rate <= 0.0:
            return {"predicted_completion": 0.0, "days_to_complete": None}
        estimated_days = (1.0 - rate) / max(rate / max(days_ahead, 1), 0.01)
        predicted_pct = min(100.0, rate * (1.0 + days_ahead / max(estimated_days, 1)))
        on_track = predicted_pct >= progress.percent_complete
        return {
            "current_percent": progress.percent_complete,
            "predicted_completion": round(predicted_pct, 1),
            "days_to_complete": round(estimated_days, 1),
            "on_track": on_track,
            "rate_per_day": round(rate / max(days_ahead, 1), 4),
        }

    def adaptive_replan(self, goal_id: str) -> ReplanSuggestion | None:
        goal = self._engine.get_goal(goal_id)
        if goal is None:
            return None
        progress = self._engine.get_progress(goal_id)
        if progress is None:
            return None
        deadline_risk = self._assess_deadline_risk(goal, progress)
        blocked_tasks = self._detect_blocked_tasks(goal_id)
        prediction = self.predict_progress(goal_id)
        reasons: list[str] = []
        confidence = 0.5
        if deadline_risk.get("risk") in ("overdue", "high"):
            reasons.append(f"Deadline risk: {deadline_risk.get('risk')}")
            confidence += 0.2
        if blocked_tasks:
            reasons.append(f"{len(blocked_tasks)} blocked task(s)")
            confidence += 0.15
        if not prediction.get("on_track", True):
            reasons.append("Progress trajectory off track")
            confidence += 0.15
        if progress.failed_tasks > progress.total_tasks * 0.25 and progress.total_tasks > 3:
            reasons.append("Elevated failure rate")
            confidence += 0.1
        if not reasons:
            return None
        suggested = []
        for bt in blocked_tasks[:3]:
            suggested.append({
                "type": "retry_with_fallback",
                "task_id": bt.get("task_id"),
                "name": bt.get("name"),
            })
        if not prediction.get("on_track", True):
            suggested.append({
                "type": "adjust_scope",
                "description": "Reduce scope or extend deadline to match progress trajectory",
            })
        if prediction.get("days_to_complete") and prediction["days_to_complete"] > 14:
            suggested.append({
                "type": "milestone_review",
                "description": "Review milestone decomposition for better granularity",
            })
        suggestion = ReplanSuggestion(
            goal_id=goal_id,
            reason="; ".join(reasons),
            suggested_milestones=suggested,
            confidence=min(1.0, confidence),
        )
        self._replan_history.append(suggestion)
        self._bus.emit(EventType.STATUS, {
            "goal": goal_id,
            "state": "adaptive_replan",
            "reason": suggestion.reason,
        })
        return suggestion

    def _should_replan(
        self,
        goal_id: str,
        progress: GoalProgress,
        deadline_risk: dict[str, Any],
        blocked_tasks: list[dict[str, Any]],
    ) -> ReplanSuggestion | None:
        reasons: list[str] = []
        confidence = 0.5
        if deadline_risk.get("risk") == "overdue":
            reasons.append("Goal is overdue")
            confidence += 0.2
        if deadline_risk.get("risk") == "high":
            reasons.append("Deadline approaching with low progress")
            confidence += 0.2
        if len(blocked_tasks) >= 3:
            reasons.append(f"{len(blocked_tasks)} tasks blocked")
            confidence += 0.15
        if progress.failed_tasks > progress.total_tasks * 0.3 and progress.total_tasks > 5:
            reasons.append("High failure rate")
            confidence += 0.15
        if not reasons:
            return None

        suggested = []
        for bt in blocked_tasks[:3]:
            suggested.append({
                "type": "retry_with_fallback",
                "task_id": bt.get("task_id"),
                "name": bt.get("name"),
            })
        suggested.append({
            "type": "reduce_scope",
            "description": "Remove or defer lowest-priority tasks to meet deadline",
        })

        suggestion = ReplanSuggestion(
            goal_id=goal_id,
            reason="; ".join(reasons),
            suggested_milestones=suggested,
            confidence=min(1.0, confidence),
        )
        self._replan_history.append(suggestion)
        self._bus.emit(EventType.STATUS, {
            "goal": goal_id,
            "state": "replan_suggested",
            "reason": suggestion.reason,
        })
        return suggestion


_long_horizon: LongHorizonPlanner | None = None


def get_long_horizon_planner() -> LongHorizonPlanner:
    global _long_horizon
    if _long_horizon is None:
        _long_horizon = LongHorizonPlanner()
    return _long_horizon


def reset_long_horizon_planner() -> None:
    global _long_horizon
    _long_horizon = None
