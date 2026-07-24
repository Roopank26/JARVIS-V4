"""
JARVIS Phase 5 — Context Fusion Engine.

Combines information from multiple sources into one unified reasoning context:
- conversation history
- long-term memory
- knowledge graph
- repositories
- documents
- active projects
- current screen
- running applications

Does NOT replace existing memory or context systems. Produces a fused snapshot.
"""

from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SourceWeight:
    source: str
    weight: float = 1.0
    max_items: int = 10
    enabled: bool = True


@dataclass
class UnifiedContext:
    query: str = ""
    conversation_fragment: str = ""
    memory_facts: list[dict[str, Any]] = field(default_factory=list)
    knowledge_graph_edges: list[dict[str, Any]] = field(default_factory=list)
    repository_context: list[dict[str, Any]] = field(default_factory=list)
    document_excerpts: list[dict[str, Any]] = field(default_factory=list)
    active_projects: list[dict[str, Any]] = field(default_factory=list)
    screen_context: dict[str, Any] = field(default_factory=dict)
    running_apps: list[str] = field(default_factory=list)
    fused_summary: str = ""
    confidence: float = 0.0
    sources_used: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "conversation_fragment": self.conversation_fragment,
            "memory_facts": self.memory_facts,
            "knowledge_graph_edges": self.knowledge_graph_edges,
            "repository_context": self.repository_context,
            "document_excerpts": self.document_excerpts,
            "active_projects": self.active_projects,
            "screen_context": self.screen_context,
            "running_apps": self.running_apps,
            "fused_summary": self.fused_summary,
            "confidence": round(self.confidence, 3),
            "sources_used": self.sources_used,
            "timestamp": self.timestamp,
        }


class ContextFusionEngine:
    """
    Fuses multiple context sources into a unified reasoning context.

    Integration points (all additive):
    - memory.enhanced (conversation + long-term)
    - memory.knowledge_graph (graph edges)
    - repo.analyzer (repository context)
    - rag (document excerpts)
    - memory.project (active projects)
    - vision.production (screen context, optional)
    - desktop.automation (running apps, optional)
    """

    def __init__(self) -> None:
        self._weights: list[SourceWeight] = [
            SourceWeight(source="conversation_history", weight=1.0, max_items=8),
            SourceWeight(source="long_term_memory", weight=0.9, max_items=6),
            SourceWeight(source="knowledge_graph", weight=0.8, max_items=6),
            SourceWeight(source="repository", weight=0.7, max_items=5),
            SourceWeight(source="documents", weight=0.6, max_items=5),
            SourceWeight(source="active_projects", weight=0.8, max_items=5),
            SourceWeight(source="screen", weight=0.4, max_items=3),
            SourceWeight(source="running_apps", weight=0.3, max_items=5),
        ]
        self._last_fusion: UnifiedContext | None = None

    async def fuse(self, query: str, extra_context: dict[str, Any] | None = None) -> UnifiedContext:
        ctx = UnifiedContext(query=query)
        sources_used: list[str] = []

        for weight in self._weights:
            if not weight.enabled:
                continue
            try:
                await self._collect_source(ctx, weight)
                sources_used.append(weight.source)
            except Exception as exc:
                logger.debug("Context fusion source %s failed: %s", weight.source, exc)

        ctx.fused_summary = self._build_summary(ctx)
        ctx.sources_used = sources_used
        ctx.confidence = self._estimate_confidence(ctx, sources_used)
        if extra_context:
            with contextlib.suppress(Exception):
                ctx.fused_summary += f"\n\n[EXTRA CONTEXT]\n{extra_context.get('summary', '')}"
        self._last_fusion = ctx
        return ctx

    def get_last_fusion(self) -> UnifiedContext | None:
        return self._last_fusion

    async def _collect_source(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        if weight.source == "conversation_history":
            await self._collect_conversation(ctx, weight)
        elif weight.source == "long_term_memory":
            await self._collect_memory(ctx, weight)
        elif weight.source == "knowledge_graph":
            await self._collect_knowledge_graph(ctx, weight)
        elif weight.source == "repository":
            await self._collect_repository(ctx, weight)
        elif weight.source == "documents":
            await self._collect_documents(ctx, weight)
        elif weight.source == "active_projects":
            await self._collect_projects(ctx, weight)
        elif weight.source == "screen":
            await self._collect_screen(ctx, weight)
        elif weight.source == "running_apps":
            await self._collect_running_apps(ctx, weight)

    def get_retrieval_precision(self) -> dict[str, float]:
        if not self._last_fusion:
            return {}
        ctx = self._last_fusion
        scores: dict[str, float] = {}
        if ctx.memory_facts:
            scores["memory_retrieval"] = min(1.0, len(ctx.memory_facts) / 5.0)
        if ctx.knowledge_graph_edges:
            scores["kg_retrieval"] = min(1.0, len(ctx.knowledge_graph_edges) / 6.0)
        if ctx.document_excerpts:
            scores["document_retrieval"] = min(1.0, len(ctx.document_excerpts) / 5.0)
        if ctx.repository_context:
            scores["repo_retrieval"] = min(1.0, len(ctx.repository_context))
        if ctx.conversation_fragment:
            scores["conversation_retrieval"] = 0.8 if len(ctx.conversation_fragment) > 100 else 0.3
        if ctx.active_projects:
            scores["project_retrieval"] = min(1.0, len(ctx.active_projects) / 5.0)
        return scores

    async def _collect_conversation(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.memory.enhanced import get_enhanced_memory
            mem = get_enhanced_memory()
            summary = mem.get_rolling_summary()
            if summary:
                ctx.conversation_fragment = summary[:2000]
        except Exception:
            pass

    async def _collect_memory(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.memory.enhanced import get_enhanced_memory
            mem = get_enhanced_memory()
            results = mem.recall(ctx.query)[: weight.max_items]
            for r in results:
                if isinstance(r, dict):
                    ctx.memory_facts.append({
                        "key": r.get("key", ""),
                        "value": r.get("value", ""),
                        "category": r.get("category", ""),
                        "source": "long_term_memory",
                    })
        except Exception:
            pass

    async def _collect_knowledge_graph(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.memory.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            nodes = getattr(kg, "_nodes", {})
            edges = getattr(kg, "_edges", [])
            for edge in list(edges)[: weight.max_items]:
                if isinstance(edge, dict):
                    ctx.knowledge_graph_edges.append({
                        "from": edge.get("source", ""),
                        "to": edge.get("target", ""),
                        "relation": edge.get("relation", ""),
                    })
            if nodes:
                ctx.knowledge_graph_edges.append({
                    "from": "knowledge_graph",
                    "to": "nodes_count",
                    "relation": str(len(nodes)),
                })
        except Exception:
            pass

    async def _collect_repository(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer

            repo_path = Path.cwd()
            analyzer = RepositoryAnalyzer(repo_path)
            analyzer.analyze()
            stats = analyzer.get_statistics()
            ctx.repository_context.append({
                "source": "local_repo",
                "files": stats.total_files,
                "lines": stats.total_lines,
                "functions": stats.total_functions,
                "classes": stats.total_classes,
            })
        except Exception:
            pass

    async def _collect_documents(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.rag import get_rag_system
            rag = get_rag_system()
            results = await rag.search(ctx.query, limit=weight.max_items)
            for r in results[: weight.max_items]:
                if isinstance(r, dict):
                    ctx.document_excerpts.append({
                        "content": (r.get("content", "") or "")[:500],
                        "source": r.get("source", ""),
                        "score": r.get("score", 0.0),
                    })
        except Exception:
            pass

    async def _collect_projects(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.memory.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            projects = mgr.get_projects()
            for p in projects[: weight.max_items]:
                if isinstance(p, dict):
                    ctx.active_projects.append(p)
        except Exception:
            pass

    async def _collect_screen(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.vision.production import get_vision_system
            vs = get_vision_system()
            if getattr(vs, "initialized", False):
                ctx.screen_context = {
                    "mode": getattr(vs, "mode", "unknown"),
                    "available": True,
                }
        except Exception:
            pass

    async def _collect_running_apps(self, ctx: UnifiedContext, weight: SourceWeight) -> None:
        try:
            from jarvis.desktop.automation import get_desktop_automation
            da = get_desktop_automation()
            windows = await da.list_windows()
            titles = [w.get("title", "") for w in windows if w.get("title")]
            ctx.running_apps = titles[: weight.max_items]
        except Exception:
            pass

    def _build_summary(self, ctx: UnifiedContext) -> str:
        parts: list[str] = []
        if ctx.conversation_fragment:
            parts.append(f"[CONVERSATION]\n{ctx.conversation_fragment}")
        if ctx.memory_facts:
            facts = "\n".join(
                f"- {f.get('key', '')}: {f.get('value', '')}" for f in ctx.memory_facts[:6]
            )
            parts.append(f"[MEMORY FACTS]\n{facts}")
        if ctx.knowledge_graph_edges:
            edges = "\n".join(
                f"- {e.get('from', '')} --[{e.get('relation', '')}]--> {e.get('to', '')}"
                for e in ctx.knowledge_graph_edges[:6]
            )
            parts.append(f"[KNOWLEDGE GRAPH]\n{edges}")
        if ctx.repository_context:
            repo = "\n".join(
                f"- {r.get('source', '')}: {r.get('files', 0)} files, {r.get('lines', 0)} lines"
                for r in ctx.repository_context
            )
            parts.append(f"[REPOSITORY]\n{repo}")
        if ctx.document_excerpts:
            docs = "\n".join(
                f"- {d.get('source', '')}: {(d.get('content', '') or '')[:120]}..."
                for d in ctx.document_excerpts[:5]
            )
            parts.append(f"[DOCUMENTS]\n{docs}")
        if ctx.active_projects:
            projs = "\n".join(
                f"- {p.get('name', p.get('key', ''))}" for p in ctx.active_projects[:5]
            )
            parts.append(f"[ACTIVE PROJECTS]\n{projs}")
        if ctx.screen_context:
            parts.append(f"[SCREEN]\n{ctx.screen_context}")
        if ctx.running_apps:
            apps = "\n".join(f"- {a}" for a in ctx.running_apps[:5])
            parts.append(f"[RUNNING APPS]\n{apps}")
        return "\n\n".join(parts) if parts else "(no context sources available)"

    def _estimate_confidence(self, ctx: UnifiedContext, sources_used: list[str]) -> float:
        if not sources_used:
            return 0.0
        total = 0.0
        weight_sum = 0.0
        for w in self._weights:
            if w.source in sources_used:
                total += w.weight
                weight_sum += 1.0
        return total / weight_sum if weight_sum > 0 else 0.0


_context_fusion: ContextFusionEngine | None = None


def get_context_fusion_engine() -> ContextFusionEngine:
    global _context_fusion
    if _context_fusion is None:
        _context_fusion = ContextFusionEngine()
    return _context_fusion


def reset_context_fusion_engine() -> None:
    global _context_fusion
    _context_fusion = None
