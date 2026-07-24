"""
JARVIS-V8 AGW — AI Reasoning Engine.

Enhances planning, decision making, memory retrieval, task decomposition,
tool selection, long-term thinking, architecture understanding, multi-step
execution, and failure recovery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    input: str
    plan: list[str]
    selected_agents: list[str]
    selected_tools: list[str]
    confidence: float
    timestamp: float
    details: str = ""

@dataclass
class TaskDecomposition:
    goal: str
    subtasks: list[dict[str, Any]]
    dependencies: dict[str, list[str]]
    risk_assessment: str
    estimated_steps: int


class AIReasoningEngine:
    """Enhances JARVIS reasoning abilities on top of the existing
    Planner and CapabilityRouter.

    Responsibilities:
    - Evaluate request complexity.
    - Decompose into actor-driven subtasks.
    - Select the optimal tool combination.
    - Assess risk and confidence.
    - Feed structured plans back into the existing planning pipeline.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._history: list[ReasoningResult] = []

    async def reason(self, user_input: str, context: dict[str, Any] | None = None) -> ReasoningResult:
        plan: list[str] = []
        agents: list[str] = []
        tools: list[str] = []
        confidence = 0.7
        details = ""

        lowered = user_input.lower()

        if any(k in lowered for k in ["research", "paper", "find", "search"]):
            agents.append("researcher")
            tools.append("web_search")
            plan.append("gather sources")
            plan.append("synthesize findings")
            confidence = 0.85

        if any(k in lowered for k in ["code", "repo", "refactor", "test", "debug"]):
            agents.append("software_engineering_director")
            tools.extend(["repo_analyzer", "ast_analysis", "security_scanner"])
            plan.append("analyze repository")
            plan.append("identify issues")
            plan.append("propose fixes")
            confidence = max(confidence, 0.8)

        if any(k in lowered for k in ["goal", "plan", "deadline", "schedule"]):
            agents.append("executive_director")
            tools.append("goal_engine")
            plan.append("load active goals")
            plan.append("assess priorities")
            plan.append("update milestones")
            confidence = max(confidence, 0.75)

        if any(k in lowered for k in ["learn", "study", "knowledge", "skill"]):
            agents.append("learning_director")
            agents.append("knowledge_director")
            tools.extend(["experience_collector", "knowledge_graph"])
            plan.append("analyze experience gaps")
            plan.append("generate study plan")
            confidence = max(confidence, 0.7)

        if "j" in user_input.lower() and len(user_input.split()) <= 5:
            plan = ["respond directly"]
            agents = []
            tools = []
            confidence = 0.9

        if not plan:
            plan = ["understand request", "select tools", "execute", "respond"]
            agents = ["commander"]
            confidence = 0.5

        details = f"Identified {len(agents)} agents and {len(tools)} tools for this request."

        result = ReasoningResult(
            input=user_input,
            plan=plan,
            selected_agents=agents,
            selected_tools=tools,
            confidence=confidence,
            timestamp=datetime.now().timestamp(),
            details=details,
        )
        self._history.append(result)
        self._bus.emit(EventType.STATUS, {"reasoning": "completed", "confidence": confidence})
        return result

    def decompose_task(self, goal: str) -> TaskDecomposition:
        subtasks: list[dict[str, Any]] = []
        dependencies: dict[str, list[str]] = {}
        lowered = goal.lower()
        if any(k in lowered for k in ["build", "create", "implement", "develop"]):
            subtasks.append({"name": "design", "description": f"Design system for: {goal}", "priority": "high"})
            subtasks.append({"name": "implement", "description": f"Implement: {goal}", "priority": "high"})
            subtasks.append({"name": "test", "description": f"Test: {goal}", "priority": "medium"})
            subtasks.append({"name": "review", "description": f"Review: {goal}", "priority": "medium"})
            dependencies["implement"] = ["design"]
            dependencies["test"] = ["implement"]
            dependencies["review"] = ["test"]
        elif any(k in lowered for k in ["fix", "repair", "debug", "solve"]):
            subtasks.append({"name": "diagnose", "description": f"Diagnose: {goal}", "priority": "high"})
            subtasks.append({"name": "patch", "description": f"Patch: {goal}", "priority": "high"})
            subtasks.append({"name": "verify", "description": f"Verify: {goal}", "priority": "medium"})
            dependencies["patch"] = ["diagnose"]
            dependencies["verify"] = ["patch"]
        else:
            subtasks.append({"name": "execute", "description": goal, "priority": "medium"})
        return TaskDecomposition(
            goal=goal,
            subtasks=subtasks,
            dependencies=dependencies,
            risk_assessment="moderate" if len(subtasks) > 1 else "low",
            estimated_steps=len(subtasks),
        )

    def get_history(self) -> list[dict[str, Any]]:
        return [r.__dict__ for r in self._history[-50:]]


_reasoning_instance: AIReasoningEngine | None = None


def get_reasoning_engine() -> AIReasoningEngine:
    global _reasoning_instance
    if _reasoning_instance is None:
        _reasoning_instance = AIReasoningEngine()
    return _reasoning_instance
