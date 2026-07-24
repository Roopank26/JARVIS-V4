"""
JARVIS Planner - LLM-driven plan generation.
Adapted from Mark-XXXIX-OR's planner.py

Key change: NEVER hardcode tool names.
The planner dynamically reads the live ToolRegistry (+ CapabilityRouter)
and injects the actual available tool list into each LLM prompt at call time.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """Represents a single step in a plan."""

    step: int
    tool: str
    description: str
    parameters: dict[str, Any]
    critical: bool = True


@dataclass
class Plan:
    """Represents a complete plan."""

    goal: str
    steps: list[PlanStep]

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [
                {
                    "step": s.step,
                    "tool": s.tool,
                    "description": s.description,
                    "parameters": s.parameters,
                    "critical": s.critical,
                }
                for s in self.steps
            ],
        }


# Dynamic planner prompt template — tool list is injected at call time
# from the live ToolRegistry. NEVER hardcode tool names here.
PLANNER_PROMPT_TEMPLATE = """You are the planning module of JARVIS, a personal AI assistant.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- Use ONLY the tools listed in AVAILABLE TOOLS. Never invent tool names.
- Each step must use a different tool when possible.
- Max 8 steps. Use the minimum steps needed.
- Every step needs a clear description and all required parameters.
- Output ONLY valid JSON, no markdown, no explanation.

AVAILABLE TOOLS (discovered at runtime — this list is authoritative):
{tool_list}

OUTPUT FORMAT:
{{
  "goal": "...",
  "steps": [
    {{
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {{"param": "value"}},
      "critical": true
    }}
  ]
}}
"""


class Planner:
    """
    LLM-driven planner for generating execution plans.

    Tool list is dynamically generated from the live ToolRegistry at every
    plan creation call. The planner never hardcodes tool names.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._tool_registry = None
        self._capability_router = None

    def set_llm_client(self, client):
        """Set the LLM client for plan generation."""
        self.llm_client = client

    def set_tool_registry(self, registry) -> None:
        """Inject the live ToolRegistry so the planner always sees current tools."""
        self._tool_registry = registry

    def set_capability_router(self, router) -> None:
        """Inject the CapabilityRouter for richer tool metadata."""
        self._capability_router = router

    def _build_tool_list(self) -> str:
        """
        Build the authoritative tool list from the live registry.

        Priority:
          1. CapabilityRouter.discover_all()  — richest metadata
          2. ToolRegistry.get_tools_for_prompt() — baseline
          3. Minimal hardcoded fallback (only bash + get_system_info)
        """
        # Option 1: CapabilityRouter (preferred)
        if self._capability_router is not None:
            try:
                caps = self._capability_router.discover_all()
                if caps:
                    lines = []
                    for cap in caps:
                        if cap.available:
                            lines.append(f"- {cap.name}: {cap.description}")
                    if lines:
                        logger.debug("[Planner] Tool list from CapabilityRouter: %d tools", len(lines))
                        return "\n".join(lines)
            except Exception as e:
                logger.debug("[Planner] CapabilityRouter failed: %s", e)

        # Option 2: ToolRegistry.get_tools_for_prompt()
        if self._tool_registry is not None:
            try:
                tools = self._tool_registry.get_tools_for_prompt()
                if tools:
                    lines = [f"- {t['name']}: {t['description']}" for t in tools]
                    logger.debug("[Planner] Tool list from ToolRegistry: %d tools", len(lines))
                    return "\n".join(lines)
            except Exception as e:
                logger.debug("[Planner] ToolRegistry failed: %s", e)

        # Option 3: Probe global registry singleton
        try:
            from jarvis.tools.registry import get_registry
            registry = get_registry()
            tools = registry.get_tools_for_prompt()
            if tools:
                lines = [f"- {t['name']}: {t['description']}" for t in tools]
                logger.debug("[Planner] Tool list from global registry: %d tools", len(lines))
                return "\n".join(lines)
        except Exception as e:
            logger.debug("[Planner] Global registry probe failed: %s", e)

        # Absolute fallback — minimum viable tools only
        logger.warning("[Planner] Using minimal fallback tool list")
        return (
            "- bash: Execute shell commands (command, timeout)\n"
            "- get_system_info: Get system information\n"
            "- speak: Speak text aloud (text)\n"
            "- generate_image: Generate an image from text (prompt)"
        )

    def _build_system_prompt(self) -> str:
        """Build the full planner system prompt with current tool list."""
        tool_list = self._build_tool_list()
        return PLANNER_PROMPT_TEMPLATE.format(tool_list=tool_list)

    async def create_plan(self, goal: str, context: str = "") -> Plan:
        """
        Create a plan for the given goal.

        The tool list is dynamically built from the live registry at call time
        so any newly installed plugin or tool is immediately visible.

        Args:
            goal: The user's goal
            context: Additional context to consider

        Returns:
            Plan with steps to achieve the goal
        """
        if self.llm_client is None:
            return self._fallback_plan(goal)

        logger.debug("[Planner] Creating plan for: %r", goal[:80])

        try:
            # Build prompt with LIVE tool list
            system_prompt = self._build_system_prompt()

            user_input = f"Goal: {goal}"
            if context:
                user_input += f"\n\nContext:\n{context}"

            response = await self.llm_client.generate(
                system=system_prompt, prompt=user_input, temperature=0.2, max_tokens=1024
            )

            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

            plan_data = json.loads(text)

            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(
                    PlanStep(
                        step=step_data.get("step", 0),
                        tool=step_data.get("tool", ""),
                        description=step_data.get("description", ""),
                        parameters=step_data.get("parameters", {}),
                        critical=step_data.get("critical", True),
                    )
                )

            return Plan(goal=goal, steps=steps)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            return self._fallback_plan(goal)
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return self._fallback_plan(goal)

    async def replan(
        self, goal: str, completed: list[dict], failed: dict | None, error: str
    ) -> Plan:
        """
        Create a revised plan after a step failure.

        Args:
            goal: Original goal
            completed: List of completed steps
            failed: Failed step info
            error: Error message from the failure

        Returns:
            Revised plan
        """
        if self.llm_client is None:
            return self._fallback_plan(goal)

        try:
            completed_str = "\n".join(
                f"  - Step {s.get('step')} ({s.get('tool')}): DONE" for s in completed
            )

            prompt = f"""Goal: {goal}

Already completed:
{completed_str if completed_str else "  (none)"}

Failed step: [{failed.get("tool")}] {failed.get("description")}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

            # Use dynamic tool list for replan too
            system_prompt = self._build_system_prompt()

            response = await self.llm_client.generate(
                system=system_prompt, prompt=prompt, temperature=0.3, max_tokens=1024
            )

            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

            plan_data = json.loads(text)

            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(
                    PlanStep(
                        step=step_data.get("step", 0),
                        tool=step_data.get("tool", ""),
                        description=step_data.get("description", ""),
                        parameters=step_data.get("parameters", {}),
                        critical=step_data.get("critical", True),
                    )
                )

            return Plan(goal=goal, steps=steps)

        except Exception as e:
            logger.error(f"Replan failed: {e}")
            return self._fallback_plan(goal)

    def _fallback_plan(self, goal: str) -> Plan:
        """Create a simple fallback plan (web search or bash)."""
        # Check if goal looks like a command
        if any(kw in goal.lower() for kw in ["run ", "execute ", "command"]):
            return Plan(
                goal=goal,
                steps=[
                    PlanStep(
                        step=1,
                        tool="bash",
                        description=f"Execute: {goal}",
                        parameters={"command": goal.split("execute ", 1)[-1].split("run ", 1)[-1]},
                        critical=True,
                    )
                ],
            )

        return Plan(
            goal=goal,
            steps=[
                PlanStep(
                    step=1,
                    tool="bash",
                    description=f"Help with: {goal}",
                    parameters={"command": f"echo '{goal}'"},
                    critical=True,
                )
            ],
        )

    def validate_tool(self, tool_name: str, available_tools: list[str]) -> bool:
        """Check if a tool is available."""
        return tool_name in available_tools

    def validate_plan(self, plan: Plan, available_tools: list[str]) -> tuple[bool, list[str]]:
        """
        Validate a plan against available tools.

        Returns:
            (is_valid, list of invalid tools)
        """
        invalid = []
        for step in plan.steps:
            if not self.validate_tool(step.tool, available_tools):
                invalid.append(step.tool)

        return len(invalid) == 0, invalid
