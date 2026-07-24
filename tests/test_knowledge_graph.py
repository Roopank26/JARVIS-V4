"""
Tests for Knowledge Graph.
"""

from pathlib import Path

from jarvis.memory.knowledge_graph import KnowledgeGraph
from jarvis.memory.long_term import LongTermMemory


class TestKnowledgeGraph:
    def test_add_node_and_get(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        node = kg.add_node("user1", "user", "Alice", {"role": "developer"})
        assert node.id == "user1"
        assert node.label == "Alice"
        fetched = kg.get_node("user1")
        assert fetched is not None
        assert fetched.type == "user"

    def test_add_edge(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("user1", "user", "Alice")
        kg.add_node("proj1", "project", "JARVIS")
        edge = kg.add_edge("user1", "proj1", "owns")
        assert edge.source == "user1"
        assert edge.target == "proj1"
        assert edge.relation == "owns"

    def test_get_related(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("n1", "type1", "A")
        kg.add_node("n2", "type2", "B")
        kg.add_node("n3", "type3", "C")
        kg.add_edge("n1", "n2", "link")
        kg.add_edge("n1", "n3", "other")
        related = kg.get_related("n1")
        assert len(related) == 2

    def test_search(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("node1", "goal", "Ship phase 2", {"priority": "high"})
        results = kg.search("phase")
        assert len(results) >= 1

    def test_to_prompt_context_empty(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        assert kg.to_prompt_context() == ""

    def test_to_prompt_context_non_empty(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("n1", "agent", "Planner")
        kg.add_edge("n1", "n2", "uses")
        out = kg.to_prompt_context()
        assert "agent" in out
        assert "Planner" in out

    def test_get_stats(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("n1", "type1", "A")
        kg.add_node("n2", "type2", "B")
        kg.add_edge("n1", "n2", "rel")
        stats = kg.get_stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert "type1" in stats["node_types"]

    def test_persistence(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("persist_node", "type", "Label")
        kg2 = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        assert kg2.get_node("persist_node") is not None


class TestMemoryGraphIntegration:
    def test_recall_includes_graph_results(self, tmp_path: Path):
        kg = KnowledgeGraph(graph_path=tmp_path / "graph.json")
        kg.add_node("proj1", "project", "JARVIS", {"priority": "high"})
        kg.add_node("goal1", "goal", "Ship phase 2")
        kg.add_edge("proj1", "goal1", "has_goal")

        memory = LongTermMemory(
            memory_path=tmp_path / "memory.json",
            knowledge_graph=kg,
        )
        memory.remember("project_jarvis", "JARVIS personal assistant", category="projects")
        results = memory.recall("JARVIS")
        assert any(r.get("source") == "knowledge_graph" for r in results)
        keys = [r.get("key") for r in results]
        assert "project_jarvis" in keys or "proj1" in keys

    def test_recall_without_graph_is_backward_compatible(self, tmp_path: Path):
        memory = LongTermMemory(memory_path=tmp_path / "memory.json")
        memory.remember("foo", "bar", category="notes")
        results = memory.recall("foo")
        assert len(results) >= 1
        assert results[0]["key"] == "foo"
        assert results[0].get("source") != "knowledge_graph"
