"""
File comparison skill for JARVIS.
Compares two files or directories.
"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import Any

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class FileComparisonSkill:
    """Compare two files or directories."""

    description = "Compare files/dirs with diffs"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, path_a: str, path_b: str) -> dict[str, Any]:
        p_a = Path(path_a)
        p_b = Path(path_b)

        if not p_a.exists() and not p_b.exists():
            return {"success": False, "error": "Both paths are missing."}

        if p_a.is_file() and p_b.is_file():
            return await self._compare_files(p_a, p_b)
        if p_a.is_dir() and p_b.is_dir():
            return self._compare_dirs(p_a, p_b)
        if p_a.is_file():
            return {
                "success": False,
                "error": f"Type mismatch: {path_a} is a file but {path_b} is a directory or missing.",
            }
        return {
            "success": False,
            "error": f"Type mismatch: {path_a} is a directory but {path_b} is a file or missing.",
        }

    async def _compare_files(self, p_a: Path, p_b: Path) -> dict[str, Any]:
        try:
            text_a = p_a.read_text(encoding="utf-8", errors="ignore").splitlines()
            text_b = p_b.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            return {"success": False, "error": f"Unable to read files: {e}"}

        diff = list(difflib.unified_diff(text_a, text_b, fromfile=str(p_a), tofile=str(p_b), lineterm=""))
        additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        summary = ""
        try:
            system = "You are a code reviewer. Summarize the diff succinctly."
            prompt = (
                f"Diff between {p_a.name} and {p_b.name}:\n"
                + "\n".join(diff[:200] or ["(no changes)"])
                + "\n\nSummarize changes."
            )
            summary = await self.llm.generate(system=system, prompt=prompt, temperature=0.2)
        except Exception as e:
            logger.warning("LLM diff summary failed: %s", e)
            summary = "Diff summary unavailable."

        return {
            "success": True,
            "type": "file",
            "path_a": str(p_a),
            "path_b": str(p_b),
            "additions": additions,
            "deletions": deletions,
            "diff_lines": len(diff),
            "summary": summary.strip(),
        }

    def _compare_dirs(self, p_a: Path, p_b: Path) -> dict[str, Any]:
        files_a = {f.relative_to(p_a): f for f in p_a.rglob("*") if f.is_file()}
        files_b = {f.relative_to(p_b): f for f in p_b.rglob("*") if f.is_file()}

        only_a = sorted(str(k) for k in files_a if k not in files_b)
        only_b = sorted(str(k) for k in files_b if k not in files_a)
        common = sorted(str(k) for k in files_a if k in files_b)

        return {
            "success": True,
            "type": "directory",
            "path_a": str(p_a),
            "path_b": str(p_b),
            "only_in_a": only_a,
            "only_in_b": only_b,
            "common": common,
        }
