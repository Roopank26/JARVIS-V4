"""
JARVIS-V7 Evolution — Enhanced Knowledge Graph Engine.

Continuously builds and improves a personal knowledge graph.
Understands projects, repositories, codebases, concepts, libraries,
frameworks, research, goals, ideas, tasks, and relationships.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_DIR = Path.home() / ".jarvis" / "evolution"
DEFAULT_GRAPH_FILE = "knowledge_graph.json"


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    confidence: float = 1.0
    last_updated: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "properties": self.properties,
            "embedding": self.embedding,
            "confidence": self.confidence,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
        }


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    last_updated: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "properties": self.properties,
            "weight": self.weight,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
        }


class KnowledgeGraphEngine:
    _MAX_NODES = 50000
    _MAX_EDGES = 200000

    def __init__(self, graph_dir: Path | None = None):
        self.graph_dir = graph_dir or DEFAULT_GRAPH_DIR
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.graph_dir / DEFAULT_GRAPH_FILE
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._load()

    def _warn_if_limits_exceeded(self) -> None:
        if len(self._nodes) >= self._MAX_NODES:
            logger.warning("Knowledge graph node limit (%d) reached. Consider compaction.", self._MAX_NODES)
        if len(self._edges) >= self._MAX_EDGES:
            logger.warning("Knowledge graph edge limit (%d) reached. Consider compaction.", self._MAX_EDGES)

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            for node in data.get("nodes", []):
                self._nodes[node["id"]] = GraphNode(**node)
            for edge in data.get("edges", []):
                self._edges.append(GraphEdge(**edge))
        except Exception as exc:
            logger.debug("Knowledge graph load failed: %s", exc)

    def _save(self) -> None:
        try:
            from jarvis.evolution import atomic_write_json
            atomic_write_json(
                self.path,
                {
                    "nodes": [n.to_dict() for n in self._nodes.values()],
                    "edges": [e.to_dict() for e in self._edges],
                },
            )
        except Exception:
            logger.debug("Knowledge graph save failed", exc_info=True)

    def add_node(self, node_type: str, label: str, properties: dict[str, Any] | None = None) -> GraphNode:
        self._warn_if_limits_exceeded()
        node_id = f"{node_type}:{uuid.uuid4().hex[:8]}"
        if properties is None:
            properties = {}
        properties.setdefault("label", label)
        node = GraphNode(id=node_id, type=node_type, label=label, properties=properties)
        self._nodes[node_id] = node
        self._save()
        return node

    def add_edge(self, source: str, target: str, relation: str, properties: dict[str, Any] | None = None) -> GraphEdge | None:
        if source not in self._nodes or target not in self._nodes:
            return None
        self._warn_if_limits_exceeded()
        edge = GraphEdge(source=source, target=target, relation=relation, properties=properties or {})
        self._edges.append(edge)
        self._save()
        return edge

    def get_or_create_node(self, node_type: str, label: str, properties: dict[str, Any] | None = None) -> GraphNode:
        for node in self._nodes.values():
            if node.type == node_type and node.label == label:
                if properties:
                    node.properties.update(properties)
                    node.last_updated = time.time()
                    self._save()
                return node
        return self.add_node(node_type, label, properties)

    def relate(self, source_type: str, source_label: str, relation: str, target_type: str, target_label: str) -> GraphEdge | None:
        source = self.get_or_create_node(source_type, source_label)
        target = self.get_or_create_node(target_type, target_label)
        return self.add_edge(source.id, target.id, relation)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_related(self, node_id: str, relation: str | None = None) -> list[tuple[GraphEdge, GraphNode | None]]:
        results = []
        for edge in self._edges:
            if edge.source == node_id or edge.target == node_id:
                if relation and edge.relation != relation:
                    continue
                if edge.source == node_id:
                    other = self._nodes.get(edge.target)
                else:
                    other = self._nodes.get(edge.source)
                results.append((edge, other))
        return results

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        q = query.lower()
        results: list[dict[str, Any]] = []
        for node in self._nodes.values():
            text = f"{node.label} {node.type} {json.dumps(node.properties, ensure_ascii=False)}".lower()
            if q in text:
                results.append({"type": "node", "data": node.to_dict()})
        for edge in self._edges:
            text = f"{edge.relation} {json.dumps(edge.properties, ensure_ascii=False)}".lower()
            if q in text:
                results.append({"type": "edge", "data": edge.to_dict()})
            if len(results) >= limit:
                break
        return results[:limit]

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
        del self._nodes[node_id]
        self._save()
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": list({n.type for n in self._nodes.values()}),
        }

    def to_prompt_context(self, max_items: int = 50) -> str:
        if not self._nodes and not self._edges:
            return ""
        lines = ["Knowledge Graph:"]
        for node in list(self._nodes.values())[: max_items // 2]:
            lines.append(f"  - {node.type}: {node.label}")
        for edge in self._edges[: max_items // 2]:
            lines.append(f"  - {edge.source} --[{edge.relation}]--> {edge.target}")
        return "\n".join(lines) + "\n"


_graph_instance: KnowledgeGraphEngine | None = None


def get_knowledge_graph() -> KnowledgeGraphEngine:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = KnowledgeGraphEngine()
    return _graph_instance


def reset_knowledge_graph() -> None:
    global _graph_instance
    _graph_instance = None
