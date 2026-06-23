"""
Session memory for JARVIS - in-memory conversation history.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: Optional[str] = None
    tool_result: Optional[str] = None


class SessionMemory:
    """
    In-memory session memory for current conversation context.
    Adapted from Claude Code's session history pattern.
    """

    MAX_MESSAGES = 100
    MAX_TOKEN_ESTIMATE = 8000

    def __init__(self):
        self.messages: List[Message] = []
        self._message_count = 0

    def add_user_message(self, content: str) -> None:
        """Add a user message to the session."""
        self.messages.append(Message(role="user", content=content))
        self._trim_if_needed()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the session."""
        self.messages.append(Message(role="assistant", content=content))
        self._trim_if_needed()

    def add_tool_message(self, tool_name: str, tool_result: str) -> None:
        """Add a tool result message to the session."""
        self.messages.append(Message(
            role="tool",
            content=f"[{tool_name}] {tool_result}",
            tool_name=tool_name,
            tool_result=tool_result
        ))
        self._trim_if_needed()

    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get the N most recent messages."""
        return self.messages[-count:] if self.messages else []

    def get_all_messages(self) -> List[Message]:
        """Get all messages in the session."""
        return self.messages.copy()

    def get_context_string(self, max_messages: int = 20) -> str:
        """Get a formatted string of recent conversation context."""
        messages = self.get_recent_messages(max_messages)

        if not messages:
            return ""

        lines = []
        for msg in messages:
            if msg.role == "user":
                lines.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                lines.append(f"Assistant: {msg.content}")
            elif msg.role == "tool":
                lines.append(f"Tool ({msg.tool_name}): {msg.tool_result}")

        return "\n".join(lines)

    def _trim_if_needed(self):
        """Trim old messages if memory exceeds limits."""
        self._message_count += 1

        # Trim by count
        while len(self.messages) > self.MAX_MESSAGES:
            # Remove oldest non-essential messages
            for i, msg in enumerate(self.messages):
                if msg.role != "system":
                    self.messages.pop(i)
                    break

        # Simple token estimation (rough: 4 chars = 1 token)
        estimated_tokens = sum(len(m.content) for m in self.messages) // 4
        while estimated_tokens > self.MAX_TOKEN_ESTIMATE and len(self.messages) > 10:
            # Keep first (system) and last few messages
            self.messages.pop(1)
            estimated_tokens = sum(len(m.content) for m in self.messages) // 4

    def clear(self) -> None:
        """Clear all session messages."""
        self.messages.clear()
        self._message_count = 0

    def get_history_summary(self) -> Dict[str, Any]:
        """Get a summary of the session history."""
        return {
            "total_messages": len(self.messages),
            "user_messages": sum(1 for m in self.messages if m.role == "user"),
            "assistant_messages": sum(1 for m in self.messages if m.role == "assistant"),
            "tool_calls": sum(1 for m in self.messages if m.role == "tool"),
        }
