"""
Test generator skill for JARVIS.
Generates pytest unit tests for a code file.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class TestGeneratorSkill:
    """Generate unit tests for a code file."""

    description = "Generate pytest unit tests"

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
                "You are a QA engineer. Generate clean pytest unit tests for the provided code. "
                "Use assertions and parametrize where appropriate. Do not add explanations."
            )
            prompt = f"File: {path.name}\n\nCode:\n{code}\n\nGenerate pytest tests."
            tests = await self.llm.generate(system=system, prompt=prompt, temperature=0.2)
        except Exception as e:
            logger.warning("LLM test generation failed: %s", e)
            tests = self._static_tests(code, path.name)

        return tests.strip() or "Test generation failed."

    def _static_tests(self, code: str, file_name: str) -> str:
        module_name = Path(file_name).stem
        lines = [
            "import pytest",
            f"from {module_name} import *",
            "",
            "",
        ]
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    tests = f"""
def test_{node.name}():
    # TODO: implement test for {node.name}
    assert True


"""
                    lines.append(tests)
        except Exception:
            pass
        return "\n".join(lines)
