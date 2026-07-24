"""
JARVIS-V4 CAE — Repository Watcher.

Continuously monitors watched repositories for file changes and triggers
re-analysis of architecture, dependencies, complexity, and technical debt.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RepoWatchTarget:
    path: str
    label: str = ""
    interval_seconds: float = 300.0
    include_submodules: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            self.label = Path(self.path).name


@dataclass
class RepoChangeEvent:
    repo_label: str
    file_path: str
    change_type: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_label": self.repo_label,
            "file_path": self.file_path,
            "change_type": self.change_type,
            "timestamp": self.timestamp,
        }


class RepositoryWatcher:
    def __init__(self) -> None:
        self._targets: dict[str, RepoWatchTarget] = {}
        self._snapshots: dict[str, dict[str, float]] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._interrupt = asyncio.Event()
        self._queue: asyncio.Queue[RepoChangeEvent] = asyncio.Queue()

    def add_repo(self, target: RepoWatchTarget) -> None:
        self._targets[target.label] = target
        root = Path(target.path)
        if root.exists():
            self._snapshots[target.label] = self._scan(root)
        logger.debug("Repo watcher registered %s at %s", target.label, target.path)

    def remove_repo(self, label: str) -> None:
        self._targets.pop(label, None)
        self._snapshots.pop(label, None)

    def list_repos(self) -> list[str]:
        return list(self._targets.keys())

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._interrupt.clear()
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("Repository watcher started")

    async def stop(self) -> None:
        self._running = False
        self._interrupt.set()
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Repository watcher stopped")

    async def get_event(self) -> RepoChangeEvent | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def _snapshot(self, root: Path) -> dict[str, float]:
        snap: dict[str, float] = {}
        if not root.exists():
            return snap
        for p in root.rglob("*"):
            if p.is_file():
                try:
                    snap[str(p)] = p.stat().st_mtime
                except OSError:
                    continue
        return snap

    def _scan(self, root: Path) -> dict[str, float]:
        return self._snapshot(root)

    async def _watch_loop(self) -> None:
        while self._running:
            if self._interrupt.is_set():
                await asyncio.sleep(1)
                continue

            for label, target in list(self._targets.items()):
                root = Path(target.path)
                if not root.exists():
                    continue

                current = self._snapshot(root)
                old = self._snapshots.get(label, {})

                added = [f for f in current if f not in old]
                removed = [f for f in old if f not in current]
                modified = [
                    f for f in current
                    if f in old and current[f] != old[f]
                ]

                if added or removed or modified:
                    changes = []
                    for f in added:
                        changes.append(RepoChangeEvent(label, f, "added"))
                    for f in removed:
                        changes.append(RepoChangeEvent(label, f, "removed"))
                    for f in modified:
                        changes.append(RepoChangeEvent(label, f, "modified"))

                    for event in changes:
                        self._queue.put_nowait(event)

                    self._snapshots[label] = current

                    logger.debug(
                        "Repo %s changed: %d added, %d removed, %d modified",
                        label,
                        len(added),
                        len(removed),
                        len(modified),
                    )

            try:
                await asyncio.wait_for(self._interrupt.wait(), timeout=60.0)
            except TimeoutError:
                continue

    async def analyze_changes(self, repo_label: str) -> dict[str, Any] | None:
        target = self._targets.get(repo_label)
        if not target:
            return None

        root = Path(target.path)
        if not root.exists():
            return None

        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer

            analyzer = RepositoryAnalyzer(root)
            return analyzer.analyze()
        except Exception as exc:
            logger.debug("Repo analysis failed for %s: %s", repo_label, exc)
            return None


_watcher_instance: RepositoryWatcher | None = None


def get_repo_watcher() -> RepositoryWatcher:
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = RepositoryWatcher()
    return _watcher_instance


def reset_repo_watcher() -> None:
    global _watcher_instance
    _watcher_instance = None
