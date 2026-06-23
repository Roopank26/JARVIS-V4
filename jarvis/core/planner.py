"""
JARVIS Planner - LLM-driven plan generation.
Adapted from Mark-XXXIX-OR's planner.py
"""

import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PlanStep:
    """Represents a single step in a plan."""
    step: int
    tool: str
    description: str
    parameters: Dict[str, Any]
    critical: bool = True


@dataclass
class Plan:
    """Represents a complete plan."""
    goal: str
    steps: List[PlanStep]

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [
                {
                    "step": s.step,
                    "tool": s.tool,
                    "description": s.description,
                    "parameters": s.parameters,
                    "critical": s.critical
                }
                for s in self.steps
            ]
        }


PLANNER_PROMPT = """You are the planning module of JARVIS, a personal AI assistant.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- Use the available tools. Never make up tools.
- Each step must use a different tool when possible.
- Max 8 steps. Use the minimum steps needed.
- Every step needs clear description.
- Output ONLY valid JSON, no markdown, no explanation.

AVAILABLE TOOLS:
- read_file: Read file contents (path)
- write_file: Create/write files (path, content)
- list_directory: List directory contents (path)
- find_files: Search for files (path, pattern)
- delete_file: Delete files (path, recursive)
- disk_usage: Get disk usage (path)
- bash: Execute shell commands (command, timeout)
- run_script: Run script files (path, args)
- get_system_info: Get system information
- open_app: Open apps/files/URLs (target)
- get_environment: Get env variables (prefix)
- get_clipboard: Get clipboard contents
- set_clipboard: Set clipboard contents

OUTPUT FORMAT:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {"param": "value"},
      "critical": true
    }
  ]
}
"""


class Planner:
    """
    LLM-driven planner for generating execution plans.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.system_prompt = PLANNER_PROMPT

    def set_llm_client(self, client):
        """Set the LLM client for plan generation."""
        self.llm_client = client

    async def create_plan(self, goal: str, context: str = "") -> Plan:
        """
        Create a plan for the given goal.

        Args:
            goal: The user's goal
            context: Additional context to consider

        Returns:
            Plan with steps to achieve the goal
        """
        if self.llm_client is None:
            return self._fallback_plan(goal)

        try:
            user_input = f"Goal: {goal}"
            if context:
                user_input += f"\n\nContext:\n{context}"

            response = await self.llm_client.generate(
                system=self.system_prompt,
                prompt=user_input,
                temperature=0.2,
                max_tokens=1024
            )

            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

            plan_data = json.loads(text)

            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(PlanStep(
                    step=step_data.get("step", 0),
                    tool=step_data.get("tool", ""),
                    description=step_data.get("description", ""),
                    parameters=step_data.get("parameters", {}),
                    critical=step_data.get("critical", True)
                ))

            return Plan(
                goal=goal,
                steps=steps
            )

        except json.JSONDecodeError as e:
            print(f"[Planner] JSON parse failed: {e}")
            return self._fallback_plan(goal)
        except Exception as e:
            print(f"[Planner] Planning failed: {e}")
            return self._fallback_plan(goal)

    async def replan(self, goal: str, completed: List[Dict],
                    failed: Optional[Dict], error: str) -> Plan:
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
                f"  - Step {s.get('step')} ({s.get('tool')}): DONE"
                for s in completed
            )

            prompt = f"""Goal: {goal}

Already completed:
{completed_str if completed_str else '  (none)'}

Failed step: [{failed.get('tool')}] {failed.get('description')}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

            response = await self.llm_client.generate(
                system=self.system_prompt,
                prompt=prompt,
                temperature=0.3,
                max_tokens=1024
            )

            text = response.strip()
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

            plan_data = json.loads(text)

            steps = []
            for step_data in plan_data.get("steps", []):
                steps.append(PlanStep(
                    step=step_data.get("step", 0),
                    tool=step_data.get("tool", ""),
                    description=step_data.get("description", ""),
                    parameters=step_data.get("parameters", {}),
                    critical=step_data.get("critical", True)
                ))

            return Plan(goal=goal, steps=steps)

        except Exception as e:
            print(f"[Planner] Replan failed: {e}")
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
                        critical=True
                    )
                ]
            )

        return Plan(
            goal=goal,
            steps=[
                PlanStep(
                    step=1,
                    tool="bash",
                    description=f"Help with: {goal}",
                    parameters={"command": f"echo '{goal}'"},
                    critical=True
                )
            ]
        )

    def validate_tool(self, tool_name: str, available_tools: List[str]) -> bool:
        """Check if a tool is available."""
        return tool_name in available_tools

    def validate_plan(self, plan: Plan, available_tools: List[str]) -> tuple[bool, List[str]]:
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
