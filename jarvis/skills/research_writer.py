"""
Research writer skill for JARVIS.
Writes a structured research report on a topic.
"""

from __future__ import annotations

import logging

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class ResearchWriterSkill:
    """Write a structured research report on a topic."""

    description = "Generate a research report with citations"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, topic: str, sources: list[str] | None = None) -> str:
        if not topic.strip():
            return "No topic provided."

        source_context = ""
        if sources:
            try:
                for src in sources[:5]:
                    docs = []
                    if hasattr(self.rag, "hybrid_search") and self.rag.hybrid_search is not None:
                        try:
                            results = self.rag.hybrid_search.search(src, top_k=3)
                            for r in results:
                                docs.append(getattr(r, "text", str(r)))
                        except Exception:
                            pass
                    source_context += "\n".join(docs) + "\n"
            except Exception as e:
                logger.warning("RAG retrieval failed: %s", e)

        try:
            system = (
                "You are a researcher. Generate a structured research report with sections: "
                "Abstract, Introduction, Findings, Conclusion, and References. "
                "If sources are provided, cite them inline."
            )
            prompt = f"Topic: {topic}\n\nSources:\n{source_context[:6000]}\n\nWrite the report."
            report = await self.llm.generate(system=system, prompt=prompt, temperature=0.4)
        except Exception as e:
            logger.warning("LLM report generation failed: %s", e)
            report = f"Research report generation failed: {e}"

        return report.strip() or "No report produced."
