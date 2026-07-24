"""
Documentation generator skill for JARVIS.
Generates markdown documentation for a code file.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class DocsGeneratorSkill:
    """Generate documentation for a code file."""

    description = "Generate markdown documentation with examples"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return f"File not found: {file_path}"

        try:
            code = path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Unable to read file: {e}"

        if not code.strip():
            return "File is empty."

        try:
            system = (
                "You are a technical writer. Generate concise markdown documentation "
                "for the provided code file. Include a module summary, public functions/classes, "
                "parameters, return values, and one short usage example."
            )
            prompt = f"File: {path.name}\n\nCode:\n{code}\n\nGenerate markdown documentation."
            docs = await self.llm.generate(system=system, prompt=prompt, temperature=0.2)
        except Exception as e:
            logger.warning("LLM docs generation failed: %s", e)
            docs = self._static_docs(code, path.name)

        return docs.strip() or "Documentation generation failed."

    def _static_docs(self, code: str, file_name: str) -> str:
        lines: list[str] = [f"# {file_name}\n"]
        try:
            tree = ast.parse(code)
            lines.append("## Summary\n")
            lines.append("Static analysis summary.\n")
            lines.append("## Functions\n")
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    lines.append(f"### `{node.name}({', '.join(args)})`\n")
                    lines.append("Description not available.\n")
            lines.append("## Classes\n")
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    lines.append(f"### `class {node.name}`\n")
                    lines.append("Description not available.\n")
        except Exception:
            lines.append("Could not parse module.\n")
        return "\n".join(lines)
