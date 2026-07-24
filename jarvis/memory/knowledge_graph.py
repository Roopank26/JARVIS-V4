"""
Knowledge Graph for JARVIS.

Relationship-based memory layer on top of existing knowledge/semantic systems.

Examples:
User → Projects → Goals → Agents → Providers → Tools → Documents → Plugins → Models

Supports semantic + graph search.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "properties": self.properties,
        }


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "properties": self.properties,
        }


class KnowledgeGraph:
    """
    Optional graph layer for entity relationships.
    Persists to JSON and supports simple adjacency traversal.
    """

    def __init__(self, graph_path: Path | None = None):
        if graph_path is None:
            base_dir = Path.home() / ".jarvis" / "memory"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.graph_path = base_dir / "knowledge_graph.json"
        else:
            self.graph_path = graph_path
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        if not self.graph_path.exists():
            self._save()
            return
        try:
            with open(self.graph_path, encoding="utf-8") as f:
                data = json.load(f)
            for node in data.get("nodes", []):
                self._nodes[node["id"]] = GraphNode(**node)
            for edge in data.get("edges", []):
                self._edges.append(GraphEdge(**edge))
        except Exception as exc:
            logger.debug("Knowledge graph load failed: %s", exc)
            self._nodes = {}
            self._edges = []

    def _save(self) -> None:
        try:
            with open(self.graph_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "nodes": [n.to_dict() for n in self._nodes.values()],
                        "edges": [e.to_dict() for e in self._edges],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception:
            logger.debug("Knowledge graph save failed", exc_info=True)

    def add_node(self, node_id: str, node_type: str, label: str, properties: dict[str, Any] | None = None) -> GraphNode:
        node = GraphNode(id=node_id, type=node_type, label=label, properties=properties or {})
        self._nodes[node_id] = node
        self._save()
        return node

    def add_edge(self, source: str, target: str, relation: str, properties: dict[str, Any] | None = None) -> GraphEdge:
        edge = GraphEdge(source=source, target=target, relation=relation, properties=properties or {})
        self._edges.append(edge)
        self._save()
        return edge

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_related(self, node_id: str, relation: str | None = None) -> list[GraphEdge]:
        related = []
        for edge in self._edges:
            if (edge.source == node_id or edge.target == node_id) and (relation is None or edge.relation == relation):
                related.append(edge)
        return related

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = query.lower()
        results: list[dict[str, Any]] = []
        for node in self._nodes.values():
            text = f"{node.label} {node.type} {json.dumps(node.properties)}".lower()
            if q in text:
                results.append({"type": "node", "data": node.to_dict()})
        for edge in self._edges:
            text = f"{edge.relation} {json.dumps(edge.properties)}".lower()
            if q in text:
                results.append({"type": "edge", "data": edge.to_dict()})
            if len(results) >= limit:
                break
        return results[:limit]

    def to_prompt_context(self, max_items: int = 30) -> str:
        if not self._nodes and not self._edges:
            return ""
        lines = ["Knowledge Graph:"]
        for node in list(self._nodes.values())[: max_items // 2]:
            lines.append(f"  - {node.type}: {node.label}")
        for edge in self._edges[: max_items // 2]:
            lines.append(f"  - {edge.source} --[{edge.relation}]--> {edge.target}")
        return "\n".join(lines) + "\n"

    def get_stats(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": list({n.type for n in self._nodes.values()}),
        }
