"""
Memory base classes for JARVIS.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime


class MemoryBase(ABC):
    """Abstract base class for all memory types."""

    @abstractmethod
    def remember(self, key: str, value: Any, category: str = "general") -> None:
        """Store information in memory."""
        pass

    @abstractmethod
    def recall(self, query: str) -> list:
        """Recall information from memory based on a query."""
        pass

    @abstractmethod
    def forget(self, key: str, category: str = "general") -> bool:
        """Remove information from memory."""
        pass

    @abstractmethod
    def format_for_prompt(self) -> str:
        """Format memory as a string for inclusion in prompts."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all memory."""
        pass


class MemoryEntry:
    """Represents a single memory entry."""

    def __init__(self, key: str, value: Any, category: str = "general",
                 timestamp: Optional[str] = None):
        self.key = key
        self.value = value
        self.category = category
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "value": str(self.value),
            "category": self.category,
            "updated": self.timestamp
        }

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "MemoryEntry":
        return cls(
            key=key,
            value=data.get("value", ""),
            category=data.get("category", "general"),
            timestamp=data.get("updated")
        )


class MemoryCategory:
    """Standard memory categories."""

    IDENTITY = "identity"
    PREFERENCES = "preferences"
    PROJECTS = "projects"
    RELATIONSHIPS = "relationships"
    WISHES = "wishes"
    NOTES = "notes"
    GENERAL = "general"

    ALL = [IDENTITY, PREFERENCES, PROJECTS, RELATIONSHIPS, WISHES, NOTES, GENERAL]
