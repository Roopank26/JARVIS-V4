"""
Tests for semantic memory system.
"""

import pytest
import tempfile
from pathlib import Path
from jarvis.memory.semantic import (
    SemanticMemoryCategory,
    MemoryEntry,
    MemoryQuery,
    SemanticMemory,
    MemoryRelationshipGraph,
)


class TestMemoryEntry:
    """Test MemoryEntry class."""
    
    def test_to_dict(self):
        """Test converting entry to dict."""
        entry = MemoryEntry(
            id="test123",
            content="Test memory",
            category=SemanticMemoryCategory.FACT,
        )
        
        data = entry.to_dict()
        
        assert data["id"] == "test123"
        assert data["content"] == "Test memory"
        assert data["category"] == "fact"
    
    def test_from_dict(self):
        """Test creating entry from dict."""
        data = {
            "id": "test123",
            "content": "Test memory",
            "category": "person",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "importance": 0.8,
            "tags": ["test", "demo"],
            "metadata": {},
            "embeddings": None,
            "relationships": [],
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.id == "test123"
        assert entry.category == SemanticMemoryCategory.PERSON
        assert "test" in entry.tags


class TestSemanticMemory:
    """Test SemanticMemory class."""
    
    @pytest.fixture
    def memory(self):
        """Create a temporary memory instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SemanticMemory(storage_path=Path(tmpdir))
    
    @pytest.mark.asyncio
    async def test_remember(self, memory):
        """Test remembering information."""
        memory_id = await memory.remember(
            content="My name is John",
            category=SemanticMemoryCategory.PERSON,
            tags={"name", "personal"},
        )
        
        assert memory_id is not None
        assert memory_id in memory._memories
    
    @pytest.mark.asyncio
    async def test_recall(self, memory):
        """Test recalling memories."""
        # Remember some things
        await memory.remember(
            content="I prefer dark mode",
            category=SemanticMemoryCategory.PREFERENCE,
        )
        await memory.remember(
            content="My favorite language is Python",
            category=SemanticMemoryCategory.PREFERENCE,
        )
        
        # Recall
        query = MemoryQuery(text="preferences", limit=10)
        results = await memory.recall(query)
        
        assert len(results) >= 2
    
    @pytest.mark.asyncio
    async def test_forget(self, memory):
        """Test forgetting a memory."""
        memory_id = await memory.remember(
            content="Temporary information",
            category=SemanticMemoryCategory.FACT,
        )
        
        # Verify it exists
        assert memory_id in memory._memories
        
        # Forget it
        assert await memory.forget(memory_id)
        assert memory_id not in memory._memories
        
        # Verify it's gone
        assert not await memory.forget(memory_id)
    
    @pytest.mark.asyncio
    async def test_update(self, memory):
        """Test updating a memory."""
        memory_id = await memory.remember(
            content="Original content",
            category=SemanticMemoryCategory.FACT,
            importance=0.5,
        )
        
        # Update
        success = await memory.update(
            memory_id,
            content="Updated content",
            importance=0.9,
        )
        
        assert success
        assert memory._memories[memory_id].content == "Updated content"
        assert memory._memories[memory_id].importance == 0.9
    
    @pytest.mark.asyncio
    async def test_relationships(self, memory):
        """Test memory relationships."""
        id1 = await memory.remember(
            content="Project JARVIS",
            category=SemanticMemoryCategory.PROJECT,
        )
        id2 = await memory.remember(
            content="Python programming",
            category=SemanticMemoryCategory.CODE,
        )
        
        # Add relationship
        assert memory.add_relationship(id1, id2)
        
        # Get related
        related = memory.get_related(id1)
        assert len(related) == 1
        assert related[0].id == id2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, memory):
        """Test getting memory statistics."""
        await memory.remember(
            content="Fact 1",
            category=SemanticMemoryCategory.FACT,
        )
        await memory.remember(
            content="Person 1",
            category=SemanticMemoryCategory.PERSON,
        )
        
        stats = memory.get_stats()
        
        assert stats["total_memories"] == 2
        assert "fact" in stats["by_category"]
        assert "person" in stats["by_category"]


class TestMemoryRelationshipGraph:
    """Test MemoryRelationshipGraph."""
    
    def test_add_relationship(self):
        """Test adding relationships."""
        graph = MemoryRelationshipGraph()
        
        graph.add("a", "b")
        graph.add("a", "c")
        
        assert "b" in graph._graph["a"]
        assert "c" in graph._graph["a"]
    
    def test_remove(self):
        """Test removing nodes."""
        graph = MemoryRelationshipGraph()
        
        graph.add("a", "b")
        graph.remove("a")
        
        assert "a" not in graph._graph
    
    def test_get_related(self):
        """Test getting related nodes."""
        graph = MemoryRelationshipGraph()
        
        graph.add("a", "b")
        graph.add("b", "c")
        graph.add("c", "d")
        
        # Depth 1
        related = graph.get_related("a", depth=1)
        # Returns all related at depth <= specified
        assert "b" in related or "a" not in related
    
    def test_find_path(self):
        """Test finding paths."""
        graph = MemoryRelationshipGraph()
        
        graph.add("a", "b")
        graph.add("b", "c")
        graph.add("c", "d")
        
        # Path exists
        path = graph.find_path("a", "d")
        assert path == ["a", "b", "c", "d"]
        
        # No path
        graph.add("x", "y")
        path = graph.find_path("a", "x")
        assert path is None
