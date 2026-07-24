"""
JARVIS Multi-Agent System

Coordinates multiple specialized agents for complex tasks.
"""

from jarvis.agents.collaboration import (
    AgentCollaboration,
    CollaborationRequest,
    CollaborationResult,
)
from jarvis.agents.multi_agent import (
    AgentOrchestrator,
    AgentType,
    BaseAgent,
    CodingAgentWrapper,
    MemoryAgentWrapper,
    Message,
    PlannerAgent,
    ResearchAgentWrapper,
    Task,
    get_orchestrator,
    initialize_multi_agent,
)

__all__ = [
    "AgentCollaboration",
    "AgentOrchestrator",
    "AgentType",
    "BaseAgent",
    "CodingAgentWrapper",
    "CollaborationRequest",
    "CollaborationResult",
    "MemoryAgentWrapper",
    "Message",
    "PlannerAgent",
    "ResearchAgentWrapper",
    "Task",
    "get_orchestrator",
    "initialize_multi_agent",
]
