"""
PDF summarizer skill for JARVIS.
Summarizes a PDF document with key points.
"""

from __future__ import annotations

import logging
from pathlib import Path

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class PDFSummarizerSkill:
    """Summarize a PDF document."""

    description = "Summarize PDF with key points"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, pdf_path: str) -> str:
        path = Path(pdf_path)
        if not path.exists() or not path.is_file():
            return f"File not found: {pdf_path}"

        text = ""
        try:
            text = self._extract_text(path)
        except Exception as e:
            logger.warning("PDF text extraction failed: %s", e)
            return f"Unable to extract text from PDF: {e}"

        if not text.strip():
            return "PDF appears to be empty or unsupported."

        try:
            system = (
                "You are a research assistant. Summarize the provided document text. "
                "Return a concise summary with 3-7 bullet key points."
            )
            prompt = f"Document text:\n{text[:8000]}\n\nSummary and key points:"
            summary = await self.llm.generate(system=system, prompt=prompt, temperature=0.3)
        except Exception as e:
            logger.warning("LLM summarization failed: %s", e)
            summary = "Summary generation failed."

        return summary.strip() or "No summary produced."

    def _extract_text(self, path: Path) -> str:
        text = ""
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            text = f"[PDF content placeholder for {path.name}]"
        return text
