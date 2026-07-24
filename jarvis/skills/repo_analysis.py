"""
Repository analysis skill for JARVIS.
Analyzes repository structure, dependencies, and health metrics.
"""

from __future__ import annotations

import ast
import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any

from jarvis.api.gemini import SimpleLLMClient
from jarvis.rag import get_rag_system

logger = logging.getLogger(__name__)


class RepoAnalysisSkill:
    """Analyze a repository structure and health."""

    description = "Analyze a repository's structure, dependencies, and health"

    def __init__(self) -> None:
        self.llm = SimpleLLMClient()
        self.rag = get_rag_system()

    async def execute(self, repo_path: str) -> dict[str, Any]:
        repo = Path(repo_path)
        if not repo.exists() or not repo.is_dir():
            return {"success": False, "error": f"Invalid repository path: {repo_path}"}

        file_count = self._count_files(repo)
        languages = self._detect_languages(repo)
        todos = self._count_todos(repo)
        complexity = self._estimate_complexity(repo)

        report = {
            "success": True,
            "repo_path": str(repo),
            "file_count": file_count,
            "languages": dict(languages),
            "todo_count": todos,
            "complexity_estimate": complexity,
            "health_score": self._health_score(file_count, todos, complexity),
        }
        return report

    def _count_files(self, repo: Path) -> int:
        count = 0
        for _root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
            count += len(files)
        return count

    def _detect_languages(self, repo: Path) -> Counter:
        extensions: Counter = Counter()
        for _root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in {".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp", ".rb", ".php"}:
                    extensions[ext] += 1
        return extensions

    def _count_todos(self, repo: Path) -> int:
        todo_count = 0
        keywords = ("# TODO", "// TODO", "/* TODO")
        for _root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
            for f in files:
                if not f.endswith((".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp", ".rb", ".php")):
                    continue
                path = Path(_root) / f
                try:
                    with open(path, encoding="utf-8", errors="ignore") as file:
                        for line in file:
                            if any(k in line for k in keywords):
                                todo_count += 1
                except Exception:
                    pass
        return todo_count

    def _estimate_complexity(self, repo: Path) -> str:
        total_complexity = 0
        function_count = 0
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}]
            for f in files:
                if f.endswith(".py"):
                    path = Path(root) / f
                    try:
                        source = path.read_text(encoding="utf-8")
                        tree = ast.parse(source)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                complexity = self._cyclomatic(node)
                                total_complexity += complexity
                                function_count += 1
                    except Exception:
                        pass
        if function_count == 0:
            return "unknown"
        avg = total_complexity / function_count
        if avg < 5:
            return "low"
        if avg < 15:
            return "moderate"
        return "high"

    def _cyclomatic(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _health_score(self, file_count: int, todos: int, complexity: str) -> str:
        if file_count == 0:
            return "empty"
        score = 100
        if todos > 0:
            score -= min(20, todos)
        if complexity == "high":
            score -= 25
        elif complexity == "moderate":
            score -= 10
        if score >= 80:
            return "healthy"
        if score >= 60:
            return "fair"
        return "needs_attention"
