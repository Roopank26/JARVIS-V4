"""
JARVIS PDF Expert - Advanced PDF operations and analysis.

Provides text extraction, table extraction, summarization, comparison,
image extraction, and conversational PDF interaction.
"""

from __future__ import annotations

import asyncio
import difflib
import importlib.util
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PDFExpertError(Exception):
    """Base exception for PDF Expert errors."""


class PDFExpert:
    """PDF Expert for advanced PDF operations."""

    def __init__(self) -> None:
        self._fitz_available = self._check_fitz()
        self._pdfplumber_available = self._check_pdfplumber()
        self._tabula_available = self._check_tabula()

    def _check_fitz(self) -> bool:
        return importlib.util.find_spec("fitz") is not None

    def _check_pdfplumber(self) -> bool:
        return importlib.util.find_spec("pdfplumber") is not None

    def _check_tabula(self) -> bool:
        return importlib.util.find_spec("tabula") is not None

    def _get_fitz(self):
        if not self._fitz_available:
            raise PDFExpertError("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
        import fitz
        return fitz

    async def get_page_count(self, pdf_path: str) -> int:
        """Return the number of pages in a PDF."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        fitz = self._get_fitz()
        doc = fitz.open(str(path))
        count = len(doc)
        doc.close()
        return count

    async def extract_text(self, pdf_path: str) -> str:
        """Extract all text from a PDF, concatenated page by page."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        fitz = self._get_fitz()
        doc = fitz.open(str(path))
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n--- Page Break ---\n\n".join(pages)

    async def extract_images(self, pdf_path: str) -> list[str]:
        """Extract embedded images from a PDF and save them to a temp directory."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        fitz = self._get_fitz()
        doc = fitz.open(str(path))
        output_dir = Path(os.environ.get("TEMP", ".")) / "jarvis_pdf_images"
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: list[str] = []
        for page_index, page in enumerate(doc):
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                stem = f"{path.stem}_p{page_index + 1}_img{img_index}"
                ext = ".png"
                img_path = output_dir / f"{stem}{ext}"
                pix.save(str(img_path))
                saved.append(str(img_path))
                pix = None
        doc.close()
        return saved

    async def extract_tables(self, pdf_path: str) -> list[dict[str, Any]]:
        """Extract tables from a PDF using tabula-py, pdfplumber, or fitz fallback."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        tables: list[dict[str, Any]] = []
        if self._tabula_available:
            tables = await asyncio.to_thread(self._extract_tables_tabula, str(path))
            if tables:
                return tables
        if self._pdfplumber_available:
            tables = await asyncio.to_thread(self._extract_tables_pdfplumber, str(path))
            if tables:
                return tables
        tables = await asyncio.to_thread(self._extract_tables_fitz, str(path))
        return tables

    def _extract_tables_tabula(self, pdf_path: str) -> list[dict[str, Any]]:
        import tabula

        dfs = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
        result = []
        for i, df in enumerate(dfs):
            if df.empty:
                continue
            result.append({"page": i + 1, "headers": df.columns.tolist(), "rows": df.values.tolist()})
        return result

    def _extract_tables_pdfplumber(self, pdf_path: str) -> list[dict[str, Any]]:
        import pdfplumber

        result = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                raw_tables = page.extract_tables() or []
                for tbl in raw_tables:
                    if not tbl:
                        continue
                    headers = tbl[0] if tbl else []
                    rows = tbl[1:] if len(tbl) > 1 else []
                    result.append({"page": page_index, "headers": headers, "rows": rows})
        return result

    def _extract_tables_fitz(self, pdf_path: str) -> list[dict[str, Any]]:
        fitz = self._get_fitz()
        doc = fitz.open(pdf_path)
        result = []
        for page_index, page in enumerate(doc, start=1):
            tabs = page.find_tables()
            for tab in tabs:
                try:
                    data = tab.extract()
                    if not data:
                        continue
                    result.append({"page": page_index, "headers": data[0], "rows": data[1:]})
                except Exception:
                    continue
        doc.close()
        return result

    async def summarize_pdf(self, pdf_path: str, max_length: int = 1000) -> str:
        """Generate a text summary of the PDF using the configured LLM."""
        text = await self.extract_text(pdf_path)
        if not text.strip():
            return "(PDF is empty or image-only)"
        prompt = (
            "Summarize the following PDF content concisely. "
            f"Keep the summary under {max_length} characters.\n\n{text[:12000]}"
        )
        response = await self._call_llm(prompt)
        summary = response.get("content", "")
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(" ", 1)[0] + "..."
        return summary

    async def chat_with_pdf(self, pdf_path: str, question: str) -> str:
        """Ask a question about the PDF using the configured LLM."""
        text = await self.extract_text(pdf_path)
        if not text.strip():
            return "(PDF is empty or image-only)"
        context = text[:16000]
        prompt = (
            "You are a helpful assistant. Answer the user's question based ONLY on the following PDF content. "
            "If the answer is not in the content, say 'Not found in the document.'\n\n"
            f"{context}\n\nQuestion: {question}"
        )
        response = await self._call_llm(prompt)
        return response.get("content", "")

    async def compare_pdfs(self, pdf_a: str, pdf_b: str) -> dict[str, Any]:
        """Compare two PDFs and return a structured similarity report."""
        text_a = await self.extract_text(pdf_a)
        text_b = await self.extract_text(pdf_b)
        pages_a = [p for p in text_a.split("\n\n--- Page Break ---\n\n") if p.strip()]
        pages_b = [p for p in text_b.split("\n\n--- Page Break ---\n\n") if p.strip()]
        max_pages = max(len(pages_a), len(pages_b))
        page_diffs = []
        for i in range(max_pages):
            a = pages_a[i] if i < len(pages_a) else ""
            b = pages_b[i] if i < len(pages_b) else ""
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            page_diffs.append(
                {
                    "page": i + 1,
                    "ratio": round(ratio, 4),
                    "added_chars": max(0, len(b) - len(a)),
                    "removed_chars": max(0, len(a) - len(b)),
                }
            )
        overall_ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
        comparison = {
            "pdf_a": pdf_a,
            "pdf_b": pdf_b,
            "pages_a": len(pages_a),
            "pages_b": len(pages_b),
            "overall_similarity": round(overall_ratio, 4),
            "page_diffs": page_diffs,
        }
        return comparison

    async def _call_llm(self, prompt: str) -> dict[str, Any]:
        try:
            from jarvis.api.providers import get_provider_manager

            manager = get_provider_manager()
            if not hasattr(manager, "primary_provider") or manager.primary_provider is None:
                return {"content": "(No LLM provider available for this operation.)"}
            provider = manager.providers.get(manager.primary_provider)
            if provider is None:
                return {"content": "(LLM provider not found.)"}
            response = await provider.generate(prompt=prompt)
            return {"content": getattr(response, "content", "")}
        except Exception as exc:
            logger.debug("LLM call failed: %s", exc)
            return {"content": f"(LLM error: {exc})", "error": str(exc)}
