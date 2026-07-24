"""
Unified memory manager for JARVIS.
Combines session and long-term memory systems.
"""

from pathlib import Path
from typing import Any

from jarvis.memory.base import MemoryBase, MemoryCategory
from jarvis.memory.knowledge_graph import KnowledgeGraph
from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.session import SessionMemory


class MemoryManager(MemoryBase):
    """
    Unified memory system combining:
    - Session memory (in-memory, current conversation)
    - Long-term memory (persistent JSON, across sessions)
    """

    def __init__(self, memory_path: Path | None = None, knowledge_graph: KnowledgeGraph | None = None):
        self.session = SessionMemory()
        self.long_term = LongTermMemory(memory_path, knowledge_graph=knowledge_graph)

    def remember(self, key: str, value: Any, category: str = "general") -> None:
        """Store information in long-term memory."""
        self.long_term.remember(key, value, category)

    def recall(self, query: str) -> list[dict[str, Any]]:
        """Recall from long-term memory based on query."""
        return self.long_term.recall(query)

    def forget(self, key: str, category: str = "general") -> bool:
        """Remove information from long-term memory."""
        return self.long_term.forget(key, category)

    def format_for_prompt(self) -> str:
        """Format memory as a string for inclusion in prompts."""
        return self.long_term.format_for_prompt()

    def clear(self) -> None:
        """Clear all memory (both session and long-term)."""
        self.session.clear()
        self.long_term.clear()

    # Session-specific methods
    def add_user_message(self, content: str) -> None:
        """Add a user message to session history."""
        self.session.add_user_message(content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to session history."""
        self.session.add_assistant_message(content)

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add a tool result to session history."""
        self.session.add_tool_message(tool_name, result)

    def get_context(self, max_messages: int = 20) -> str:
        """Get formatted conversation context."""
        return self.session.get_context_string(max_messages)

    def get_rolling_summary(self) -> str:
        """Get the rolling summary of older session messages."""
        return getattr(self.session, "_rolling_summary", "")

    def get_history_summary(self) -> dict[str, Any]:
        """Get summary of session history."""
        return self.session.get_history_summary()

    # Long-term specific methods
    def update_identity(self, key: str, value: Any) -> bool:
        """Quick update for identity facts."""
        return self.long_term.remember(key, value, MemoryCategory.IDENTITY)

    def update_preference(self, key: str, value: Any) -> bool:
        """Quick update for preferences."""
        return self.long_term.remember(key, value, MemoryCategory.PREFERENCES)

    def update_project(self, key: str, value: Any) -> bool:
        """Quick update for projects."""
        return self.long_term.remember(key, value, MemoryCategory.PROJECTS)

    def get_identity(self) -> dict[str, Any]:
        """Get identity information."""
        return self.long_term.get_identity()

    def get_preferences(self) -> dict[str, Any]:
        """Get user preferences."""
        return self.long_term.get_preferences()

    def get_projects(self) -> dict[str, Any]:
        """Get user projects."""
        return self.long_term.get_projects()

    # Goal-specific methods
    def save_goal(
        self,
        key: str,
        value: Any,
        status: str = "active",
        priority: str = "medium",
        dependencies: str = "",
        estimated_completion: str = "",
        subgoals: str = "",
    ) -> bool:
        """Store a goal in long-term memory."""
        return self.long_term.save_goal(
            key=key,
            value=value,
            status=status,
            priority=priority,
            dependencies=dependencies,
            estimated_completion=estimated_completion,
            subgoals=subgoals,
        )

    def get_goal(self, key: str) -> dict[str, Any] | None:
        """Get a specific goal."""
        return self.long_term.get_goal(key)

    def get_goals(self) -> dict[str, Any]:
        """Get all goals."""
        return self.long_term.get_goals()

    def get_goals_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get goals filtered by status."""
        return self.long_term.get_goals_by_status(status)

    def get_current_goal(self) -> dict[str, Any] | None:
        """Get the current active goal."""
        return self.long_term.get_current_goal()

    def update_goal_status(self, key: str, status: str) -> bool:
        """Update a goal's status."""
        return self.long_term.update_goal_status(key, status)

    def get_goal_context(self) -> str:
        """Format goals for inclusion in prompts."""
        return self.long_term.format_goals_for_prompt()

    def get_full_memory(self) -> dict[str, dict]:
        """Get the full long-term memory structure."""
        return self.long_term.load()


# Global memory manager instance
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def init_memory_manager(memory_path: Path | None = None) -> MemoryManager:
    """Initialize the global memory manager."""
    global _memory_manager
    _memory_manager = MemoryManager(memory_path)
    return _memory_manager
