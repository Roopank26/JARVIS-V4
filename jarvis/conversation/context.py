"""
Conversation Context for JARVIS.
Maintains turn-based conversation state, topic tracking, and context
resolution for follow-up queries.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    INTERRUPTED = "interrupted"
    PAUSED = "paused"


class ResolvedReference:
    def __init__(self, kind: str, target: str | None, confidence: float = 1.0):
        self.kind = kind
        self.target = target
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"ResolvedReference(kind={self.kind!r}, target={self.target!r})"


@dataclass
class Turn:
    turn_id: str
    role: str
    content: str
    intent: str | None = None
    timestamp: float = field(default_factory=time.time)
    resolved: dict[str, Any] | None = None
    tool_calls: list[str] = field(default_factory=list)


class ConversationContext:
    MAX_TURNS = 40

    def __init__(self):
        self._turns: list[Turn] = []
        self._state = ConversationState.IDLE
        self._current_topic: str | None = None
        self._references: dict[str, ResolvedReference] = {}
        self._last_user_input: str | None = None
        self._last_assistant_output: str | None = None
        self._active_tool: str | None = None
        self._lock = asyncio.Lock()

    def add_turn(self, role: str, content: str, intent: str | None = None) -> Turn:
        turn = Turn(
            turn_id=uuid.uuid4().hex[:8],
            role=role,
            content=content,
            intent=intent,
        )
        self._turns.append(turn)
        if len(self._turns) > self.MAX_TURNS:
            self._turns = self._turns[-self.MAX_TURNS :]
        if role == "user":
            self._last_user_input = content
        else:
            self._last_assistant_output = content
        return turn

    def get_recent_turns(self, n: int = 10) -> list[Turn]:
        return list(self._turns[-n:])

    def get_recent_user_messages(self, n: int = 5) -> list[Turn]:
        return [t for t in self._turns if t.role == "user"][-n:]

    def get_last_user_message(self) -> Turn | None:
        for turn in reversed(self._turns):
            if turn.role == "user":
                return turn
        return None

    def get_recent_assistant_messages(self, n: int = 5) -> list[Turn]:
        return [t for t in self._turns if t.role == "assistant"][-n:]

    def set_topic(self, topic: str | None):
        self._current_topic = topic

    def get_topic(self) -> str | None:
        return self._current_topic

    def add_reference(self, token: str, ref: ResolvedReference):
        self._references[token.lower()] = ref

    def resolve_reference(self, token: str) -> ResolvedReference | None:
        return self._references.get(token.lower())

    def set_active_tool(self, tool: str | None):
        self._active_tool = tool

    def get_active_tool(self) -> str | None:
        return self._active_tool

    def mark_turn_tool_call(self, turn_id: str, tool_name: str):
        for turn in reversed(self._turns):
            if turn.turn_id == turn_id:
                turn.tool_calls.append(tool_name)
                break

    def set_state(self, state: ConversationState):
        self._state = state

    def get_state(self) -> ConversationState:
        return self._state

    def to_prompt_context(self, max_turns: int = 8) -> str:
        turns = self.get_recent_turns(max_turns)
        lines: list[str] = []
        for turn in turns:
            role = "You" if turn.role == "user" else "JARVIS"
            lines.append(f"{role}: {turn.content}")
        if self._current_topic:
            lines.append(f"[Current topic: {self._current_topic}]")
        return "\n".join(lines)

    def clear(self):
        self._turns.clear()
        self._state = ConversationState.IDLE
        self._current_topic = None
        self._references.clear()
        self._last_user_input = None
        self._last_assistant_output = None
        self._active_tool = None
