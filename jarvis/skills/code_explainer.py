"""
Code explainer skill for JARVIS.
Explains a code snippet or file in plain language.
"""

from __future__ import annotations

import ast
import logging

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class CodeExplainerSkill:
    """Explain a code snippet or file in plain language."""

    description = "Explain code in plain English with examples"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, code: str, language: str = "python") -> str:
        if not code.strip():
            return "No code provided."

        explanation = ""
        try:
            system = (
                "You are an expert software engineer. Explain the provided code "
                "in clear, plain English. Include purpose, inputs/outputs, and a short example if relevant."
            )
            prompt = f"Language: {language}\n\nCode:\n{code}\n\nExplain this code."
            explanation = await self.llm.generate(system=system, prompt=prompt, temperature=0.3)
        except Exception as e:
            logger.warning("LLM explanation failed: %s", e)
            explanation = self._static_explain(code, language)

        return explanation.strip() or "I could not explain this code."

    def _static_explain(self, code: str, language: str) -> str:
        try:
            if language.lower() == "python":
                tree = ast.parse(code)
                nodes = []
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef):
                        nodes.append(f"defines function '{node.name}'")
                    elif isinstance(node, ast.ClassDef):
                        nodes.append(f"defines class '{node.name}'")
                    elif isinstance(node, ast.Assign):
                        nodes.append("assigns variables")
                    elif isinstance(node, ast.Import):
                        nodes.append("imports modules")
                summary = " and ".join(nodes) if nodes else "contains Python code"
                return f"This Python snippet {summary}."
        except Exception:
            pass
        return f"This is a {language} code snippet."
