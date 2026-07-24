"""
Master Agent (JARVIS Core).

All user interactions flow through the Master Agent.
It wraps JarvisAgent, threads Goal context through the pipeline,
and seamlessly routes through AGW Directors when appropriate.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.core.agent import JarvisAgent, create_jarvis
from jarvis.core.goal import Goal

logger = logging.getLogger(__name__)


class MasterAgent:
    """
    Facade that enforces all user interactions flow through JARVIS Core.

    Wraps JarvisAgent and adds:
    - Goal-aware orchestration
    - Unified entry point for all UIs
    - AGW Director routing for complex workflows
    """

    def __init__(self, agent: JarvisAgent | None = None):
        self._agent = agent or create_jarvis()
        self._current_goal: Goal | None = None
        self._agw: Any = None

    async def _get_agw(self) -> Any:
        if self._agw is None:
            try:
                from jarvis.agw.orchestrator import (
                    get_agw_orchestrator,  # type: ignore[attr-defined]
                )
                agw = get_agw_orchestrator()
                await agw.initialize()
                self._agw = agw
            except Exception:
                self._agw = None
        return self._agw

    def set_goal(self, goal: Goal | None) -> None:
        self._current_goal = goal

    def get_goal(self) -> Goal | None:
        return self._current_goal

    async def process(self, user_input: str, goal: Goal | None = None) -> str:
        if goal is not None:
            self._current_goal = goal

        agw = await self._get_agw()
        if agw:
            lowered = user_input.lower()
            director_keywords = {
                "software_engineering": ["code", "repo", "refactor", "bug", "pull request", "repository", "architecture", "deploy"],
                "research": ["research", "paper", "find", "search", "compare", "evaluate"],
                "executive": ["goal", "schedule", "deadline", "plan", "roadmap", "brief"],
                "knowledge": ["knowledge", "graph", "connect", "synthesize", "memory"],
                "learning": ["learn", "study", "skill gap", "training", "book"],
                "automation": ["automate", "schedule", "script", "recurring"],
                "quality": ["benchmark", "test coverage", "performance", "regression"],
                "security": ["security", "audit", "secret", "audit", "encryption"],
                "architecture": ["diagram", "design", "system", "workflow", "pipeline"],
            }
            matched_domain = None
            for domain, keywords in director_keywords.items():
                if any(k in lowered for k in keywords):
                    matched_domain = domain
                    break
            if matched_domain:
                try:
                    director = agw.get_director(matched_domain)
                    if director:
                        exec_result = await director.execute(user_input, {"task": matched_domain})
                        status = exec_result.get("status", "completed")
                        if status == "completed":
                            artifacts = exec_result.get("report", exec_result.get("brief", exec_result))
                            if isinstance(artifacts, dict):
                                return str(artifacts)
                            return str(artifacts)
                except Exception:
                    pass

        return await self._agent.process(user_input, goal=goal)

    def request_interrupt(self) -> None:
        if self._agent:
            self._agent.request_interrupt()

    def clear_interrupt(self) -> None:
        if self._agent:
            self._agent.clear_interrupt()

    def set_speak_callback(self, callback) -> None:
        if self._agent:
            self._agent.set_speak_callback(callback)

    def add_message_handler(self, handler) -> None:
        if self._agent:
            self._agent.add_message_handler(handler)

    def activate_agw(self) -> Any:
        """Explicitly activate AGW mode and return the orchestrator."""
        try:
            from jarvis.agw.orchestrator import get_agw_orchestrator  # type: ignore[attr-defined]
            agw = get_agw_orchestrator()
            import asyncio
            asyncio.get_event_loop().run_until_complete(agw.initialize())
            self._agw = agw
            return agw
        except Exception:
            return None

    def start_work_session(self, project_path: str | None = None) -> dict[str, Any]:
        """Start an AGW Work Session."""
        import asyncio
        agw = self.activate_agw()
        if agw:
            return asyncio.get_event_loop().run_until_complete(agw.start_work_session(project_path))
        return {}

    def end_work_session(self) -> None:
        agw = self.activate_agw()
        if agw:
            agw.end_work_session()

    @property
    def current_goal(self) -> Goal | None:
        return self._current_goal

    @property
    def agw_status(self) -> dict[str, Any]:
        if self._agw:
            return self._agw.get_status()
        return {"initialized": False, "running": False}


def create_master_agent(config=None, api_key=None):
    """Create a configured Master Agent."""
    agent = create_jarvis(config=config, api_key=api_key)
    return MasterAgent(agent=agent)
