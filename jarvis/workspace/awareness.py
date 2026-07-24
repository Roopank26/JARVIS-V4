"""
Workspace Awareness for JARVIS.
Tracks current repository, active branch, recent files,
terminal directory, and running servers.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceState:
    repo: str | None = None
    branch: str | None = None
    directory: str | None = None
    recent_files: list[str] = field(default_factory=list)
    running_servers: list[str] = field(default_factory=list)
    editor: str | None = None
    browser: str | None = None
    updated: float = field(default_factory=time.time)


class WorkspaceAwareness:
    def __init__(self):
        self._state = WorkspaceState()
        self._refresh()

    def refresh(self):
        self._refresh()

    def _refresh(self):
        try:
            cwd = os.getcwd()
            self._state.directory = cwd
            self._state.editor = os.environ.get("EDITOR")
            self._state.browser = None
            self._state.updated = time.time()

            try:
                result = subprocess.run(
                    ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._state.repo = result.stdout.strip()
            except Exception:
                pass

            try:
                result = subprocess.run(
                    ["git", "-C", cwd, "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._state.branch = result.stdout.strip()
            except Exception:
                pass

            try:
                result = subprocess.run(
                    ["git", "-C", cwd, "log", "-1", "--name-only", "--pretty=format:"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._state.recent_files = [
                        f.strip() for f in result.stdout.strip().splitlines() if f.strip()
                    ][:10]
            except Exception:
                pass

            try:
                if platform.system().lower() == "windows":
                    result = subprocess.run(
                        ["powershell", "-Command", "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -ExpandProperty MainWindowTitle"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    if result.returncode == 0:
                        self._state.running_servers = [
                            line.strip() for line in result.stdout.strip().splitlines() if line.strip()
                        ][:10]
            except Exception:
                pass
        except Exception as e:
            logger.debug("Workspace refresh error: %s", e)

        return self._state

    def set_repo(self, repo: str | None):
        self._state.repo = repo
        self._state.updated = time.time()

    def set_branch(self, branch: str | None):
        self._state.branch = branch
        self._state.updated = time.time()

    def set_directory(self, directory: str | None):
        self._state.directory = directory
        self._state.updated = time.time()

    def add_recent_file(self, path: str):
        if path not in self._state.recent_files:
            self._state.recent_files.insert(0, path)
            self._state.recent_files = self._state.recent_files[:20]
        self._state.updated = time.time()

    def add_server(self, server: str):
        if server not in self._state.running_servers:
            self._state.running_servers.append(server)
        self._state.updated = time.time()

    def remove_server(self, server: str):
        if server in self._state.running_servers:
            self._state.running_servers.remove(server)
        self._state.updated = time.time()

    def get_state(self) -> WorkspaceState:
        return self._state

    def to_prompt_context(self) -> str:
        s = self._state
        parts: list[str] = []
        if s.repo:
            parts.append(f"Current repository: {s.repo}")
        if s.branch:
            parts.append(f"Active branch: {s.branch}")
        if s.directory:
            parts.append(f"Working directory: {s.directory}")
        if s.editor:
            parts.append(f"Editor: {s.editor}")
        if s.recent_files:
            parts.append(f"Recent files: {', '.join(s.recent_files[:5])}")
        if s.running_servers:
            parts.append(f"Running servers: {', '.join(s.running_servers[:5])}")
        return "\n".join(parts) if parts else ""
