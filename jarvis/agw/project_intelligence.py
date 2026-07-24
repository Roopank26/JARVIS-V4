"""
JARVIS-V8 AGW — Project Intelligence.

Continuously builds and evolves the Project Intelligence Graph for each
repository understood by JARVIS.

Every repository should have:
- Architecture map
- Dependency graph
- Knowledge graph
- Issue graph
- Technical debt score
- Complexity score
- Documentation coverage
- Test coverage
- Performance profile
- Historical evolution
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ProjectIntelligence:
    """Intelligence data for a single project."""

    project_path: str
    project_name: str
    architecture_map: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    knowledge_graph_nodes: list[dict[str, Any]] = field(default_factory=list)
    issue_graph: list[dict[str, Any]] = field(default_factory=list)
    technical_debt_score: float | None = None
    complexity_score: float | None = None
    documentation_coverage: float | None = None
    test_coverage_estimate: float | None = None
    performance_profile: dict[str, Any] = field(default_factory=dict)
    historical_evolution: list[dict[str, Any]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)
    snapshot_count: int = 0


class ProjectIntelligenceManager:
    """Manages Project Intelligence for all known repositories.

    For each project, periodically:
    1. Re-analyze architecture.
    2. Update dependency graph.
    3. Sync with knowledge graph.
    4. Detect new issues.
    5. Update scores.
    6. Record history.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        self._intel: dict[str, ProjectIntelligence] = {}

    def get_or_create(self, project_path: str) -> ProjectIntelligence:
        project_path = os.path.abspath(project_path)
        if project_path not in self._intel:
            project_name = os.path.basename(project_path)
            self._intel[project_path] = ProjectIntelligence(
                project_path=project_path,
                project_name=project_name,
            )
            self._bus.emit(EventType.STATUS, {"project_intel": "created", "path": project_name})
        return self._intel[project_path]

    async def update_project(self, project_path: str) -> dict[str, Any]:
        intel = self.get_or_create(project_path)
        self._bus.emit(EventType.STATUS, {"project_intel": "update_started", "path": intel.project_name})

        try:
            intel.architecture_map = await self._load_architecture(project_path)
            intel.dependency_graph = await self._load_dependencies(project_path)
            intel.technical_debt_score = await self._compute_debt_score(project_path)
            intel.test_coverage_estimate = await self._estimate_test_coverage(project_path)
            intel.complexity_score = self._compute_complexity_score(project_path)
            intel.documentation_coverage = self._estimate_doc_coverage(project_path)
            intel.issue_graph = self._detect_issues(project_path)
            self._sync_knowledge_graph(intel)
            intel.updated_at = time.time()
            intel.snapshot_count += 1

            self._bus.emit(EventType.STATUS, {"project_intel": "updated", "path": intel.project_name})
        except Exception as exc:
            logger.debug("Project intelligence update failed: %s", exc)

        return self.serialize(intel)

    async def _load_architecture(self, project_path: str) -> dict[str, Any]:
        arch: dict[str, Any] = {}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            arch = analyzer.get_architecture()
        except Exception:
            pass
        return arch

    async def _load_dependencies(self, project_path: str) -> dict[str, Any]:
        deps: dict[str, Any] = {"libraries": [], "risk": "low"}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            dep_list = analyzer.get_dependencies()
            deps["libraries"] = list(dep_list)[:50]
        except Exception:
            pass
        return deps

    async def _compute_debt_score(self, project_path: str) -> float | None:
        score: float | None = None
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            stats = analyzer.get_statistics()
            total = stats.total_functions + stats.total_classes
            if total > 0:
                score = round(stats.complexity / total, 4)
        except Exception:
            pass
        return score

    async def _estimate_test_coverage(self, project_path: str) -> float | None:
        coverage: float | None = None
        try:
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

    def _compute_complexity_score(self, project_path: str) -> float | None:
        complexity: float | None = None
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            stats = analyzer.get_statistics()
            complexity = float(stats.complexity)
        except Exception:
            pass
        return complexity

    def _estimate_doc_coverage(self, project_path: str) -> float | None:
        coverage: float | None = None
        try:
            total = docs = 0
            for root, _, files in os.walk(project_path):
                for fname in files:
                    if fname.endswith((".py",)):
                        total += 1
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath) as f:
                                content = f.read()
                            if '"""' in content or "'''" in content:
                                docs += 1
                        except Exception:
                            continue
            if total > 0:
                coverage = round((docs / total) * 100, 1)
        except Exception:
            pass
        return coverage

    def _detect_issues(self, project_path: str) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(project_path)
            security = analyzer.scan_security()
            issues = security.get("issues", [])[:50]
        except Exception:
            pass
        return issues

    def _sync_knowledge_graph(self, intel: ProjectIntelligence) -> None:
        try:
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )
            graph = get_knowledge_graph()
            graph.get_or_create_node("project", intel.project_name, {
                "path": intel.project_path,
                "language": "auto-detected",
                "debt_score": intel.technical_debt_score,
                "complexity": intel.complexity_score,
                "test_coverage": intel.test_coverage_estimate,
                "doc_coverage": intel.documentation_coverage,
            })
        except Exception:
            pass

    def serialize(self, intel: ProjectIntelligence) -> dict[str, Any]:
        return {
            "project_path": intel.project_path,
            "project_name": intel.project_name,
            "technical_debt_score": intel.technical_debt_score,
            "complexity_score": intel.complexity_score,
            "test_coverage_estimate": intel.test_coverage_estimate,
            "documentation_coverage": intel.documentation_coverage,
            "issues_count": len(intel.issue_graph),
            "snapshot_count": intel.snapshot_count,
            "updated_at": intel.updated_at,
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "tracked_projects": len(self._intel),
            "projects": [(p.project_name, p.snapshot_count, p.updated_at) for p in self._intel.values()],
        }


_manager_instance: ProjectIntelligenceManager | None = None


def get_project_intelligence() -> ProjectIntelligenceManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ProjectIntelligenceManager()
    return _manager_instance
