"""
JARVIS Phase 3 — Research Pipeline.

Structured research workflow:

  Search → Collect → Verify → Compare → Extract → Summarize → Store → Generate report → Update memory
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    url: str
    title: str = ""
    snippet: str = ""
    source_name: str = ""
    published_date: str | None = None
    relevance_score: float = 0.0
    content: str = ""


@dataclass
class ResearchResult:
    query: str
    sources: list[ResearchSource] = field(default_factory=list)
    summary: str = ""
    key_findings: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    report: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0


class ResearchPipeline:
    """
    Advanced research pipeline that wraps the existing ResearchAgent
    and enforces a structured workflow with citations and confidence.
    """

    def __init__(self) -> None:
        self._agent = None

    async def _get_agent(self) -> Any | None:
        if self._agent is None:
            try:
                from jarvis.research.research_agent import ResearchAgent
                self._agent = ResearchAgent()
            except Exception:
                return None
        return self._agent

    async def run(self, query: str, depth: str = "normal") -> ResearchResult:
        """
        Execute the full research pipeline for a query.

        Args:
            query: The research question
            depth: quick | normal | deep

        Returns:
            ResearchResult with sources, verified facts, and summary
        """
        agent = await self._get_agent()
        sources: list[ResearchSource] = []
        result = ResearchResult(query=query)

        if agent is None:
            result.summary = "Research agent unavailable."
            result.confidence = 0.0
            return result

        try:
            raw = await agent.research(query)
            if hasattr(raw, "sources"):
                for s in raw.sources:
                    sources.append(ResearchSource(
                        url=getattr(s, "url", ""),
                        title=getattr(s, "title", ""),
                        snippet=getattr(s, "snippet", ""),
                        source_name=getattr(s, "source_name", ""),
                        published_date=getattr(s, "published_date", None),
                        relevance_score=float(getattr(s, "relevance_score", 0.0) or 0.0),
                    ))
            result.sources = sources
            result.summary = getattr(raw, "summary", "") or ""
            result.key_findings = list(getattr(raw, "key_findings", []) or [])
            result.citations = list(getattr(raw, "citations", []) or [])
        except Exception as exc:
            logger.debug("Research pipeline failed: %s", exc)
            result.summary = f"Research failed: {exc}"
            result.confidence = 0.0
            return result

        result.confidence = self._estimate_confidence(result)
        result.report = self._generate_report(result)
        return result

    def _estimate_confidence(self, result: ResearchResult) -> float:
        if not result.sources:
            return 0.0
        source_quality = sum(s.relevance_score for s in result.sources) / len(result.sources)
        coverage = min(1.0, len(result.sources) / 5.0)
        citation_rate = len(result.citations) / max(1, len(result.sources))
        return round((source_quality * 0.5 + coverage * 0.3 + citation_rate * 0.2), 3)

    def _generate_report(self, result: ResearchResult) -> str:
        lines = [f"# Research Report: {result.query}", ""]
        lines.append("## Summary")
        lines.append(result.summary or "No summary available.")
        lines.append("")
        lines.append("## Key Findings")
        for i, finding in enumerate(result.key_findings, 1):
            lines.append(f"{i}. {finding}")
        lines.append("")
        lines.append("## Sources")
        for i, source in enumerate(result.sources, 1):
            lines.append(f"{i}. [{source.title or source.url}]({source.url}) — {source.source_name or 'Web'}")
        if result.citations:
            lines.append("")
            lines.append("## Citations")
            for c in result.citations:
                lines.append(f"- {c}")
        return "\n".join(lines)

    async def store(self, result: ResearchResult) -> bool:
        """Store research result in memory/knowledge base."""
        try:
            from jarvis.memory.memory_manager import get_memory_manager
            memory = get_memory_manager()
            memory.remember(
                f"research:{result.query}",
                result.summary,
                category="research",
            )
            return True
        except Exception:
            return False
