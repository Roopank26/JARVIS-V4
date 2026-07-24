"""
JARVIS-V8 AGW — Work Session Mode.

When the owner starts working, JARVIS automatically:
1. Detects the current project
2. Loads memory, documentation, architecture, TODOs
3. Loads recent commits and research
4. Prepares an execution plan
5. Waits for the next instruction (with context already loaded)
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Loaded context for the current work session."""

    project_path: str
    project_name: str
    repository: str | None
    branch: str | None
    language: str
    framework: str | None
    architecture_summary: str
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    todos: list[str] = field(default_factory=list)
    recent_commits: list[dict[str, Any]] = field(default_factory=list)
    technical_debt_score: float | None = None
    test_coverage_estimate: float | None = None
    documentation_coverage: float | None = None
    active_goals: list[dict[str, Any]] = field(default_factory=list)
    recent_tasks: list[dict[str, Any]] = field(default_factory=list)
    research_notes: list[str] = field(default_factory=list)
    memory_snippets: list[dict[str, Any]] = field(default_factory=list)
    loaded_at: float = field(default_factory=lambda: datetime.now().timestamp())


class WorkSessionManager:
    """Manages the Work Session Mode experience.

    On activation:
      1. Detect project (workspace awareness, git repo detection).
      2. Load project memory from KnowledgeGraph.
      3. Load architecture map and dependency graph.
      4. Load TODOs.
      5. Load recent commits.
      6. Load related research.
      7. Load active goals.
      8. Build execution plan.

    The loaded context is then available to all Directors and Agents.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._session_context: ProjectContext | None = None
        self._is_active = False

    async def start_session(self, project_path: str | None = None) -> ProjectContext:
        """Start a new work session for the current project."""
        self._is_active = True
        self._bus.emit(EventType.STATUS, {"work_session": "started"})

        project_path = project_path or os.getcwd()
        logger.info("[WorkSession] Starting session for project: %s", project_path)

        repository = self._detect_repo(project_path)
        branch = self._detect_branch(project_path)
        language, framework = self._detect_stack(project_path)
        architecture = await self._load_architecture(project_path)
        dependency_graph = await self._load_dependencies(project_path)
        todos = self._extract_todos(project_path)
        recent_commits = self._get_recent_commits(project_path)
        technical_debt_score = await self._compute_debt_score(project_path)
        test_coverage = await self._estimate_coverage(project_path)
        active_goals = self._load_active_goals()
        research_notes = self._load_research_notes(project_path)
        memory_snippets = self._load_project_memory(project_path)

        project_name = os.path.basename(os.path.abspath(project_path))

        self._session_context = ProjectContext(
            project_path=project_path,
            project_name=project_name,
            repository=repository,
            branch=branch,
            language=language,
            framework=framework,
            architecture_summary=architecture.get("summary", ""),
            dependency_graph=dependency_graph,
            todos=todos,
            recent_commits=recent_commits,
            technical_debt_score=technical_debt_score,
            test_coverage_estimate=test_coverage,
            active_goals=active_goals,
            research_notes=research_notes,
            memory_snippets=memory_snippets,
        )

        logger.info("[WorkSession] Context loaded for %s", project_name)
        self._bus.emit(EventType.STATUS, {"work_session": "ready", "context": self._session_context_to_dict()})
        return self._session_context

    def get_context(self) -> ProjectContext | None:
        return self._session_context

    def end_session(self) -> None:
        """End the current work session."""
        self._session_context = None
        self._is_active = False
        self._bus.emit(EventType.STATUS, {"work_session": "ended"})

    def _session_context_to_dict(self) -> dict[str, Any]:
        if not self._session_context:
            return {}
        ctx = self._session_context
        return {
            "project_name": ctx.project_name,
            "repository": ctx.repository,
            "branch": ctx.branch,
            "language": ctx.language,
            "framework": ctx.framework,
            "architecture_summary": ctx.architecture_summary,
            "todos": ctx.todos,
            "recent_commits": ctx.recent_commits,
            "technical_debt_score": ctx.technical_debt_score,
            "test_coverage_estimate": ctx.test_coverage_estimate,
            "active_goals": ctx.active_goals,
            "research_notes": ctx.research_notes,
            "loaded_at": ctx.loaded_at,
        }

    def _detect_repo(self, project_path: str) -> str | None:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", project_path, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _detect_branch(self, project_path: str) -> str | None:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", project_path, "branch", "--show-current"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip() or None
        except Exception:
            pass
        return None

    def _detect_stack(self, project_path: str) -> tuple[str, str | None]:
        language = "unknown"
        framework = None
        try:
            if os.path.exists(os.path.join(project_path, "pom.xml")):
                language, framework = "java", "maven"
            elif os.path.exists(os.path.join(project_path, "build.gradle")) or os.path.exists(os.path.join(project_path, "build.gradle.kts")):
                language, framework = "java/kotlin", "gradle"
            elif os.path.exists(os.path.join(project_path, "go.mod")):
                language, framework = "go", "go_modules"
            elif os.path.exists(os.path.join(project_path, "Cargo.toml")):
                language, framework = "rust", "cargo"
            elif os.path.exists(os.path.join(project_path, "package.json")):
                language = "javascript/typescript"
                framework = self._detect_js_framework(project_path)
            elif os.path.exists(os.path.join(project_path, "pyproject.toml")):
                language = "python"
                framework = self._detect_py_framework(project_path)
            elif os.path.exists(os.path.join(project_path, "requirements.txt")):
                language = "python"
        except Exception:
            pass
        return language, framework

    def _detect_js_framework(self, project_path: str) -> str | None:
        for fname in ["next.config.js", "next.config.mjs", "vite.config.js", "vue.config.js"]:
            if os.path.exists(os.path.join(project_path, fname)):
                return fname.split(".")[0]
        return "unknown"

    def _detect_py_framework(self, project_path: str) -> str | None:
        try:
            with open(os.path.join(project_path, "pyproject.toml")) as f:
                content = f.read()
                for field in ["django", "flask", "fastapi", "uvicorn"]:
                    if field in content.lower():
                        return field
        except Exception:
            pass
        return "unknown"

    async def _load_architecture(self, project_path: str) -> dict[str, Any]:
        architecture: dict[str, Any] = {"summary": "", "components": []}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            architecture = analyzer.get_architecture()
        except Exception:
            pass
        return architecture

    async def _load_dependencies(self, project_path: str) -> dict[str, Any]:
        deps: dict[str, Any] = {"libraries": [], "risk": "low"}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            dependency_list = analyzer.get_dependencies()
            deps["libraries"] = list(dependency_list)[:50]
        except Exception:
            pass
        return deps

    def _extract_todos(self, project_path: str) -> list[str]:
        todos: list[str] = []
        try:
            for root, _, files in os.walk(project_path):
                for fname in files:
                    if not fname.endswith((".py", ".js", ".ts", ".md", ".txt")):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath) as f:
                            for i, line in enumerate(f, 1):
                                if "TODO" in line or "FIXME" in line or "HACK" in line:
                                    todos.append(f"{fpath}:{i}: {line.strip()}")
                    except Exception:
                        continue
        except Exception:
            pass
        return todos[:50]

    def _get_recent_commits(self, project_path: str, limit: int = 10) -> list[dict[str, Any]]:
        commits: list[dict[str, Any]] = []
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", project_path, "log", f"-{limit}", "--name-only", "--pretty=format:%H %s %an %ad", "--date=relative"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                commit_blocks = result.stdout.split("\n\n")
                for block in commit_blocks:
                    lines = block.strip().splitlines()
                    if not lines:
                        continue
                    header = lines[0]
                    files = lines[1:] if len(lines) > 1 else []
                    commits.append({
                        "header": header,
                        "files": files,
                    })
        except Exception:
            pass
        return commits

    async def _compute_debt_score(self, project_path: str) -> float | None:
        score: float | None = None
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            stats = analyzer.get_statistics()
            total = stats.total_functions + stats.total_classes
            complexity = stats.complexity
            if total > 0:
                score = round(complexity / total, 2)
        except Exception:
            pass
        return score

    async def _estimate_coverage(self, project_path: str) -> float | None:
        coverage: float | None = None
        try:
            import os
            src_count = test_count = 0
            for _root, _, files in os.walk(project_path):
                for fname in files:
                    if fname.startswith("test_") and fname.endswith(".py"):
                        test_count += 1
                    elif fname.endswith(".py") and not fname.startswith("test_") and fname != "setup.py":
                        src_count += 1
            if src_count > 0:
                coverage = round((test_count / src_count) * 100, 1)
        except Exception:
            pass
        return coverage

    def _load_active_goals(self) -> list[dict[str, Any]]:
        goals: list[dict[str, Any]] = []
        try:
            from jarvis.goals import get_goal_engine  # type: ignore[attr-defined]
            ge = get_goal_engine()
            for g in ge.list_goals():
                goals.append({
                    "goal_id": getattr(g, "goal_id", ""),
                    "title": getattr(g, "title", ""),
                    "status": getattr(g, "status", ""),
                })
        except Exception:
            pass
        return goals

    def _load_research_notes(self, project_path: str) -> list[str]:
        notes: list[str] = []
        try:
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )
            graph = get_knowledge_graph()
            project_name = os.path.basename(os.path.abspath(project_path))
            related = []
            with contextlib.suppress(Exception):
                related = graph.search(project_name)
            notes = [" ".join(str(x) for x in r.get("data", {}).get("properties", {}).values()) for r in related[:20]]
        except Exception:
            pass
        return notes

    def _load_project_memory(self, project_path: str) -> list[dict[str, Any]]:
        snippets: list[dict[str, Any]] = []
        try:
            project_name = os.path.basename(os.path.abspath(project_path)) if project_path else ""
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )
            graph = get_knowledge_graph()
            hits = graph.search(project_name)
            snippets = [hit["data"] for hit in hits[:10]]
        except Exception:
            pass
        return snippets
