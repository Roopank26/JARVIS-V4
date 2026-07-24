"""
Goal model for JARVIS.

Represents a user goal with metadata that flows through the
planning, execution, and memory systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class GoalStatus(StrEnum):
    """Status of a goal."""

    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GoalPriority(StrEnum):
    """Priority of a goal."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Goal:
    """Represents a user goal with tracking metadata."""

    key: str
    value: str
    status: GoalStatus = GoalStatus.ACTIVE
    priority: GoalPriority = GoalPriority.MEDIUM
    subgoals: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_completion: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "subgoals": self.subgoals,
            "dependencies": self.dependencies,
            "estimated_completion": self.estimated_completion,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Goal:
        status = data.get("status", GoalStatus.ACTIVE.value)
        priority = data.get("priority", GoalPriority.MEDIUM.value)
        return cls(
            key=data["key"],
            value=data["value"],
            status=GoalStatus(status) if isinstance(status, str) else status,
            priority=GoalPriority(priority) if isinstance(priority, str) else priority,
            subgoals=data.get("subgoals", []),
            dependencies=data.get("dependencies", []),
            estimated_completion=data.get("estimated_completion"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )
