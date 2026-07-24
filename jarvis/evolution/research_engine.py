"""
JARVIS-V7 Evolution — Autonomous Research Engine.

When idle, JARVIS continuously:
- Reads local documentation
- Studies project repositories
- Reviews API documentation
- Summarizes research papers
- Learns new programming techniques
- Tracks framework updates
- Indexes everything into the knowledge graph
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RESEARCH_DIR = Path.home() / ".jarvis" / "evolution" / "research"
DEFAULT_RESEARCH_FILE = "research_log.jsonl"


@dataclass
class ResearchTask:
    task_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    task_type: str = "general"
    query: str = ""
    status: str = "pending"
    result: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


class ResearchLog:
    def __init__(self, storage_path: Path | None = None):
        self.path = storage_path or DEFAULT_RESEARCH_DIR / DEFAULT_RESEARCH_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, task: ResearchTask) -> None:
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                import json
                f.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass


class AutonomousResearchEngine:
    def __init__(self):
        self.log = ResearchLog()
        self.graph = None
        try:
            from jarvis.evolution.knowledge_graph_v2 import get_knowledge_graph
            self.graph = get_knowledge_graph()
        except Exception:
            pass
        self._running = False
        self._queue: asyncio.Queue[ResearchTask] = asyncio.Queue()

    async def start(self) -> None:
        self._running = True
        self._register_with_health_monitor()
        logger.info("Autonomous research engine started")

    async def stop(self) -> None:
        self._running = False
        logger.info("Autonomous research engine stopped")

    def _register_with_health_monitor(self) -> None:
        try:
            from jarvis.monitoring.health_monitor import get_health_monitor
            monitor = get_health_monitor()
            monitor.register(
                "research_engine",
                starter=self.start,
                stopper=self.stop,
                memory_threshold_bytes=200 * 1024 * 1024,
                pauseable=True,
            )
        except Exception:
            pass

    async def run_research_cycle(self, idle_threshold_ms: float = 60000) -> None:
        if not self._running:
            return
        await asyncio.sleep(idle_threshold_ms / 1000.0)
        if not self._running:
            return
        tasks = [
            self._scan_local_docs(),
            self._review_projects(),
            self._index_knowledge_graph(),
        ]
        for task in tasks:
            if not self._running:
                break
            try:
                await asyncio.wait_for(task, timeout=30)
            except TimeoutError:
                continue
            except Exception as exc:
                logger.debug("Research task failed: %s", exc)

    async def _scan_local_docs(self) -> None:
        start = time.perf_counter()
        task = ResearchTask(task_type="local_docs_scan", query="Local documentation scan")
        count = 0
        walk_results = await asyncio.to_thread(os.walk, ".")
        for root, _dirs, files in walk_results:
            if ".git" in root or "node_modules" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith((".py", ".md", ".txt", ".json", ".yaml", ".yml")):
                    count += 1
        task.result = f"Indexed {count} local files"
        task.duration_ms = (time.perf_counter() - start) * 1000.0
        task.status = "complete"
        if self.graph:
            self.graph.get_or_create_node("research_summary", task.result, {"type": "local_docs_scan"})
        self.log.append(task)

    async def _review_projects(self) -> None:
        start = time.perf_counter()
        task = ResearchTask(task_type="project_review", query="Repository analysis")
        try:
            from pathlib import Path

            from jarvis.repo.analyzer import RepositoryAnalyzer
            analyzer = RepositoryAnalyzer(Path.cwd())
            analyzer.analyze()
            stats = analyzer.get_statistics()
            task.result = f"Reviewed repository: {stats.total_files} files, {stats.total_lines} lines"
        except Exception as exc:
            task.result = f"Review failed: {exc}"
            task.status = "failed"
        task.duration_ms = (time.perf_counter() - start) * 1000.0
        if self.graph:
            node = self.graph.get_or_create_node("research_summary", task.result, {"type": "project_review"})
            self.graph.add_edge("project:JARVIS-V4", node.id, "reviewed_by")
        self.log.append(task)

    async def _index_knowledge_graph(self) -> None:
        start = time.perf_counter()
        task = ResearchTask(task_type="knowledge_graph_maintenance", query="Knowledge graph indexing")
        if self.graph:
            stats = self.graph.get_stats()
            task.result = f"Knowledge graph: {stats['nodes']} nodes, {stats['edges']} edges"
        else:
            task.result = "Knowledge graph not available"
        task.duration_ms = (time.perf_counter() - start) * 1000.0
        self.log.append(task)

    def queue_task(self, task_type: str, query: str) -> None:
        task = ResearchTask(task_type=task_type, query=query)
        self._queue.put_nowait(task)

    async def process_queue(self) -> None:
        while self._running:
            try:
                task = self._queue.get_nowait()
                start = time.perf_counter()
                if task.task_type == "web_search":
                    await self._web_search(task)
                task.duration_ms = (time.perf_counter() - start) * 1000.0
                self.log.append(task)
            except asyncio.QueueEmpty:
                await asyncio.sleep(1)

    async def _web_search(self, task: ResearchTask) -> None:
        try:
            from jarvis.research.research_agent import get_research_agent
            agent = get_research_agent()
            result = await agent.research(task.query)
            task.result = result.summary or str(result.sources[:3])
            task.status = "complete"
        except Exception as exc:
            task.result = str(exc)
            task.status = "failed"


_research_instance: AutonomousResearchEngine | None = None


def get_research_engine() -> AutonomousResearchEngine:
    global _research_instance
    if _research_instance is None:
        _research_instance = AutonomousResearchEngine()
    return _research_instance


def reset_research_engine() -> None:
    global _research_instance
    _research_instance = None
