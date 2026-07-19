"""
JARVIS Semantic Memory System
Long-term memory with embeddings for semantic search.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("jarvis.memory.semantic")


class SemanticMemoryCategory(Enum):
    """Categories for semantic memories."""

    PERSON = "person"
    PROJECT = "project"
    GOAL = "goal"
    PREFERENCE = "preference"
    CONVERSATION = "conversation"
    MEETING = "meeting"
    FILE = "file"
    CODE = "code"
    FACT = "fact"
    CUSTOM = "custom"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    content: str
    category: SemanticMemoryCategory
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    importance: float = 1.0  # 0.0 - 1.0
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    embeddings: list[float] | None = None
    relationships: list[str] = field(default_factory=list)  # IDs of related memories

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "importance": self.importance,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "embeddings": self.embeddings,
            "relationships": self.relationships,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            category=SemanticMemoryCategory(data.get("category", "fact")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data.get("updated_at", data["created_at"])),
            importance=data.get("importance", 1.0),
            tags=set(data.get("tags", [])),
            metadata=data.get("metadata", {}),
            embeddings=data.get("embeddings"),
            relationships=data.get("relationships", []),
        )


@dataclass
class MemoryQuery:
    """Query for memory search."""

    text: str
    category: SemanticMemoryCategory | None = None
    tags: set[str] | None = None
    limit: int = 10
    min_importance: float = 0.0
    min_similarity: float = 0.0


@dataclass
class MemorySearchResult:
    """Result from memory search."""

    entry: MemoryEntry
    similarity: float
    matched_on: list[str] = field(default_factory=list)


class SemanticMemory:
    """
    Semantic memory with embeddings for intelligent recall.

    Features:
    - Semantic search using embeddings
    - Memory relationships
    - Automatic importance scoring
    - Category-based organization
    - Temporal decay for importance
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.storage_path = storage_path or Path.home() / ".jarvis" / "memory" / "semantic"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.embedding_model = embedding_model
        self._embedder = None
        self._memories: dict[str, MemoryEntry] = {}
        self._embeddings_matrix: np.ndarray | None = None
        self._embedding_ids: list[str] = []

        # Load existing memories
        self._load()

    def _load(self) -> None:
        """Load memories from disk."""
        memories_file = self.storage_path / "memories.json"

        if memories_file.exists():
            try:
                with open(memories_file) as f:
                    data = json.load(f)
                    for entry_data in data.get("memories", []):
                        entry = MemoryEntry.from_dict(entry_data)
                        self._memories[entry.id] = entry
                        self._embedding_ids.append(entry.id)

                self._rebuild_embeddings_matrix()
                logger.info(f"Loaded {len(self._memories)} memories")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")

    def _save(self) -> None:
        """Save memories to disk."""
        memories_file = self.storage_path / "memories.json"

        try:
            with open(memories_file, "w") as f:
                json.dump(
                    {
                        "memories": [m.to_dict() for m in self._memories.values()],
                        "model": self.embedding_model,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory."""
        hash_input = f"{content}{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for texts."""
        if not self._embedder:
            await self._initialize_embedder()

        if self._embedder:
            try:
                embeddings = self._embedder.encode(texts)
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Embedding error: {e}")

        # Fallback: return zero vectors
        dim = 384  # Standard embedding dimension
        return [[0.0] * dim for _ in texts]

    async def _initialize_embedder(self) -> None:
        """Initialize embedding model."""
        try:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(self.embedding_model)
            logger.info(f"Loaded embedding model: {self.embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using fallback embeddings")
        except Exception as e:
            logger.error(f"Failed to load embedder: {e}")

    def _rebuild_embeddings_matrix(self) -> None:
        """Rebuild the embeddings matrix."""
        if not self._memories:
            self._embeddings_matrix = None
            return

        embeddings = []
        self._embedding_ids = []

        for entry in sorted(self._memories.values(), key=lambda x: x.created_at):
            if entry.embeddings:
                embeddings.append(entry.embeddings)
                self._embedding_ids.append(entry.id)

        if embeddings:
            self._embeddings_matrix = np.array(embeddings)
        else:
            self._embeddings_matrix = None

    async def remember(
        self,
        content: str,
        category: SemanticMemoryCategory = SemanticMemoryCategory.FACT,
        tags: set[str] | None = None,
        importance: float = 1.0,
        metadata: dict[str, Any] | None = None,
        related_to: list[str] | None = None,
    ) -> str:
        """
        Store a new memory.

        Args:
            content: Memory content
            category: Memory category
            tags: Associated tags
            importance: Importance score (0.0 - 1.0)
            metadata: Additional metadata
            related_to: IDs of related memories

        Returns:
            Memory ID
        """
        # Generate ID
        memory_id = self._generate_id(content)

        # Get embeddings
        embeddings = await self._get_embeddings([content])

        # Create entry
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            category=category,
            importance=importance,
            tags=tags or set(),
            metadata=metadata or {},
            embeddings=embeddings[0] if embeddings else None,
            relationships=related_to or [],
        )

        # Store
        self._memories[memory_id] = entry

        # Rebuild matrix
        self._rebuild_embeddings_matrix()

        # Save
        self._save()

        logger.info(f"Remembered: {memory_id} ({category.value})")

        return memory_id

    async def recall(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """
        Recall memories matching a query.

        Args:
            query: Search query

        Returns:
            List of matching memories with similarity scores
        """
        results: list[MemorySearchResult] = []

        # Get query embedding
        query_embeddings = await self._get_embeddings([query.text])
        query_embedding = np.array(query_embeddings[0])

        # Search in-memory
        for entry in self._memories.values():
            matched_on = []

            # Category filter
            if query.category and entry.category != query.category:
                continue
            elif query.category:
                matched_on.append("category")

            # Tags filter
            if query.tags:
                matching_tags = entry.tags & query.tags
                if matching_tags:
                    matched_on.append("tags")

            # Importance filter
            if entry.importance < query.min_importance:
                continue

            # Semantic similarity
            if entry.embeddings and self._embeddings_matrix is not None:
                idx = self._embedding_ids.index(entry.id)
                entry_embedding = self._embeddings_matrix[idx]

                similarity = self._cosine_similarity(query_embedding, entry_embedding)

                if similarity >= query.min_similarity:
                    results.append(
                        MemorySearchResult(
                            entry=entry,
                            similarity=similarity,
                            matched_on=matched_on,
                        )
                    )
            else:
                # Fallback: keyword matching
                keywords = set(query.text.lower().split())
                if keywords & set(entry.content.lower().split()):
                    results.append(
                        MemorySearchResult(
                            entry=entry,
                            similarity=0.5,
                            matched_on=["keyword"],
                        )
                    )

        # Sort by relevance (importance * similarity)
        results.sort(
            key=lambda x: x.entry.importance * x.similarity,
            reverse=True,
        )

        return results[: query.limit]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))

    async def forget(self, memory_id: str) -> bool:
        """
        Remove a memory.

        Args:
            memory_id: ID of memory to remove

        Returns:
            True if removed
        """
        if memory_id in self._memories:
            del self._memories[memory_id]
            self._rebuild_embeddings_matrix()
            self._save()
            logger.info(f"Forgot: {memory_id}")
            return True
        return False

    async def update(
        self,
        memory_id: str,
        content: str | None = None,
        importance: float | None = None,
        tags: set[str] | None = None,
    ) -> bool:
        """
        Update a memory.

        Args:
            memory_id: ID of memory to update
            content: New content (optional)
            importance: New importance (optional)
            tags: New tags (optional)

        Returns:
            True if updated
        """
        if memory_id not in self._memories:
            return False

        entry = self._memories[memory_id]

        if content:
            entry.content = content
            entry.embeddings = (await self._get_embeddings([content]))[0]

        if importance is not None:
            entry.importance = max(0.0, min(1.0, importance))

        if tags is not None:
            entry.tags = tags

        entry.updated_at = datetime.now()

        self._rebuild_embeddings_matrix()
        self._save()

        return True

    def add_relationship(self, memory_id: str, related_id: str) -> bool:
        """Add a relationship between memories."""
        if memory_id not in self._memories or related_id not in self._memories:
            return False

        if related_id not in self._memories[memory_id].relationships:
            self._memories[memory_id].relationships.append(related_id)
            self._save()

        return True

    def get_related(self, memory_id: str) -> list[MemoryEntry]:
        """Get related memories."""
        if memory_id not in self._memories:
            return []

        related = []
        for related_id in self._memories[memory_id].relationships:
            if related_id in self._memories:
                related.append(self._memories[related_id])

        return related

    async def summarize_me(self) -> str:
        """
        Generate a summary of the user based on memories.

        Returns:
            Summary string
        """
        # Get important memories
        important = [m for m in self._memories.values() if m.importance >= 0.7]

        # Group by category
        by_category: dict[SemanticMemoryCategory, list[MemoryEntry]] = {}
        for entry in important:
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)

        # Build summary
        lines = ["Here's what I know about you:", ""]

        for category in [
            SemanticMemoryCategory.PERSON,
            SemanticMemoryCategory.PREFERENCE,
            SemanticMemoryCategory.GOAL,
            SemanticMemoryCategory.PROJECT,
        ]:
            if category in by_category:
                entries = by_category[category]
                lines.append(f"**{category.value.title()}:**")
                for entry in entries[:5]:  # Limit to 5 per category
                    lines.append(f"  - {entry.content}")
                lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        by_category: dict[str, int] = {}
        total_importance = 0.0

        for entry in self._memories.values():
            cat = entry.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            total_importance += entry.importance

        return {
            "total_memories": len(self._memories),
            "by_category": by_category,
            "average_importance": total_importance / len(self._memories) if self._memories else 0,
            "storage_path": str(self.storage_path),
        }


class MemoryRelationshipGraph:
    """
    Graph of memory relationships for advanced queries.
    """

    def __init__(self):
        self._graph: dict[str, set[str]] = {}  # memory_id -> related_ids

    def add(self, memory_id: str, related_id: str) -> None:
        """Add a relationship."""
        if memory_id not in self._graph:
            self._graph[memory_id] = set()
        self._graph[memory_id].add(related_id)

    def remove(self, memory_id: str) -> None:
        """Remove a memory and its relationships."""
        if memory_id in self._graph:
            del self._graph[memory_id]

        for related in self._graph.values():
            related.discard(memory_id)

    def get_related(self, memory_id: str, depth: int = 1) -> set[str]:
        """Get related memories up to a certain depth."""
        visited = set()
        current = {memory_id}

        for _ in range(depth):
            next_level = set()
            for mid in current:
                visited.add(mid)
                if mid in self._graph:
                    next_level.update(self._graph[mid])

            current = next_level - visited

        return visited - {memory_id}

    def find_path(self, start: str, end: str) -> list[str] | None:
        """Find a path between two memories."""
        if start == end:
            return [start]

        visited = {start}
        queue = [(start, [start])]

        while queue:
            current, path = queue.pop(0)

            for related in self._graph.get(current, []):
                if related == end:
                    return path + [related]

                if related not in visited:
                    visited.add(related)
                    queue.append((related, path + [related]))

        return None
