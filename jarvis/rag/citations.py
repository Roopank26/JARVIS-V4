"""
Citation formatting utilities for JARVIS RAG system.

Supports multiple citation styles:
- inline: [Source N: filename, page X]
- footnote: Source N^1
- numbered: [1] filename, page X
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Citation:
    """Represents a single citation from a document chunk."""

    source_path: str
    document_title: str
    page: int | None = None
    chunk_index: int = 0
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CitationResult:
    """Result containing a chunk and its citation."""

    content: str
    citation: Citation
    score: float = 0.0


class CitationFormatter:
    """Format citations in different styles."""

    @staticmethod
    def format_filename(source_path: str) -> str:
        """Extract filename from full path."""
        return Path(source_path).name

    def inline(
        self,
        results: list[CitationResult],
        *,
        start_index: int = 1,
    ) -> str:
        """Format citations as inline references [Source N: file, page X]."""
        if not results:
            return ""

        parts = []
        for i, result in enumerate(results, start=start_index):
            page_str = f", page {result.citation.page}" if result.citation.page else ""
            parts.append(f"[{i}: {self.format_filename(result.citation.source_path)}{page_str}]")
        return " ".join(parts)

    def footnote(
        self,
        results: list[CitationResult],
        *,
        start_index: int = 1,
    ) -> str:
        """Format citations as footnotes Source N^1."""
        if not results:
            return ""

        parts = []
        for i, result in enumerate(results, start=start_index):
            page_str = f", page {result.citation.page}" if result.citation.page else ""
            parts.append(f"{self.format_filename(result.citation.source_path)}{page_str}^{i}")
        return " ".join(parts)

    def numbered(
        self,
        results: list[CitationResult],
        *,
        start_index: int = 1,
    ) -> str:
        """Format citations as numbered references [1] file, page X."""
        if not results:
            return ""

        parts = []
        for i, result in enumerate(results, start=start_index):
            page_str = f", page {result.citation.page}" if result.citation.page else ""
            parts.append(f"[{i}] {self.format_filename(result.citation.source_path)}{page_str}")
        return "\n".join(parts)

    def format(
        self,
        results: list[CitationResult],
        style: str = "inline",
        *,
        start_index: int = 1,
    ) -> str:
        """Format citations using the specified style."""
        if style == "footnote":
            return self.footnote(results, start_index=start_index)
        elif style == "numbered":
            return self.numbered(results, start_index=start_index)
        else:
            return self.inline(results, start_index=start_index)

    @staticmethod
    def attach_to_content(
        content: str,
        citation: Citation,
        style: str = "inline",
        index: int = 1,
    ) -> str:
        """Attach citation to a single content string."""
        formatter = CitationFormatter()
        formatted = formatter.format(
            [CitationResult(content=content, citation=citation)],
            style=style,
            start_index=index,
        )
        return f"{content}\n{formatted}"
