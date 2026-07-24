"""
Intelligent Reasoning Pipeline.

Replaces simple request-response with a multi-stage pipeline:
Intent Detection → Capability Discovery → Memory Recall → Goal Analysis →
Planning → Agent Selection → Tool Selection → Execution → Self Review →
Reflection → Memory Update → Response Generation
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.agent import JarvisAgent, classify_intent
from jarvis.core.capabilities import get_capability_discovery
from jarvis.events import EventBus, EventType, Stage, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Context object passed through pipeline stages."""

    user_input: str
    intent: str | None = None
    capabilities: Any | None = None
    goal: Any | None = None
    plan: Any | None = None
    agent_name: str | None = None
    tool_names: list[str] = field(default_factory=list)
    result: Any | None = None
    response: str | None = None
    review: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IntelligentReasoningPipeline:
    """
    Multi-stage reasoning pipeline for JARVIS.

    Composes existing components and adds missing stages:
    - capability discovery
    - goal analysis
    - agent selection
    - self review
    - reflection
    """

    def __init__(self, agent: JarvisAgent | None = None, bus: EventBus | None = None):
        self.agent = agent
        self.bus = bus or get_event_bus()
        self.capabilities = get_capability_discovery()
        self._review_prompts = True

    async def run(self, user_input: str, goal: Any = None) -> str:
        ctx = PipelineContext(user_input=user_input, goal=goal)
        self._emit(Stage.THINKING)

        try:
            await self._detect_intent(ctx)
            await self._discover_capabilities(ctx)
            await self._recall_memory(ctx)
            await self._analyze_goal(ctx)
            await self._plan(ctx)
            await self._select_agent(ctx)
            await self._select_tools(ctx)
            await self._execute(ctx)
            await self._self_review(ctx)
            await self._reflect(ctx)
            await self._update_memory(ctx)
            response = await self._generate_response(ctx)
            ctx.response = response
            return response
        except Exception as exc:
            logger.warning("Pipeline error: %s", exc, exc_info=True)
            ctx.response = f"I hit an issue: {exc}. Falling back to direct chat."
            return ctx.response

    async def _detect_intent(self, ctx: PipelineContext) -> None:
        self._emit(Stage.PLANNING)
        ctx.intent = classify_intent(ctx.user_input)
        ctx.metadata["intent"] = ctx.intent

    async def _discover_capabilities(self, ctx: PipelineContext) -> None:
        try:
            caps = await self.capabilities.discover(getattr(self.agent, "tools", None))
            ctx.capabilities = caps
            ctx.metadata["providers"] = len(caps.providers)
            ctx.metadata["tools"] = len(caps.tools)
        except Exception as exc:
            logger.debug("Capability discovery skipped: %s", exc)

    async def _recall_memory(self, ctx: PipelineContext) -> None:
        if self.agent is None:
            return
        try:
            memory = self.agent.memory.format_for_prompt()
            ctx.metadata["memory_available"] = bool(memory)
        except Exception:
            pass

    async def _analyze_goal(self, ctx: PipelineContext) -> None:
        if ctx.goal is not None:
            ctx.metadata["goal_key"] = getattr(ctx.goal, "key", None)
            ctx.metadata["goal_status"] = getattr(ctx.goal, "status", None)

    async def _plan(self, ctx: PipelineContext) -> None:
        planner = getattr(self.agent, "planner", None)
        if planner is None:
            return
        try:
            context = ""
            if self.agent is not None:
                context = self.agent.memory.format_for_prompt()
            plan_obj = await planner.create_plan(ctx.user_input, context)
            ctx.plan = plan_obj
        except Exception as exc:
            logger.debug("Planning skipped: %s", exc)

    async def _select_agent(self, ctx: PipelineContext) -> None:
        try:
            from jarvis.core.agent_registry import get_agent_registry

            registry = get_agent_registry()
            hits = registry.search(ctx.user_input)
            if hits:
                ctx.agent_name = hits[0].name
        except Exception:
            pass

    async def _select_tools(self, ctx: PipelineContext) -> None:
        registry = getattr(self.agent, "tools", None)
        if registry is None:
            return
        try:
            names = registry.list_names()
            ctx.tool_names = names[:10]
        except Exception:
            pass

    async def _execute(self, ctx: PipelineContext) -> None:
        if self.agent is None:
            return
        try:
            goal_arg = ctx.goal if hasattr(ctx, "goal") else None
            result = await self.agent.process(ctx.user_input, goal=goal_arg)
            ctx.result = result
        except Exception as exc:
            ctx.result = f"(execution error: {exc})"

    async def _self_review(self, ctx: PipelineContext) -> None:
        if not ctx.result or not self._review_prompts:
            return
        try:
            response = str(ctx.result)
            ctx.review = {
                "success": True,
                "length": len(response),
                "has_error": "error" in response.lower(),
                "intent_matched": ctx.intent is not None,
            }
        except Exception:
            ctx.review = {"success": False}

    async def _reflect(self, ctx: PipelineContext) -> None:
        if ctx.review is None:
            return
        try:
            from jarvis.events import EventType

            self.bus.emit(
                EventType.STAGE,
                {
                    "stage": Stage.COMPLETE,
                    "intent": ctx.intent,
                    "agent": ctx.agent_name,
                    "review": ctx.review,
                },
            )
        except Exception:
            pass

    async def _update_memory(self, ctx: PipelineContext) -> None:
        if self.agent is None or not ctx.user_input or not ctx.response:
            return
        try:
            if hasattr(self.agent.memory, "extract_conversation_facts"):
                self.agent.memory.extract_conversation_facts(ctx.user_input, ctx.response)
        except Exception:
            pass

    async def _generate_response(self, ctx: PipelineContext) -> str:
        if ctx.result:
            return str(ctx.result)
        if self.agent is not None:
            return await self.agent.process(ctx.user_input)
        return "I couldn't process that request."

    def _emit(self, stage: str) -> None:
        with contextlib.suppress(Exception):
            self.bus.emit(EventType.STAGE, {"stage": stage})


def get_reasoning_pipeline(agent: JarvisAgent | None = None) -> IntelligentReasoningPipeline:
    return IntelligentReasoningPipeline(agent=agent)
