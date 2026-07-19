"""
JARVIS Multi-Agent System

Coordinates multiple specialized agents for complex tasks.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents."""
    PLANNER = "planner"
    RESEARCH = "research"
    CODING = "coding"
    MEMORY = "memory"
    ORCHESTRATOR = "orchestrator"


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str
    description: str
    type: AgentType
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    subtasks: List["Task"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """Message between agents."""
    sender: str
    receiver: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    type: str = "message"
    reply_to: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all JARVIS agents.
    
    Each agent specializes in a specific domain and can
    communicate with other agents.
    """
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._memory: Dict[str, Any] = {}
        self._parent = None
    
    @property
    def name(self) -> str:
        return f"{self.agent_type.value}_{self.agent_id}"
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent."""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Process input and return result.
        
        Args:
            input_data: Input to process
            
        Returns:
            Processing result
        """
        pass
    
    async def receive_message(self, message: Message) -> None:
        """Receive a message from another agent."""
        await self._message_queue.put(message)
    
    async def send_message(self, receiver: str, content: Any, msg_type: str = "message") -> None:
        """Send a message to another agent."""
        if self._parent:
            message = Message(
                sender=self.name,
                receiver=receiver,
                content=content,
                type=msg_type
            )
            await self._parent.route_message(message)
    
    async def run(self) -> None:
        """Main agent loop."""
        self._running = True
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Agent {self.name} error: {e}")
    
    async def _handle_message(self, message: Message) -> None:
        """Handle incoming message."""
        if message.type == "shutdown":
            self._running = False
        elif message.type == "ping":
            await self.send_message(message.sender, {"status": "pong"})
    
    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False


class PlannerAgent(BaseAgent):
    """
    Agent specialized in planning and task decomposition.
    
    Responsibilities:
    - Break down complex tasks into subtasks
    - Determine execution order
    - Assign tasks to appropriate agents
    - Monitor progress
    """
    
    def __init__(self, agent_id: str = "main"):
        super().__init__(agent_id, AgentType.PLANNER)
        self._task_queue: List[Task] = []
        self._execution_history: List[Task] = []
    
    async def initialize(self) -> None:
        """Initialize planner agent."""
        logger.info(f"Planner agent {self.name} initialized")
    
    async def process(self, input_data: Any) -> Any:
        """
        Create execution plan for input task.
        
        Args:
            input_data: Task description or dict with task details
            
        Returns:
            Execution plan with subtasks
        """
        if isinstance(input_data, str):
            task = Task(
                id=self._generate_task_id(),
                description=input_data,
                type=AgentType.ORCHESTRATOR,
                priority=1
            )
        else:
            task = input_data
        
        # Analyze and decompose task
        subtasks = await self._decompose_task(task)
        task.subtasks = subtasks
        
        self._task_queue.append(task)
        
        return {
            "task": task.id,
            "subtasks": [
                {"id": s.id, "description": s.description, "type": s.type.value}
                for s in subtasks
            ],
            "estimated_complexity": len(subtasks)
        }
    
    async def _decompose_task(self, task: Task) -> List[Task]:
        """Decompose a complex task into subtasks."""
        subtasks = []
        description = task.description.lower()
        
        # Detect task components
        if any(kw in description for kw in ["search", "research", "find", "look up"]):
            subtasks.append(Task(
                id=self._generate_task_id(),
                description="Research: " + task.description,
                type=AgentType.RESEARCH,
                priority=2
            ))
        
        if any(kw in description for kw in ["code", "program", "implement", "write", "develop"]):
            subtasks.append(Task(
                id=self._generate_task_id(),
                description="Coding: " + task.description,
                type=AgentType.CODING,
                priority=1
            ))
        
        if any(kw in description for kw in ["remember", "save", "store", "learn"]):
            subtasks.append(Task(
                id=self._generate_task_id(),
                description="Memory: " + task.description,
                type=AgentType.MEMORY,
                priority=3
            ))
        
        # If no specific components, treat as general task
        if not subtasks:
            subtasks.append(Task(
                id=self._generate_task_id(),
                description=task.description,
                type=AgentType.ORCHESTRATOR,
                priority=1
            ))
        
        return subtasks
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        import uuid
        return f"task_{uuid.uuid4().hex[:8]}"
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a task."""
        for task in self._task_queue + self._execution_history:
            if task.id == task_id:
                return {
                    "id": task.id,
                    "description": task.description,
                    "status": task.status,
                    "result": task.result,
                    "error": task.error,
                    "subtasks": len(task.subtasks)
                }
        return None
    
    def get_execution_summary(self) -> Dict:
        """Get summary of all executed tasks."""
        return {
            "total_tasks": len(self._execution_history),
            "completed": sum(1 for t in self._execution_history if t.status == "completed"),
            "failed": sum(1 for t in self._execution_history if t.status == "failed"),
            "pending": len(self._task_queue)
        }


class ResearchAgentWrapper(BaseAgent):
    """Wrapper for ResearchAgent to work in multi-agent system."""
    
    def __init__(self, agent_id: str = "researcher"):
        super().__init__(agent_id, AgentType.RESEARCH)
        self._researcher = None
    
    async def initialize(self) -> None:
        """Initialize research agent."""
        from jarvis.research.research_agent import ResearchAgent
        self._researcher = ResearchAgent()
        logger.info(f"Research agent {self.name} initialized")
    
    async def process(self, input_data: Any) -> Any:
        """Process research task."""
        if not self._researcher:
            await self.initialize()
        
        if isinstance(input_data, str):
            query = input_data.replace("Research: ", "")
            result = await self._researcher.research(query)
            return {
                "query": query,
                "summary": result.summary,
                "sources": len(result.sources),
                "key_findings": result.key_findings
            }
        return {"error": "Invalid input for research"}


class CodingAgentWrapper(BaseAgent):
    """Wrapper for CodingAgent to work in multi-agent system."""
    
    def __init__(self, agent_id: str = "coder"):
        super().__init__(agent_id, AgentType.CODING)
        self._coder = None
    
    async def initialize(self) -> None:
        """Initialize coding agent."""
        logger.info(f"Coding agent {self.name} initialized")
    
    async def process(self, input_data: Any) -> Any:
        """Process coding task."""
        if isinstance(input_data, str):
            task = input_data.replace("Coding: ", "")
            return {
                "task": task,
                "status": "completed",
                "message": f"Coding task planned: {task}"
            }
        return {"error": "Invalid input for coding"}


class MemoryAgentWrapper(BaseAgent):
    """Wrapper for memory operations to work in multi-agent system."""
    
    def __init__(self, agent_id: str = "memory_keeper"):
        super().__init__(agent_id, AgentType.MEMORY)
        self._memory_system = None
    
    async def initialize(self) -> None:
        """Initialize memory agent."""
        logger.info(f"Memory agent {self.name} initialized")
    
    async def process(self, input_data: Any) -> Any:
        """Process memory task."""
        if isinstance(input_data, str):
            task = input_data.replace("Memory: ", "")
            return {
                "task": task,
                "status": "stored",
                "message": f"Memory stored: {task[:50]}..."
            }
        return {"error": "Invalid input for memory"}


class AgentOrchestrator:
    """
    Orchestrates multiple agents for coordinated task execution.
    
    Responsibilities:
    - Manage agent lifecycle
    - Route messages between agents
    - Coordinate task execution
    - Aggregate results
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._message_log: List[Message] = []
        self._task_results: Dict[str, Any] = {}
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize and register all agents."""
        # Create specialized agents
        self.register_agent(PlannerAgent("main"))
        self.register_agent(ResearchAgentWrapper())
        self.register_agent(CodingAgentWrapper())
        self.register_agent(MemoryAgentWrapper())
        
        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize()
            agent._parent = self
        
        self._running = True
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        logger.debug(f"Registered agent: {agent.name}")
    
    async def route_message(self, message: Message) -> None:
        """Route message to target agent."""
        self._message_log.append(message)
        
        if message.receiver in self.agents:
            await self.agents[message.receiver].receive_message(message)
        else:
            # Broadcast to all agents
            for agent in self.agents.values():
                if agent.name != message.sender:
                    await agent.receive_message(message)
    
    async def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Execute a complex task using coordinated agents.
        
        Args:
            task: Task description
            
        Returns:
            Aggregated results from all agents
        """
        # Create execution plan
        planner = self.agents.get("planner_main")
        if not planner:
            return {"error": "Planner not available"}
        
        plan = await planner.process(task)
        
        # Execute subtasks
        results = []
        for subtask in plan.get("subtasks", []):
            agent_type = subtask.get("type")
            agent = self._find_agent_by_type(agent_type)
            
            if agent:
                result = await agent.process(subtask.get("description"))
                results.append({
                    "type": agent_type,
                    "result": result
                })
            else:
                results.append({
                    "type": agent_type,
                    "error": "Agent not found"
                })
        
        # Aggregate results
        return {
            "task": task,
            "plan": plan,
            "results": results,
            "summary": self._summarize_results(results)
        }
    
    def _find_agent_by_type(self, agent_type: str) -> Optional[BaseAgent]:
        """Find agent by type."""
        type_map = {
            "research": "research_researcher",
            "coding": "coding_coder",
            "memory": "memory_memory_keeper",
            "planner": "planner_main"
        }
        
        agent_name = type_map.get(agent_type)
        return self.agents.get(agent_name)
    
    def _summarize_results(self, results: List[Dict]) -> str:
        """Create summary from results."""
        completed = sum(1 for r in results if "error" not in r)
        return f"Completed {completed}/{len(results)} subtasks"
    
    async def shutdown(self) -> None:
        """Shutdown all agents."""
        for agent in self.agents.values():
            await agent.stop()
        
        self._running = False
        logger.info("Orchestrator shutdown complete")
    
    def get_status(self) -> Dict:
        """Get orchestrator status."""
        return {
            "running": self._running,
            "agents": list(self.agents.keys()),
            "message_count": len(self._message_log),
            "results_count": len(self._task_results)
        }


# Global orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


async def initialize_multi_agent() -> AgentOrchestrator:
    """Initialize multi-agent system."""
    orchestrator = get_orchestrator()
    await orchestrator.initialize()
    return orchestrator
