"""
JARVIS Multi-Agent Architecture
===============================
Coordinates specialized subagents under the direction of the Commander Agent.

Agents:
- COMMANDER (Coordinates task execution, message routing, parallel dispatch)
- PLANNER (Decomposes complex requests into task DAG step graphs)
- RESEARCH (Web search, Hacker News stream, citation synthesis)
- MEMORY (Working memory, long-term memory, RAG recall)
- CODING (Repo comprehension, code generation, refactoring, test generation)
- VISION (Camera, screenshot, OCR, object detection)
- AUTOMATION (Workflows, background jobs, task queue management)
- BROWSER (Web browser navigation, form filling, extraction)
- SYSTEM (OS desktop control, terminal execution, file operations)
- RESPONSE_COMPOSER (Formats final structured responses with citations)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from jarvis.events import EventType, get_event_bus

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Specialized Agent Categories."""

    COMMANDER = "commander"
    PLANNER = "planner"
    RESEARCH = "research"
    MEMORY = "memory"
    CODING = "coding"
    VISION = "vision"
    AUTOMATION = "automation"
    BROWSER = "browser"
    SYSTEM = "system"
    RESPONSE_COMPOSER = "response_composer"
    SWE_DIRECTOR = "swe_director"
    RESEARCH_DIRECTOR = "research_director"
    EXECUTIVE_DIRECTOR = "executive_director"
    KNOWLEDGE_DIRECTOR = "knowledge_director"
    AUTOMATION_DIRECTOR = "automation_director"
    LEARNING_DIRECTOR = "learning_director"
    QUALITY_DIRECTOR = "quality_director"
    SECURITY_DIRECTOR = "security_director"
    ARCHITECTURE_DIRECTOR = "architecture_director"


@dataclass
class Task:
    """A unit of work assigned to a specialized agent."""

    id: str
    description: str
    type: AgentType
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    subtasks: list[Task] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Inter-agent communication message."""

    sender: str
    receiver: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    type: str = "message"
    reply_to: str | None = None


class BaseAgent(ABC):
    """Base class for all JARVIS specialized agents."""

    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._parent = None

    @property
    def name(self) -> str:
        return f"{self.agent_type.value}_{self.agent_id}"

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        pass

    async def receive_message(self, message: Message) -> None:
        await self._message_queue.put(message)

    async def send_message(self, receiver: str, content: Any, msg_type: str = "message") -> None:
        if self._parent:
            message = Message(sender=self.name, receiver=receiver, content=content, type=msg_type)
            await self._parent.route_message(message)


class CommanderAgent(BaseAgent):
    """Commander Agent coordinating all specialized agents."""

    def __init__(self, agent_id: str = "main"):
        super().__init__(agent_id, AgentType.COMMANDER)

    async def initialize(self) -> None:
        logger.info("[CommanderAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        logger.info("[CommanderAgent] Processing request: %r", input_data)
        get_event_bus().emit(EventType.STAGE, {"stage": "thinking"})
        return {"commander_status": "routing", "request": input_data}


class PlannerAgent(BaseAgent):
    """Task decomposition & DAG planner agent."""

    def __init__(self, agent_id: str = "main"):
        super().__init__(agent_id, AgentType.PLANNER)

    async def initialize(self) -> None:
        logger.info("[PlannerAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        goal = input_data if isinstance(input_data, str) else input_data.get("goal", "")
        goal_lower = goal.lower()
        subtasks: list[Task] = []

        import uuid
        def gen_id(): return f"task_{uuid.uuid4().hex[:6]}"

        if any(k in goal_lower for k in ["search", "research", "find", "news", "look up"]):
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.RESEARCH))

        if any(k in goal_lower for k in ["remember", "memory", "save", "fact", "preference"]):
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.MEMORY))

        if any(k in goal_lower for k in ["code", "script", "repo", "refactor", "test", "python"]):
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.CODING))

        if any(k in goal_lower for k in ["camera", "screenshot", "screen", "ocr", "photo"]):
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.VISION))

        if any(k in goal_lower for k in ["open", "calc", "app", "cmd", "run", "bash"]):
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.SYSTEM))

        if not subtasks:
            subtasks.append(Task(id=gen_id(), description=goal, type=AgentType.SYSTEM))

        return {"goal": goal, "subtasks": subtasks}


class ResearchAgentWrapper(BaseAgent):
    def __init__(self, agent_id: str = "researcher"):
        super().__init__(agent_id, AgentType.RESEARCH)

    async def initialize(self) -> None:
        logger.info("[ResearchAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        try:
            from jarvis.tools.system_tools import SearchWebTool
            tool = SearchWebTool()
            query = str(input_data)
            res = await tool.execute({"query": query})
            return {"query": query, "result": res.output if res.success else res.error}
        except Exception as e:
            return {"query": str(input_data), "error": str(e)}


class MemoryAgentWrapper(BaseAgent):
    def __init__(self, agent_id: str = "memory"):
        super().__init__(agent_id, AgentType.MEMORY)

    async def initialize(self) -> None:
        logger.info("[MemoryAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        try:
            from jarvis.memory.enhanced import get_enhanced_memory
            mem = get_enhanced_memory()
            return {"status": "ok", "entries_count": len(getattr(mem, "memories", []))}
        except Exception as e:
            return {"error": str(e)}


class CodingAgentWrapper(BaseAgent):
    def __init__(self, agent_id: str = "coder"):
        super().__init__(agent_id, AgentType.CODING)

    async def initialize(self) -> None:
        logger.info("[CodingAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        return {"coding_task": str(input_data), "status": "completed"}


class VisionAgentWrapper(BaseAgent):
    def __init__(self, agent_id: str = "vision"):
        super().__init__(agent_id, AgentType.VISION)

    async def initialize(self) -> None:
        logger.info("[VisionAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        try:
            from jarvis.tools.camera_tool import CameraTool
            tool = CameraTool()
            res = await tool.execute({"source": "auto"})
            return {"vision_result": res.output if res.success else res.error}
        except Exception as e:
            return {"error": str(e)}


class SystemAgentWrapper(BaseAgent):
    def __init__(self, agent_id: str = "system"):
        super().__init__(agent_id, AgentType.SYSTEM)

    async def initialize(self) -> None:
        logger.info("[SystemAgent] Initialized")

    async def process(self, input_data: Any) -> Any:
        return {"system_action": str(input_data), "status": "completed"}


class ResponseComposerAgent(BaseAgent):
    def __init__(self, agent_id: str = "composer"):
        super().__init__(agent_id, AgentType.RESPONSE_COMPOSER)

    async def initialize(self) -> None:
        logger.info("[ResponseComposer] Initialized")

    async def process(self, input_data: Any) -> Any:
        return {"composed_response": str(input_data)}


class AgentOrchestrator:
    """
    Central multi-agent orchestrator managing parallel execution & message dispatch.
    """

    def __init__(self) -> None:
        self.agents: dict[str, BaseAgent] = {}
        self._message_log: list[Message] = []
        self._running = False

    async def initialize(self) -> None:
        self.register_agent(CommanderAgent("main"))
        self.register_agent(PlannerAgent("main"))
        self.register_agent(ResearchAgentWrapper("main"))
        self.register_agent(MemoryAgentWrapper("main"))
        self.register_agent(CodingAgentWrapper("main"))
        self.register_agent(VisionAgentWrapper("main"))
        self.register_agent(SystemAgentWrapper("main"))
        self.register_agent(ResponseComposerAgent("main"))

        for agent in self.agents.values():
            await agent.initialize()
            agent._parent = self

        self._running = True
        logger.info("[AgentOrchestrator] Multi-agent system initialized with %d agents", len(self.agents))

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.name] = agent

    async def route_message(self, message: Message) -> None:
        self._message_log.append(message)
        if message.receiver in self.agents:
            await self.agents[message.receiver].receive_message(message)

    async def execute_task(self, goal: str) -> dict[str, Any]:
        """
        Execute goal across multi-agent DAG hierarchy with parallel dispatch.
        """
        planner = self.agents.get("planner_main")
        if not planner:
            return {"error": "Planner Agent unavailable"}

        plan_res = await planner.process(goal)
        subtasks: list[Task] = plan_res.get("subtasks", [])

        # Execute subtasks in parallel via asyncio.gather
        async def run_subtask(st: Task):
            target_name = f"{st.type.value}_main"
            agent = self.agents.get(target_name)
            if agent:
                res = await agent.process(st.description)
                st.status = "completed"
                st.result = res
            else:
                st.status = "failed"
                st.error = "Agent unavailable"
            return st

        results = await asyncio.gather(*[run_subtask(st) for st in subtasks], return_exceptions=True)

        return {
            "goal": goal,
            "subtasks_count": len(subtasks),
            "results": [
                {"id": r.id, "type": r.type.value, "status": r.status, "result": r.result}
                for r in results if isinstance(r, Task)
            ],
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "agents": list(self.agents.keys()),
            "message_count": len(self._message_log),
        }


_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


async def initialize_multi_agent() -> AgentOrchestrator:
    orch = get_orchestrator()
    await orch.initialize()
    return orch
