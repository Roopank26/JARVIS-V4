"""
JARVIS Planning Engine

Local planning that creates execution plans from decisions.
Can operate entirely without a model using templates and heuristics.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.brain.context_engine import Situation
from jarvis.brain.decision_engine import Action, Decision


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: int
    tool: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)
    critical: bool = True
    timeout: int = 30
    can_parallel: bool = False

    def to_dict(self) -> dict:
        return {
            "step": self.step_id,
            "tool": self.tool,
            "description": self.description,
            "parameters": self.parameters,
            "critical": self.critical,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan."""
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    source: str = "local"  # local, model, hybrid
    created_at: float = field(default_factory=time.time)
    estimated_duration_ms: float = 0.0
    strategy_hint: str = ""  # V4.2: learned strategy suggestion

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "source": self.source,
            "step_count": len(self.steps),
            "strategy_hint": self.strategy_hint,
        }


# Local plan templates — no model needed
_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "read_file": [
        {"tool": "read_file", "description": "Read file contents"},
    ],
    "write_file": [
        {"tool": "write_file", "description": "Write content to file"},
    ],
    "list_dir": [
        {"tool": "list_directory", "description": "List directory contents"},
    ],
    "run_command": [
        {"tool": "bash", "description": "Execute shell command"},
    ],
    "search_files": [
        {"tool": "find_files", "description": "Search for matching files"},
    ],
    "system_info": [
        {"tool": "get_system_info", "description": "Get system information"},
    ],
    "open_app": [
        {"tool": "open_app", "description": "Open application"},
    ],
    "screenshot": [
        {"tool": "bash", "description": "Take screenshot", "parameters": {"command": "echo 'Screenshot captured'"}},
    ],
    "disk_usage": [
        {"tool": "disk_usage", "description": "Check disk usage"},
    ],
    "memory_search": [
        {"tool": "find_files", "description": "Search memory files"},
    ],
    "multi_file_read": [
        {"tool": "find_files", "description": "Find matching files"},
        {"tool": "read_file", "description": "Read found files"},
    ],
    "code_search": [
        {"tool": "bash", "description": "Search code with grep"},
        {"tool": "read_file", "description": "Read matching files"},
    ],
}


class PlanningEngine:
    """
    Creates execution plans from decisions.
    Uses templates and heuristics first, model only for complex plans.

    V4.2: Consults StrategyMemory to prefer strategies that have worked
    for similar tasks in the past.
    """

    def __init__(self):
        self._plan_history: list[ExecutionPlan] = []
        self._templates = dict(_TEMPLATES)
        self._strategy_memory: Any = None  # Set via set_strategy_memory

    def set_strategy_memory(self, strategy_memory: Any) -> None:
        """Connect the StrategyMemory for strategy-aware planning."""
        self._strategy_memory = strategy_memory

    def create_plan(
        self,
        decision: Decision,
        situation: Situation,
        user_input: str = "",
        failure_guidance: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan from a decision.
        Prioritizes local templates; model is only for complex multi-step plans.

        V4.2: Consults strategy memory for strategy-aware planning.
        V4.4: Generates alternatives and selects best plan.
        """
        goal = user_input or situation.user_input
        start = time.time()

        # V4.2: Consult strategy memory for plan optimization
        strategy_hint = self._consult_strategies(goal, situation)

        # V4.4: Generate alternative plans and select best
        candidates = self._generate_plan_candidates(
            decision, situation, goal, user_input, failure_guidance, strategy_hint,
        )
        if candidates and len(candidates) > 1:
            best = self._select_best_plan(candidates, failure_guidance)
            self._plan_history.append(best)
            return best

        # Direct tool execution
        if decision.action == Action.USE_TOOL:
            plan = self._plan_from_tool(decision, goal, situation)
            plan.strategy_hint = strategy_hint
            self._plan_history.append(plan)
            return plan

        # Memory operations
        if decision.action == Action.USE_MEMORY:
            plan = self._plan_from_memory(decision, goal)
            self._plan_history.append(plan)
            return plan

        # Direct response — no tools needed
        if decision.action == Action.RESPOND_DIRECTLY:
            plan = ExecutionPlan(goal=goal, steps=[], source="local")
            self._plan_history.append(plan)
            return plan

        # Complex plans — try local templates first
        if decision.action in (Action.EXECUTE_PLAN, Action.COMPOUND):
            plan = self._plan_complex(goal, situation, user_input)
            plan.strategy_hint = strategy_hint
            self._plan_history.append(plan)
            return plan

        # Model consultation — plan is "ask model"
        if decision.action == Action.CONSULT_MODEL:
            plan = ExecutionPlan(
                goal=goal,
                steps=[],
                source="model",
            )
            self._plan_history.append(plan)
            return plan

        # Fallback
        plan = ExecutionPlan(goal=goal, steps=[], source="local")
        self._plan_history.append(plan)
        return plan

    def _generate_plan_candidates(
        self,
        decision: Decision,
        situation: Situation,
        goal: str,
        user_input: str,
        failure_guidance: dict[str, Any] | None,
        strategy_hint: str,
    ) -> list[ExecutionPlan]:
        """V4.4: Generate multiple candidate plans for comparison."""
        candidates: list[ExecutionPlan] = []

        if decision.action == Action.USE_TOOL:
            # Primary: direct tool plan
            plan_a = self._plan_from_tool(decision, goal, situation)
            plan_a.strategy_hint = strategy_hint
            plan_a.source = "local"
            candidates.append(plan_a)

        elif decision.action in (Action.EXECUTE_PLAN, Action.COMPOUND):
            # Plan A: template-based
            plan_a = self._plan_complex(goal, situation, user_input)
            plan_a.strategy_hint = strategy_hint
            if plan_a.steps:
                candidates.append(plan_a)

            # Plan B: strategy-informed (if strategy memory has suggestions)
            if strategy_hint and not failure_guidance:
                alt_steps = self._strategy_informed_steps(goal, situation, strategy_hint)
                if alt_steps and alt_steps != plan_a.steps:
                    plan_b = ExecutionPlan(
                        goal=goal, steps=alt_steps, source="strategy",
                        strategy_hint=strategy_hint,
                    )
                    candidates.append(plan_b)

        return candidates

    def _strategy_informed_steps(
        self, goal: str, situation: Situation, strategy_hint: str,
    ) -> list[PlanStep]:
        """Generate steps informed by a learned strategy."""
        # Use the strategy hint to modify plan generation
        goal_lower = goal.lower()
        hint_lower = strategy_hint.lower()

        # If strategy suggests a specific approach, try it
        steps: list[PlanStep] = []

        # Extract tools from strategy hint
        for template_name, template_steps in self._templates.items():
            name_words = set(template_name.replace("_", " ").split())
            hint_words = set(hint_lower.split())
            if name_words & hint_words:
                for i, ts in enumerate(template_steps, 1):
                    steps.append(PlanStep(
                        step_id=i,
                        tool=ts["tool"],
                        description=ts["description"],
                        parameters=ts.get("parameters", {}),
                    ))
                break

        return steps

    def _select_best_plan(
        self,
        candidates: list[ExecutionPlan],
        failure_guidance: dict[str, Any] | None,
    ) -> ExecutionPlan:
        """V4.4: Select the best plan from candidates."""
        if not candidates:
            return ExecutionPlan(goal="", steps=[], source="local")
        if len(candidates) == 1:
            return candidates[0]

        avoid = set()
        if failure_guidance:
            for s in failure_guidance.get("avoid_strategies", []):
                avoid.add(s.lower())

        def plan_score(plan: ExecutionPlan) -> float:
            score = 0.5  # base
            # Prefer plans with steps (more complete)
            if plan.steps:
                score += 0.1
            # Penalize plans using known-bad strategies
            if plan.strategy_hint.lower() in avoid:
                score -= 0.4
            # Prefer strategy-informed plans
            if plan.source == "strategy":
                score += 0.15
            # Prefer plans with fewer steps (more efficient)
            if plan.steps:
                score += max(0, 0.1 - len(plan.steps) * 0.02)
            return score

        return max(candidates, key=plan_score)

    def _consult_strategies(self, goal: str, situation: Situation) -> str:
        """
        V4.2: Consult strategy memory for planning hints.
        Returns a strategy description if a good strategy is found, empty string otherwise.
        """
        if not self._strategy_memory:
            return ""
        try:
            candidates = self._strategy_memory.find_relevant(
                task_context=goal,
                limit=1,
            )
            if candidates and candidates[0].success_rate > 0.4:
                return candidates[0].description
        except Exception:
            pass
        return ""

    def _plan_from_tool(self, decision: Decision, goal: str, situation: Situation) -> ExecutionPlan:
        """Create a plan for a single tool execution."""
        tool_name = decision.target

        # Extract parameters from the situation
        params = self._extract_tool_params(tool_name, situation)

        step = PlanStep(
            step_id=1,
            tool=tool_name,
            description=f"Execute {tool_name}",
            parameters=params,
            critical=True,
        )

        return ExecutionPlan(goal=goal, steps=[step], source="local")

    def _plan_from_memory(self, decision: Decision, goal: str) -> ExecutionPlan:
        """Create a plan for memory operations."""
        # Memory operations don't need tool steps — they're handled directly
        return ExecutionPlan(goal=goal, steps=[], source="local")

    def _plan_complex(self, goal: str, situation: Situation, user_input: str) -> ExecutionPlan:
        """Create a plan for complex multi-step requests."""
        # Try template matching
        plan = self._match_template(goal, situation)
        if plan:
            return plan

        # Heuristic: extract commands from multi-part request
        steps = self._extract_multi_steps(user_input)
        if steps:
            return ExecutionPlan(goal=goal, steps=steps, source="local")

        # No local plan possible
        return ExecutionPlan(goal=goal, steps=[], source="model")

    def _match_template(self, goal: str, situation: Situation) -> ExecutionPlan | None:
        """Try to match the goal to a plan template."""
        goal_lower = goal.lower()

        # Direct template matches
        for template_name, template_steps in self._templates.items():
            if template_name.replace("_", " ") in goal_lower:
                steps = []
                for i, ts in enumerate(template_steps, 1):
                    params = ts.get("parameters", {})
                    if not params and situation.entities:
                        # Try to fill params from entities
                        for entity in situation.entities:
                            if entity.kind == "file" and "path" not in params:
                                params["path"] = entity.name
                            elif entity.kind == "app" and "target" not in params:
                                params["target"] = entity.name
                    steps.append(PlanStep(
                        step_id=i,
                        tool=ts["tool"],
                        description=ts["description"],
                        parameters=params,
                    ))
                return ExecutionPlan(goal=goal, steps=steps, source="local")

        # Pattern matching for common commands
        patterns = [
            (r"(?:read|open|cat|view)\s+(.+)", "read_file", "path"),
            (r"(?:write|create)\s+(?:file\s+)?(.+)", "write_file", "path"),
            (r"(?:ls|list|dir)\s*(.*)", "list_directory", "path"),
            (r"(?:run|exec|execute)\s+(.+)", "bash", "command"),
            (r"(?:find|search|grep)\s+(.+)", "find_files", "pattern"),
            (r"(?:open|launch|start)\s+(\w+)", "open_app", "target"),
        ]

        for pattern, tool, param_name in patterns:
            match = re.search(pattern, goal_lower)
            if match:
                value = match.group(1).strip()
                if tool == "list_directory" and not value:
                    value = "."
                step = PlanStep(
                    step_id=1,
                    tool=tool,
                    description=f"Execute {tool}: {value}",
                    parameters={param_name: value},
                )
                return ExecutionPlan(goal=goal, steps=[step], source="local")

        return None

    def _extract_multi_steps(self, text: str) -> list[PlanStep]:
        """Extract multiple steps from a complex request."""
        steps = []
        text_lower = text.lower()

        # Split on "and then", "then", "and also"
        parts = re.split(r"\s+(?:and\s+then|then|and\s+also|after\s+that)\s+", text_lower)

        for i, part in enumerate(parts, 1):
            part = part.strip()
            if not part:
                continue

            # Match each part to a tool
            for pattern, tool, param_name in [
                (r"(?:read|open|cat)\s+(.+)", "read_file", "path"),
                (r"(?:write|create)\s+(.+)", "write_file", "path"),
                (r"(?:run|exec)\s+(.+)", "bash", "command"),
                (r"(?:find|search)\s+(.+)", "find_files", "pattern"),
                (r"(?:list|ls|dir)\s*(.*)", "list_directory", "path"),
            ]:
                match = re.search(pattern, part)
                if match:
                    value = match.group(1).strip()
                    steps.append(PlanStep(
                        step_id=i,
                        tool=tool,
                        description=f"Step {i}: {part[:50]}",
                        parameters={param_name: value},
                    ))
                    break

        return steps

    def _extract_tool_params(self, tool_name: str, situation: Situation) -> dict[str, Any]:
        """Extract tool parameters from the situation."""
        params: dict[str, Any] = {}

        # Get params from entities
        for entity in situation.entities:
            if entity.kind == "file" and tool_name in ("read_file", "write_file", "list_directory", "find_files", "disk_usage"):
                if tool_name == "find_files":
                    params["pattern"] = entity.name
                else:
                    params["path"] = entity.name
            elif entity.kind == "app" and tool_name == "open_app":
                params["target"] = entity.name
            elif entity.kind == "url" and tool_name == "open_app":
                params["target"] = entity.name

        # Extract from raw text if params still empty
        if not params:
            text = situation.user_input.lower()
            if tool_name == "bash":
                # Try to extract command
                match = re.search(r"(?:run|execute|exec)\s+(.+)", text)
                if match:
                    params["command"] = match.group(1).strip()
                else:
                    params["command"] = situation.user_input
            elif tool_name == "read_file":
                match = re.search(r"(?:read|open|cat|view)\s+(.+)", text)
                if match:
                    params["path"] = match.group(1).strip()
            elif tool_name == "list_directory":
                match = re.search(r"(?:ls|list|dir)\s*(.*)", text)
                params["path"] = match.group(1).strip() if match and match.group(1).strip() else "."
            elif tool_name == "find_files":
                match = re.search(r"(?:find|search|grep)\s+(.+)", text)
                if match:
                    params["pattern"] = match.group(1).strip()
                params.setdefault("path", ".")

        return params

    def get_stats(self) -> dict:
        return {
            "total_plans": len(self._plan_history),
            "local_plans": sum(1 for p in self._plan_history if p.source == "local"),
            "model_plans": sum(1 for p in self._plan_history if p.source == "model"),
            "avg_steps": (
                sum(len(p.steps) for p in self._plan_history) /
                max(1, len(self._plan_history))
            ),
        }
