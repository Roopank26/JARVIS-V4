"""
Autonomous Goal Execution Engine for JARVIS.

Manages long-term goals, breaks them into milestones, generates tasks,
schedules execution, executes, monitors, adapts, and notifies the user.

Supports:
- Daily goals
- Weekly goals
- Project goals
- Learning goals
- Career goals
- Research goals

Phase 5 Long-Horizon Planning:
- Milestone auto-decomposition
- Progress trend analysis
- Blocked-task detection
- Replanning triggers
- Deadline risk prediction
"""

from jarvis.goals.engine import (
    AutonomousGoalEngine,
    Goal,
    GoalProgress,
    GoalStatus,
    GoalTask,
    GoalType,
    Milestone,
    TaskPriority,
    TaskStatus,
    get_goal_engine,
    reset_goal_engine,
)
from jarvis.goals.long_horizon import (
    LongHorizonPlanner,
    MilestoneHealth,
    ReplanSuggestion,
    get_long_horizon_planner,
    reset_long_horizon_planner,
)

__all__ = [
    "AutonomousGoalEngine",
    "Goal",
    "GoalProgress",
    "GoalStatus",
    "GoalTask",
    "GoalType",
    "LongHorizonPlanner",
    "Milestone",
    "MilestoneHealth",
    "ReplanSuggestion",
    "TaskPriority",
    "TaskStatus",
    "get_goal_engine",
    "get_long_horizon_planner",
    "reset_goal_engine",
    "reset_long_horizon_planner",
]
