"""
JARVIS Orchestrator.

A thin presentation/orchestration layer that wraps the existing
:class:`jarvis.core.agent.JarvisAgent` and exposes a *premium* interaction
surface: visible reasoning stages, autonomous planning, and token-by-token
streaming. It does not replace any backend logic — it composes the agent,
planner, executor and provider manager that already exist.

Design notes (per architecture constraints):
- ``core/`` agent/planner/executor stay untouched.
- The orchestrator only *observes and emits*; it adds a streaming path on top
  of the existing non-streaming ``answer_query`` for chat responses.
- Tool execution still flows through ``ToolRegistry``; we subscribe to its
  existing callback interface to surface tool events.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from jarvis.errors import handle_error
from jarvis.events import (
    EventBus,
    EventType,
    Stage,
    get_event_bus,
)

logger = logging.getLogger(__name__)


class _ToolEventBridge:
    """Bridges ToolRegistry callbacks to the event bus (no backend change)."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def on_tool_start(self, tool_name: str, input_data: dict[str, Any]) -> None:
        self._bus.emit(
            EventType.TOOL,
            {
                "phase": "start",
                "tool": tool_name,
                "input": {k: _safe(v) for k, v in (input_data or {}).items()},
            },
        )

    def on_tool_complete(self, tool_name: str, result: Any) -> None:
        ok = getattr(result, "success", True)
        self._bus.emit(
            EventType.TOOL,
            {
                "phase": "complete",
                "tool": tool_name,
                "success": bool(ok),
                "summary": _summarize_result(result),
            },
        )

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        self._bus.emit(
            EventType.TOOL,
            {
                "phase": "error",
                "tool": tool_name,
                "error": str(error),
            },
        )


def _safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)[:200]


def _summarize_result(result: Any) -> str:
    if result is None:
        return ""
    out = getattr(result, "output", None)
    if out is None:
        return ""
    text = str(out)
    return text if len(text) <= 240 else text[:240] + "…"


class JarvisOrchestrator:
    """
    Premium orchestration layer over the JARVIS agent.

    Use :meth:`process` for a full request lifecycle with reasoning-stage
    events, or :meth:`stream_response` for a token stream of a chat answer.
    """

    def __init__(
        self,
        agent: Any,
        bus: EventBus | None = None,
    ) -> None:
        self.agent = agent
        self.bus = bus or get_event_bus()
        self._bridge = _ToolEventBridge(self.bus)
        self._wire_tools()
        # Track whether current request is voice-driven (for interrupt handling)
        self.voice_active = False
        self._interrupt_event: asyncio.Event | None = None

        # Tool/plan caches for the UI
        self.last_plan: dict[str, Any] | None = None
        self._request_id: str | None = None

    def _wire_tools(self) -> None:
        try:
            registry = self.agent.tools
            if hasattr(registry, "add_callback"):
                registry.add_callback(self._bridge)
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Could not wire tool callbacks: {e}")

    def set_interrupt_event(self, event: asyncio.Event) -> None:
        """Register a voice interrupt event (set when the user starts talking)."""
        self._interrupt_event = event

    async def process(self, user_input: str) -> str:
        """
        Process a user request with full premium lifecycle:
        stages → (plan) → tools → streaming response.
        """
        self._request_id = user_input[:40]
        self.bus.emit(EventType.USER_MESSAGE, {"content": user_input})
        self.bus.emit(EventType.STAGE, {"stage": Stage.THINKING})

        try:
            # Decide whether this is a multi-step (planned) task.
            is_plan_task = await self._looks_like_plan_task(user_input)

            if is_plan_task:
                return await self._process_plan_task(user_input)

            # Simple request: stage walk + streaming answer.
            self.bus.emit(EventType.STAGE, {"stage": Stage.PLANNING})
            self.bus.emit(EventType.STAGE, {"stage": Stage.SELECTING_TOOLS})
            self.bus.emit(EventType.STAGE, {"stage": Stage.GENERATING})

            response = await self._stream_chat_answer(user_input)

            self.bus.emit(EventType.STAGE, {"stage": Stage.COMPLETE})
            self.bus.emit(EventType.ASSISTANT_MESSAGE, {"content": response})
            return response

        except Exception as e:
            friendly = handle_error(e, context="processing your request")
            self.bus.emit(EventType.ERROR, friendly.to_dict())
            self.bus.emit(EventType.STAGE, {"stage": Stage.COMPLETE})
            return friendly.reason

    async def _looks_like_plan_task(self, text: str) -> bool:
        """Heuristic: does this warrant an autonomous plan?"""
        lowered = text.lower()
        signals = [
            "research",
            "create a report",
            "generate report",
            "summarize",
            "build",
            "make a",
            "create",
            "index repository",
            "analyze repository",
            "plan",
            "step by step",
            "ingest",
            "export",
            "download",
            "automate",
        ]
        # Multi-verb / "and then" requests are good plan candidates
        if " then " in lowered or (
            " and " in lowered
            and any(s in lowered for s in ["research", "create", "generate", "build", "index"])
        ):
            return True
        return any(s in lowered for s in signals)

    async def _process_plan_task(self, user_input: str) -> str:
        """Autonomous planning + execution with visible plan (Feature 6)."""
        self.bus.emit(EventType.STAGE, {"stage": Stage.PLANNING})

        plan = await self._build_plan(user_input)
        if plan is None:
            # Fall back to a normal chat answer
            self.bus.emit(EventType.STAGE, {"stage": Stage.GENERATING})
            response = await self._stream_chat_answer(user_input)
            self.bus.emit(EventType.STAGE, {"stage": Stage.COMPLETE})
            self.bus.emit(EventType.ASSISTANT_MESSAGE, {"content": response})
            return response

        self.last_plan = plan
        self.bus.emit(EventType.PLAN, {"plan": plan})
        self.bus.emit(EventType.STAGE, {"stage": Stage.SELECTING_TOOLS})

        # Execute the plan, emitting step + tool + observing stages.
        self.bus.emit(EventType.STAGE, {"stage": Stage.EXECUTING})
        result = await self._run_plan(plan, user_input)

        self.bus.emit(EventType.STAGE, {"stage": Stage.OBSERVING})

        # Generate a final natural-language summary using the streaming path.
        self.bus.emit(EventType.STAGE, {"stage": Stage.GENERATING})
        summary_prompt = (
            f"Summarize the outcome of this completed task for the user, "
            f"in a friendly tone. Task: {user_input}\n\n"
            f"Result: {result}"
        )
        response = await self._stream_chat_answer(summary_prompt, inject_system=False)

        self.bus.emit(EventType.STAGE, {"stage": Stage.COMPLETE})
        self.bus.emit(EventType.ASSISTANT_MESSAGE, {"content": response})
        return response

    async def _build_plan(self, goal: str) -> dict[str, Any] | None:
        """Build a plan using the existing Planner if available."""
        planner = getattr(self.agent, "planner", None)
        if planner is None:
            return None
        try:
            context = ""
            try:
                context = self.agent.memory.format_for_prompt()
            except Exception:
                context = ""
            plan_obj = await planner.create_plan(goal, context)
            steps = []
            for s in getattr(plan_obj, "steps", []):
                steps.append(
                    {
                        "step": getattr(s, "step", 0),
                        "tool": getattr(s, "tool", ""),
                        "description": getattr(s, "description", ""),
                        "critical": getattr(s, "critical", True),
                    }
                )
            if not steps:
                return None
            return {"goal": getattr(plan_obj, "goal", goal), "steps": steps}
        except Exception as e:
            logger.warning(f"Planning failed, falling back: {e}")
            return None

    async def _run_plan(self, plan: dict[str, Any], goal: str) -> str:
        """Execute a plan, emitting step + tool + observing events."""
        executor = getattr(self.agent, "executor", None)
        completed: list[str] = []
        failed_step: str | None = None

        if executor is None:
            return "(planner available but executor unavailable)"

        for step in plan["steps"]:
            if self._interrupted():
                self.bus.emit(EventType.VOICE_INTERRUPT, {"reason": "user_speech"})
                return "Stopped — I heard you speak."

            self.bus.emit(
                EventType.STEP,
                {
                    "phase": "start",
                    "step": step["step"],
                    "tool": step["tool"],
                    "description": step["description"],
                },
            )

            try:
                res = await executor.execute(step["tool"], step["parameters"])
                ok = getattr(res, "success", False)
            except Exception as e:
                ok = False
                res = type("R", (), {"success": False, "error": str(e)})()

            self.bus.emit(
                EventType.STEP,
                {
                    "phase": "complete" if ok else "error",
                    "step": step["step"],
                    "tool": step["tool"],
                    "description": step["description"],
                    "success": bool(ok),
                    "error": getattr(res, "error", None),
                },
            )

            if ok:
                completed.append(step["description"])
            else:
                failed_step = step["description"]
                # Auto-retry once on the same step (Feature 6: retry reasonable failures)
                retried = await self._retry_step(step)
                if retried:
                    completed.append(step["description"])
                    failed_step = None
                else:
                    break

        self.bus.emit(
            EventType.OBSERVING,
            {
                "completed": completed,
                "failed": failed_step,
            },
        )

        if failed_step:
            return f"Completed {len(completed)} step(s). Failed at: {failed_step}."
        return f"Completed all {len(completed)} step(s) for: {goal}"

    async def _retry_step(self, step: dict[str, Any]) -> bool:
        """Retry a failed step once (reasonable auto-retry)."""
        executor = getattr(self.agent, "executor", None)
        if executor is None:
            return False
        try:
            await asyncio.sleep(0.5)
            res = await executor.execute(step["tool"], step["parameters"])
            return bool(getattr(res, "success", False))
        except Exception:
            return False

    async def _stream_chat_answer(
        self,
        prompt: str,
        inject_system: bool = True,
    ) -> str:
        """
        Generate a chat answer, streaming tokens to the bus (Feature 7).

        Uses the provider manager streaming path when available; otherwise
        falls back to the agent's existing non-streaming answer and emits it
        as one block.
        """
        # Try streaming via the provider manager / LLM client first.
        chunks = []
        streamed = False
        try:
            stream = self._open_stream(prompt, inject_system)
            if stream is not None:
                async for token in stream:
                    if not token:
                        continue
                    streamed = True
                    chunks.append(token)
                    self.bus.emit(EventType.TOKEN, {"token": token})
                    if self._interrupted():
                        break
        except Exception as e:
            logger.debug(f"Streaming path failed, fallback to non-streaming: {e}")
            streamed = False

        if streamed:
            return "".join(chunks).strip()

        # Fallback: existing agent answer (still wrapper, no backend change).
        try:
            response = await self.agent.answer_query(prompt)
        except Exception as e:
            friendly = handle_error(e, context="answering")
            self.bus.emit(EventType.ERROR, friendly.to_dict())
            return friendly.reason
        if response:
            self.bus.emit(EventType.TOKEN, {"token": response})
        return response

    def _open_stream(self, prompt: str, inject_system: bool) -> AsyncIterator[str] | None:
        """
        Get an async token iterator from the provider stack if one exists.
        Returns None when streaming is unavailable so callers can fall back.
        """
        # Prefer the provider manager (has stream_generate with fallback).
        try:
            from jarvis.api.providers import get_provider_manager

            manager = get_provider_manager()
            system = (
                self.agent._build_system_prompt()
                if (inject_system and hasattr(self.agent, "_build_system_prompt"))
                else ""
            )
            # Build a messages payload accepted by stream_generate callers.
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # ProviderManager.stream_generate takes a flat prompt; synthesize.
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\nUser: {prompt}"
            return manager.stream_generate(full_prompt)
        except Exception as e:
            logger.debug(f"No provider streaming available: {e}")

        # Fallback to SimpleLLMClient if it gains streaming later.
        client = getattr(self.agent, "llm", None)
        if client is not None and hasattr(client, "stream_generate"):
            try:
                return client.stream_generate(prompt=prompt)
            except Exception:
                return None
        return None

    def _interrupted(self) -> bool:
        if self._interrupt_event is None:
            return False
        try:
            return self._interrupt_event.is_set()
        except Exception:
            return False
