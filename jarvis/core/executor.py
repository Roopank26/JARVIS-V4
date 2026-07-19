"""
JARVIS Executor - Plan execution with error recovery.
Adapted from Mark-XXXIX-OR's executor.py
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jarvis.tools.base import ToolResult

if TYPE_CHECKING:
    from jarvis.core.planner import PlanStep

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """Represents an executed step."""

    step: "PlanStep"
    result: ToolResult | None = None
    attempts: int = 0
    error: str | None = None


@dataclass
class ExecutionResult:
    """Result of plan execution."""

    success: bool
    summary: str
    completed_steps: list[ExecutionStep]
    failed_step: ExecutionStep | None = None
    error: str | None = None


class Executor:
    """
    Executes plans with tool calls, error handling, and recovery.
    """

    MAX_RETRIES = 3
    MAX_REPLANS = 2

    def __init__(self, tool_registry, planner=None):
        self.tool_registry = tool_registry
        self.planner = planner
        self._speak_callback: Callable | None = None
        self._cancel_flag = asyncio.Event()

    def set_speak_callback(self, callback: Callable):
        """Set the speak callback for voice output."""
        self._speak_callback = callback

    def speak(self, message: str):
        """Speak a message if callback is set."""
        if self._speak_callback:
            try:
                self._speak_callback(message)
            except Exception as e:
                logger.error(f"Speak error: {e}")

    def cancel(self):
        """Cancel the current execution."""
        self._cancel_flag.set()

    def reset(self):
        """Reset the cancel flag."""
        self._cancel_flag.clear()

    async def execute(self, goal: str, context: str = "") -> ExecutionResult:
        """
        Execute a goal by creating and running a plan.

        Args:
            goal: The goal to achieve
            context: Additional context

        Returns:
            ExecutionResult with execution details
        """
        self.reset()
        completed_steps: list[ExecutionStep] = []

        # Create initial plan
        if self.planner:
            plan = await self.planner.create_plan(goal, context)
        else:
            from jarvis.core.planner import Plan, PlanStep

            plan = Plan(
                goal=goal,
                steps=[
                    PlanStep(
                        step=1,
                        tool="bash",
                        description=f"Execute: {goal}",
                        parameters={"command": goal},
                    )
                ],
            )

        replan_attempts = 0

        while True:
            if self._cancel_flag.is_set():
                return ExecutionResult(
                    success=False, summary="Execution cancelled", completed_steps=completed_steps
                )

            success = True
            failed_step: ExecutionStep | None = None

            for plan_step in plan.steps:
                if self._cancel_flag.is_set():
                    return ExecutionResult(
                        success=False,
                        summary="Execution cancelled",
                        completed_steps=completed_steps,
                    )

                # Execute step
                execution_step, result = await self._execute_step(plan_step)

                if result.success:
                    completed_steps.append(execution_step)
                    logger.info(f"[OK] Step {plan_step.step}: {plan_step.tool}")
                else:
                    execution_step.error = result.error
                    failed_step = execution_step
                    success = False
                    logger.error(f"[FAIL] Step {plan_step.step} failed: {result.error}")
                    break

            if success:
                summary = await self._summarize(goal, completed_steps)
                return ExecutionResult(
                    success=True, summary=summary, completed_steps=completed_steps
                )

            # Handle failure
            if failed_step is None:
                return ExecutionResult(
                    success=False,
                    summary="Unknown failure",
                    completed_steps=completed_steps,
                    error="No failed step recorded",
                )

            # Try to replan
            if replan_attempts >= self.MAX_REPLANS:
                return ExecutionResult(
                    success=False,
                    summary=f"Failed after {replan_attempts} replan attempts",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=failed_step.error,
                )

            self.speak("Adjusting my approach...")
            replan_attempts += 1

            if self.planner:
                failed_data = {
                    "step": failed_step.step.step,
                    "tool": failed_step.step.tool,
                    "description": failed_step.step.description,
                    "parameters": failed_step.step.parameters,
                }
                completed_data = [
                    {"step": s.step.step, "tool": s.step.tool, "description": s.step.description}
                    for s in completed_steps
                ]
                plan = await self.planner.replan(
                    goal, completed_data, failed_data, failed_step.error or ""
                )
            else:
                # No planner, give up
                return ExecutionResult(
                    success=False,
                    summary="Execution failed without replanning capability",
                    completed_steps=completed_steps,
                    failed_step=failed_step,
                    error=failed_step.error,
                )

    async def _execute_step(self, step: "PlanStep") -> tuple[ExecutionStep, ToolResult]:
        """
        Execute a single plan step with retries.

        Returns:
            (ExecutionStep, ToolResult)
        """
        execution = ExecutionStep(step=step, attempts=0)
        result = ToolResult(success=False, output=None)

        for attempt in range(1, self.MAX_RETRIES + 1):
            execution.attempts = attempt

            if self._cancel_flag.is_set():
                result.error = "Cancelled"
                return execution, result

            try:
                result = await self.tool_registry.execute(step.tool, step.parameters)

                if result.success:
                    return execution, result

                logger.warning(f"[WARN] Attempt {attempt} failed: {result.error}")

                # Backoff on retry
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(1)

            except Exception as e:
                result.error = str(e)
                logger.warning(f"[WARN] Attempt {attempt} exception: {e}")

                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(1)

        return execution, result

    async def _summarize(self, goal: str, completed: list[ExecutionStep]) -> str:
        """Generate a summary of what was accomplished."""
        step_count = len(completed)

        if step_count == 0:
            return "No steps were completed."

        if step_count == 1:
            step = completed[0]
            return f"Completed: {step.step.description}"

        return f"Completed {step_count} steps for: {goal[:50]}..."

    async def execute_steps(self, steps: list["PlanStep"]) -> ExecutionResult:
        """
        Execute a list of plan steps directly.

        Args:
            steps: List of PlanStep to execute

        Returns:
            ExecutionResult
        """
        self.reset()
        completed_steps: list[ExecutionStep] = []

        for step in steps:
            if self._cancel_flag.is_set():
                return ExecutionResult(
                    success=False, summary="Execution cancelled", completed_steps=completed_steps
                )

            execution_step, result = await self._execute_step(step)

            if result.success:
                completed_steps.append(execution_step)
            else:
                execution_step.error = result.error
                return ExecutionResult(
                    success=False,
                    summary=f"Failed at step {step.step}: {result.error}",
                    completed_steps=completed_steps,
                    failed_step=execution_step,
                    error=result.error,
                )

        return ExecutionResult(
            success=True,
            summary=f"Completed {len(completed_steps)} steps",
            completed_steps=completed_steps,
        )
