"""
JARVIS-V8 AGW — Director System.

Nine Directors coordinate specialized agents, encode workflows, and own
domain-specific project intelligence.  Directors wrap existing subsystems
(MemoryManager, ResearchAgent, RepositoryAnalyzer, GoalEngine, etc.)
through a unified control surface without replacing any backend logic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from jarvis.events import EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class DirectorWorkflow:
    """A workflow that a Director can execute."""

    name: str
    description: str
    steps: list[str] = field(default_factory=list)
    risk_level: str = "safe"  # safe, moderate, high
    requires_owner_approval: bool = False


class BaseDirector(ABC):
    """Base class for all JARVIS AGW Directors.

    Each Director owns a domain, coordinates relevant agents,
    and executes end-to-end workflows.

    Design:
    - Does not duplicate existing subsystem logic; delegates to
      existing agents, memory, knowledge graph, and tool registry.
    - Emits events for observability on the shared EventBus.
    """

    DOMAIN: str = "base"
    CAPABILITIES: list[str] = []
    WORKFLOWS: list[DirectorWorkflow] = []

    def __init__(self, bus: EventBus | None = None, owner_id: str = "owner"):
        self._bus = bus or get_event_bus()
        self._owner_id = owner_id
        self._context: dict[str, Any] = {}

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the director and its dependent subsystems."""

    @abstractmethod
    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute an instruction within the director's domain.

        Returns a structured result dict with status, outputs, and artifacts.
        """

    def get_capabilities(self) -> list[str]:
        return list(self.CAPABILITIES)

    def get_workflows(self) -> list[DirectorWorkflow]:
        return list(self.WORKFLOWS)

    def _emit(self, event_type: EventType, data: dict[str, Any]) -> None:
        try:
            self._bus.emit(event_type, data)
        except Exception as exc:
            logger.debug("Director event emission failed: %s", exc)

    def _get_workspace(self) -> dict[str, Any]:
        workspace: dict[str, Any] = {}
        try:
            from jarvis.workspace.awareness import (
                get_workspace_awareness,  # type: ignore[attr-defined]
            )
            awareness = get_workspace_awareness()
            state = awareness.get_state()
            workspace = {
                "repo": state.repo,
                "branch": state.branch,
                "directory": state.directory,
                "recent_files": state.recent_files,
                "editor": state.editor,
            }
        except Exception:
            pass
        return workspace

    def _get_memory(self) -> dict[str, Any]:
        memory: dict[str, Any] = {}
        try:
            from jarvis.memory.enhanced import get_enhanced_memory  # type: ignore[attr-defined]
            mem = get_enhanced_memory()
            memories = getattr(mem, "memories", [])
            memory = {
                "count": len(memories),
                "recent": memories[-5:] if memories else [],
            }
        except Exception:
            pass
        return memory

    def _get_knowledge_graph(self) -> dict[str, Any]:
        kg: dict[str, Any] = {}
        try:
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )
            graph = get_knowledge_graph()
            kg = graph.get_stats()
        except Exception:
            pass
        return kg

    def _get_goal_engine(self) -> dict[str, Any]:
        goals: dict[str, Any] = {}
        try:
            from jarvis.goals import get_goal_engine  # type: ignore[attr-defined]
            ge = get_goal_engine()
            goals = ge.health_check()
        except Exception:
            pass
        return goals


class SoftwareEngineeringDirector(BaseDirector):
    DOMAIN = "software_engineering"
    CAPABILITIES = [
        "repo_analysis",
        "architecture_mapping",
        "dependency_graph",
        "code_smell_detection",
        "technical_debt_tracking",
        "test_generation",
        "documentation_update",
        "performance_monitoring",
        "pull_request_review",
        "release_notes",
        "complexity_estimation",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="repository_audit",
            description="Full repository audit: architecture, complexity, bugs, code smells, and docs.",
            steps=[
                "detect_repo",
                "run_repository_analysis",
                "check_dependencies",
                "scan_security",
                "scan_tests",
                "generate_report",
            ],
            risk_level="safe",
        ),
        DirectorWorkflow(
            name="pull_request_review",
            description="Review uncommitted or recent PR changes.",
            steps=["detect_changes", "analyze_diff", "check_tests", "check_security", "generate_review"],
            risk_level="moderate",
            requires_owner_approval=True,
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[SoftwareEngineeringDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        task = ctx.get("task", "repository_audit")
        workspace = self._get_workspace()
        repo_path = ctx.get("repo_path") or workspace.get("directory")

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "task": task, "state": "started"})
        result: dict[str, Any] = {"task": task, "status": "completed", "workspace": workspace}

        try:
            if task == "repository_audit":
                result["report"] = await self._repository_audit(repo_path, ctx)
            elif task == "pull_request_review":
                result["report"] = await self._pull_request_review(repo_path, ctx)
            elif task == "architecture_map":
                result["report"] = await self._architecture_map(repo_path)
            elif task == "dependency_graph":
                result["report"] = await self._dependency_graph(repo_path)
            elif task == "code_smell_scan":
                result["report"] = await self._code_smell_scan(repo_path)
            else:
                result["status"] = "error"
                result["error"] = f"Unknown task: {task}"
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "task": task, "state": result["status"]})
        return result

    async def _repository_audit(self, repo_path: str | None, ctx: dict[str, Any]) -> dict[str, Any]:
        audit: dict[str, Any] = {"repo": repo_path}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(repo_path)
            if repo_path:
                stats = analyzer.get_statistics()
                architecture = analyzer.get_architecture()
                audit["statistics"] = stats
                audit["architecture"] = architecture
                audit["file_count"] = len(analyzer.get_python_files()) if hasattr(analyzer, "get_python_files") else 0
                security = analyzer.scan_security()
                audit["security_issues_count"] = len(security.get("issues", []))
        except Exception as exc:
            audit["error"] = str(exc)
        return audit

    async def _pull_request_review(self, repo_path: str | None, ctx: dict[str, Any]) -> dict[str, Any]:
        review: dict[str, Any] = {"repo": repo_path}
        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
            analyzer = RepositoryAnalyzer(repo_path)
            review["security_issues"] = analyzer.scan_security()
            review["test_coverage"] = await self._estimate_test_coverage(repo_path)
        except Exception as exc:
            review["error"] = str(exc)
        return review

    async def _architecture_map(self, repo_path: str | None) -> dict[str, Any]:
        architecture: dict[str, Any] = {}
        try:
            if repo_path:
                from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
                analyzer = RepositoryAnalyzer(repo_path)
                architecture = analyzer.get_architecture()
        except Exception as exc:
            architecture["error"] = str(exc)
        return architecture

    async def _dependency_graph(self, repo_path: str | None) -> dict[str, Any]:
        graph: dict[str, Any] = {"nodes": [], "edges": []}
        try:
            if repo_path:
                from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
                analyzer = RepositoryAnalyzer(repo_path)
                deps = analyzer.get_dependencies()
                graph["dependency_count"] = len(deps)
                graph["sample_dependencies"] = list(deps)[:50]
        except Exception as exc:
            graph["error"] = str(exc)
        return graph

    async def _code_smell_scan(self, repo_path: str | None) -> dict[str, Any]:
        smells: dict[str, Any] = {"issues": []}
        try:
            if repo_path:
                from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
                analyzer = RepositoryAnalyzer(repo_path)
                files = analyzer.get_python_files() if hasattr(analyzer, "get_python_files") else []
                smells["python_files"] = len(files)
                total_complexity = 0
                for f in files[:20]:
                    fa = analyzer.analyze_file(str(f)) if hasattr(analyzer, "analyze_file") else None
                    if fa:
                        total_complexity += fa.complexity
                        smells["issues"].extend(fa.issues)
                smells["estimated_complexity"] = total_complexity
        except Exception as exc:
            smells["error"] = str(exc)
        return smells

    async def _estimate_test_coverage(self, repo_path: str | None) -> dict[str, Any]:
        coverage: dict[str, Any] = {"estimated": 0.0}
        try:
            if repo_path:
                import os
                src_count = test_count = 0
                for _root, _, files in os.walk(repo_path):
                    for fname in files:
                        if fname.startswith("test_") and fname.endswith(".py"):
                            test_count += 1
                        elif fname.endswith(".py") and not fname.startswith("test_"):
                            src_count += 1
                coverage["source_files"] = src_count
                coverage["test_files"] = test_count
                coverage["estimated"] = round((test_count / max(src_count, 1)) * 100, 1)
        except Exception as exc:
            coverage["error"] = str(exc)
        return coverage


class ResearchDirector(BaseDirector):
    DOMAIN = "research"
    CAPABILITIES = [
        "web_search",
        "multi_source_research",
        "citation_synthesis",
        "research_report",
        "technology_evaluation",
        "comparison_report",
        "learning_plan",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="deep_research",
            description="Multi-stage research on a topic with citations and synthesis.",
            steps=["gather_sources", "synthesize", "validate", "generate_report"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[ResearchDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "instruction": instruction, "state": "started"})
        result: dict[str, Any] = {"instruction": instruction, "status": "completed", "sources": [], "report": ""}

        try:
            from jarvis.research.research_agent import (
                get_research_agent,  # type: ignore[attr-defined]
            )
            agent = get_research_agent()
            research_result = await agent.research_topic(
                topic=instruction,
                depth=ctx.get("depth", "standard"),
                sources=ctx.get("sources"),
            )
            result["report"] = research_result.summary if hasattr(research_result, "summary") else str(research_result)
            result["sources"] = [
                {"url": s.url, "title": s.title, "relevance": s.relevance_score}
                for s in getattr(research_result, "sources", [])
            ]
            try:
                from jarvis.evolution.knowledge_graph_v2 import (
                    get_knowledge_graph,  # type: ignore[attr-defined]
                )
                graph = get_knowledge_graph()
                graph.add_node("research", instruction, {"query": instruction, "depth": ctx.get("depth", "standard")})
            except Exception:
                pass
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class ExecutiveDirector(BaseDirector):
    DOMAIN = "executive"
    CAPABILITIES = [
        "schedule_management",
        "goal_management",
        "deadline_tracking",
        "daily_brief",
        "weekly_review",
        "monthly_review",
        "quarterly_planning",
        "yearly_planning",
        "career_roadmap",
        "learning_roadmap",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="daily_brief",
            description="Generate morning brief with schedule, goals, and priorities.",
            steps=["load_calendar", "load_goals", "load_tasks", "generate_brief"],
            risk_level="safe",
        ),
        DirectorWorkflow(
            name="weekly_review",
            description="Weekly review: completed tasks, goal progress, next priorities.",
            steps=["fetch_completed_tasks", "assess_goal_progress", "identify_priorities", "generate_summary"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[ExecutiveDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        task = ctx.get("period", "daily_brief")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "task": task, "state": "started"})
        result: dict[str, Any] = {"task": task, "status": "completed", "brief": ""}

        try:
            goal_engine = self._get_goal_engine().get("goals", 0)
            memory = self._get_memory()
            goals_list = []
            try:
                from jarvis.goals import get_goal_engine  # type: ignore[attr-defined]
                ge = get_goal_engine()
                goals_list = [{"goal_id": g.goal_id, "title": g.title, "status": g.status} for g in ge.list_goals()]
            except Exception:
                pass

            if task == "daily_brief":
                result["brief"] = (
                    f"Daily Brief\n"
                    f"- Active goals: {goal_engine}\n"
                    f"- Memory entries: {memory.get('count', 0)}\n"
                    f"- Recent memories: {memory.get('recent', [])[-3:]}\n"
                    f"- Goals tracked: {len(goals_list)}\n"
                    f"- Top goals: {[g['title'] for g in goals_list[:3]]}"
                )
            elif task == "weekly_review":
                result["brief"] = (
                    f"Weekly Review\n"
                    f"- Goals tracked: {len(goals_list)}\n"
                    f"- Memory entries: {memory.get('count', 0)}\n"
                    f"- Knowledge nodes: knowledge graph active\n"
                    f"- Next priorities: Review growth items and archive completed goals."
                )
            else:
                result["brief"] = f"Executive briefing for {task} is ready."
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class KnowledgeDirector(BaseDirector):
    DOMAIN = "knowledge"
    CAPABILITIES = [
        "knowledge_graph_query",
        "concept_linkage",
        "project_interconnection",
        "knowledge_synthesis",
        "memory_organization",
        "knowledge_base_query",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="synthesize_knowledge",
            description="Link concepts, projects, research, and memories into the knowledge graph.",
            steps=["query_graph", "identify_gaps", "add_relations", "update_context"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[KnowledgeDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "instruction": instruction, "state": "started"})
        result: dict[str, Any] = {"instruction": instruction, "status": "completed", "relationships": []}

        try:
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )
            graph = get_knowledge_graph()
            kg_stats = graph.get_stats()
            nodes = graph.get_related(instruction) if instruction else []
            result["graph_stats"] = kg_stats
            result["relationships"] = [
                {"relation": rel.relation, "node": node.label if node else None}
                for rel, node in nodes[:10]
            ]
            if instruction:
                graph.get_or_create_node("query", instruction, {"query": instruction})
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class AutomationDirector(BaseDirector):
    DOMAIN = "automation"
    CAPABILITIES = [
        "dependency_check",
        "benchmark_scheduling",
        "test_automation",
        "code_formatting",
        "backup_tasks",
        "research_indexing",
        "scheduling",
        "repository_maintenance",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="dependency_check",
            description="Check for outdated dependencies in all projects.",
            steps=["scan_projects", "detect_outdated", "propose_updates"],
            risk_level="moderate",
            requires_owner_approval=True,
        ),
        DirectorWorkflow(
            name="repository_maintenance",
            description="Routine repository cleanup and health check.",
            steps=["scan_repo", "identify_stale", "propose_actions"],
            risk_level="moderate",
            requires_owner_approval=True,
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[AutomationDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        workflow = ctx.get("workflow", "dependency_check")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "workflow": workflow, "state": "started"})
        result: dict[str, Any] = {"workflow": workflow, "status": "completed", "proposals": []}

        try:
            if workflow == "dependency_check":
                result["proposals"] = [
                    {
                        "action": "review_dependencies",
                        "description": "Check `requirements.txt`, `package.json`, and `pyproject.toml` for outdated deps.",
                        "risk": "moderate",
                    }
                ]
            elif workflow == "repository_maintenance":
                result["proposals"] = [
                    {
                        "action": "cleanup",
                        "description": "Remove `node_modules`, clean caches, and prune `.git` history.",
                        "risk": "moderate",
                    }
                ]
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class LearningDirector(BaseDirector):
    DOMAIN = "learning"
    CAPABILITIES = [
        "weak_skill_identification",
        "study_plan_generation",
        "book_recommendation",
        "project_recommendation",
        "research_recommendation",
        "mastery_tracking",
        "skill_gap_analysis",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="create_study_plan",
            description="Generate a personalized study plan to close skill gaps.",
            steps=["analyze_experiences", "identify_gaps", "generate_plan", "track_mastery"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[LearningDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        task = ctx.get("task", "create_study_plan")
        skill = ctx.get("skill", instruction)
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "task": task, "state": "started"})
        result: dict[str, Any] = {"task": task, "status": "completed", "plan": ""}

        try:
            from jarvis.evolution.experience_collector import (
                get_experience_collector,  # type: ignore[attr-defined]
            )
            from jarvis.evolution.knowledge_graph_v2 import (
                get_knowledge_graph,  # type: ignore[attr-defined]
            )

            collector = get_experience_collector()
            graph = get_knowledge_graph()
            insights = collector.get_insights()
            experience_summary = insights.get("top_failures", [])[:5]
            kg_stats = graph.get_stats()
            memory = self._get_memory()

            if task == "create_study_plan":
                result["plan"] = (
                    f"Study Plan for {skill}\n"
                    f"- Recent failures: {experience_summary}\n"
                    f"- Knowledge graph nodes: {kg_stats.get('nodes', 0)}\n"
                    f"- Memory entries: {memory.get('count', 0)}\n"
                    f"- Recommendation: Review core concepts, build projects, track outcomes."
                )
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class QualityDirector(BaseDirector):
    DOMAIN = "quality"
    CAPABILITIES = [
        "benchmark_execution",
        "test_coverage_analysis",
        "performance_profiling",
        "regression_detection",
        "improvement_validation",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="run_benchmarks",
            description="Execute project benchmarks and compare against historical baselines.",
            steps=["load_benchmarks", "run_tests", "compare_baselines", "report_gaps"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[QualityDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "started"})
        result: dict[str, Any] = {"status": "completed", "benchmarks": {}}

        try:
            from jarvis.performance.benchmarks import get_benchmark  # type: ignore[attr-defined]
            benchmark = get_benchmark()
            if benchmark:
                result["benchmarks"]["available"] = True
                result["benchmarks"]["metrics"] = list(getattr(benchmark, "metrics", []))
            else:
                result["benchmarks"]["available"] = False
        except Exception as exc:
            result["benchmarks"]["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class SecurityDirector(BaseDirector):
    DOMAIN = "security"
    CAPABILITIES = [
        "security_scan",
        "secret_detection",
        "approval_gate_management",
        "audit_logging",
        "risk_assessment",
        "permission_validation",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="security_audit",
            description="Comprehensive security audit of current codebase and configs.",
            steps=["scan_codebase", "check_secrets", "review_permissions", "risk_report"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[SecurityDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace = self._get_workspace()
        repo_path = workspace.get("directory")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "started"})
        result: dict[str, Any] = {"status": "completed", "security_scan": {}}

        try:
            if repo_path:
                from jarvis.repo.analyzer import RepositoryAnalyzer  # type: ignore[attr-defined]
                analyzer = RepositoryAnalyzer(repo_path)
                result["security_scan"] = analyzer.scan_security()
        except Exception as exc:
            result["security_scan"]["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


class ArchitectureDirector(BaseDirector):
    DOMAIN = "architecture"
    CAPABILITIES = [
        "system_design",
        "workflow_orchestration",
        "dependency_analysis",
        "refactor_planning",
        "capability_router",
        "multi_agent_coordination",
        "pipeline_design",
    ]
    WORKFLOWS = [
        DirectorWorkflow(
            name="architecture_review",
            description="Review the system architecture, identify bottlenecks, propose improvements.",
            steps=["inspect_capabilities", "analyze_flows", "propose_refactors", "estimate_effort"],
            risk_level="safe",
        ),
    ]

    async def initialize(self) -> None:
        logger.info("[ArchitectureDirector] Initialized")
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "initialized"})

    async def execute(self, instruction: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": "started"})
        result: dict[str, Any] = {"status": "completed", "capabilities": {}, "recommendations": []}

        try:
            from jarvis.core.capability_router import (
                get_capability_router,  # type: ignore[attr-defined]
            )
            router = get_capability_router()
            if router:
                result["capabilities"] = router.available_tools() if hasattr(router, "available_tools") else {}
            result["recommendations"] = [
                "Consider adding a caching layer for repeated queries.",
                "Review tool dependencies for circular imports.",
                "Profile planner accuracy vs. execution time.",
            ]
        except Exception as exc:
            result["error"] = str(exc)

        self._emit(EventType.STATUS, {"director": self.DOMAIN, "state": result["status"]})
        return result


_DIRECTOR_REGISTRY: dict[str, BaseDirector] = {}


def register_director(director: BaseDirector) -> None:
    _DIRECTOR_REGISTRY[director.DOMAIN] = director


def get_director(domain: str) -> BaseDirector | None:
    return _DIRECTOR_REGISTRY.get(domain)


def get_all_directors() -> dict[str, BaseDirector]:
    return dict(_DIRECTOR_REGISTRY)


async def initialize_all_directors() -> dict[str, BaseDirector]:
    """Create and initialize all nine Directors."""
    directors: dict[str, BaseDirector] = {
        "software_engineering": SoftwareEngineeringDirector(),
        "research": ResearchDirector(),
        "executive": ExecutiveDirector(),
        "knowledge": KnowledgeDirector(),
        "automation": AutomationDirector(),
        "learning": LearningDirector(),
        "quality": QualityDirector(),
        "security": SecurityDirector(),
        "architecture": ArchitectureDirector(),
    }
    for d in directors.values():
        try:
            await d.initialize()
        except Exception as exc:
            logger.debug("Director %s initialization failed: %s", getattr(d, "DOMAIN", "?"), exc)
        _DIRECTOR_REGISTRY[d.DOMAIN] = d
    return directors
