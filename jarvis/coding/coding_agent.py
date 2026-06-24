"""
JARVIS Coding Agent - Repository Intelligence System
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CodeFile:
    """Represents a code file."""
    path: Path
    language: str
    lines: int
    size: int
    content: Optional[str] = None
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


@dataclass
class ProjectMap:
    """Project structure map."""
    root: Path
    language_stats: Dict[str, int] = field(default_factory=dict)
    files: Dict[str, CodeFile] = field(default_factory=dict)
    file_count: int = 0
    total_lines: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class RepositoryIndexer:
    """
    Indexes repositories for analysis.
    """

    LANGUAGE_EXTENSIONS = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".java": "java", ".go": "go", ".rs": "rust", ".c": "c",
        ".cpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".md": "markdown",
    }

    SKIP_DIRS = {
        ".git", "node_modules", "__pycache__", "venv", "build",
        "dist", ".idea", ".vscode", "target", "vendor",
    }

    def __init__(self, root_path: Optional[Path] = None):
        self.root = root_path or Path.cwd()
        self.project_map: Optional[ProjectMap] = None

    async def index(self, path: Optional[Path] = None) -> ProjectMap:
        """Index a repository."""
        root = path or self.root
        if not root.exists():
            raise FileNotFoundError(f"Path not found: {root}")

        project_map = ProjectMap(root=root)
        files: Dict[str, CodeFile] = {}
        language_stats: Dict[str, int] = defaultdict(int)
        total_lines = 0

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            if any(skip in file_path.parts for skip in self.SKIP_DIRS):
                continue

            ext = file_path.suffix.lower()
            language = self.LANGUAGE_EXTENSIONS.get(ext, "unknown")
            if language == "unknown":
                continue

            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            content = None
            if size < 100_000 and ext in {".py", ".js", ".ts", ".java", ".go", ".md"}:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

            lines = len(content.splitlines()) if content else 0
            total_lines += lines

            functions, classes, imports = self._extract_code_info(content, ext)

            code_file = CodeFile(
                path=file_path.relative_to(root),
                language=language,
                lines=lines,
                size=size,
                content=content,
                functions=functions,
                classes=classes,
                imports=imports
            )

            str_path = str(file_path.relative_to(root))
            files[str_path] = code_file
            language_stats[language] += 1

        project_map.files = files
        project_map.language_stats = dict(language_stats)
        project_map.file_count = len(files)
        project_map.total_lines = total_lines
        self.project_map = project_map
        return project_map

    def _extract_code_info(self, content: Optional[str], ext: str) -> tuple:
        """Extract functions, classes, imports."""
        if not content:
            return [], [], []

        functions, classes, imports = [], [], []

        if ext == ".py":
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            functions = re.findall(r"^(?:async\s+)?def\s+(\w+)", content, re.MULTILINE)
            imports = re.findall(r"^(?:from|import)\s+([\w.]+)", content, re.MULTILINE)
        elif ext in {".js", ".ts"}:
            classes = re.findall(r"class\s+(\w+)", content)
            functions = re.findall(r"(?:function\s+(\w+)|const\s+(\w+)\s*=)", content)
        elif ext == ".java":
            classes = re.findall(r"public\s+class\s+(\w+)", content)
            functions = re.findall(r"(?:public|private)\s+\w+\s+(\w+)\s*\(", content)

        return list(set(functions)), list(set(classes)), list(set(imports))

    def format_summary(self) -> str:
        """Format project summary."""
        if not self.project_map:
            return "No project indexed"
        pm = self.project_map
        lines = [f"# Project: {pm.root.name}", "", f"Files: {pm.file_count}", f"Lines: {pm.total_lines:,}", "", "Languages:"]
        for lang, count in sorted(pm.language_stats.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  - {lang}: {count}")
        return "\n".join(lines)


class CodeAnalyzer:
    """Analyzes code quality and complexity."""

    def __init__(self, project_map: ProjectMap):
        self.project_map = project_map

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file."""
        code_file = self.project_map.files.get(file_path)
        if not code_file:
            return {"error": "File not found"}

        return {
            "path": file_path,
            "language": code_file.language,
            "lines": code_file.lines,
            "functions": len(code_file.functions),
            "classes": len(code_file.classes),
            "issues": self._check_issues(code_file),
        }

    def _check_issues(self, code_file: CodeFile) -> List[str]:
        """Check for common issues."""
        issues = []
        if not code_file.content:
            return issues

        if "TODO" in code_file.content or "FIXME" in code_file.content:
            issues.append("Contains TODO/FIXME")
        if re.search(r"(api_key|password|secret)\s*=\s*['\"][^'\"]{8,}", code_file.content, re.I):
            issues.append("Potential hardcoded secrets")
        if code_file.language == "python":
            if "except:" in code_file.content:
                issues.append("Uses bare except")
        return issues


class GitIntegration:
    """Git operations."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()

    async def get_status(self) -> Dict[str, Any]:
        """Get git status."""
        try:
            result = await self._run_git(["status", "--porcelain"])
            return {"status": "success", "output": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_branch(self) -> str:
        """Get current branch."""
        try:
            return (await self._run_git(["branch", "--show"])).strip()
        except Exception:
            return "unknown"

    async def get_commits(self, count: int = 10) -> List[Dict[str, str]]:
        """Get recent commits."""
        try:
            output = await self._run_git(["log", "--oneline", f"-{count}"])
            commits = []
            for line in output.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0][:8], "message": parts[1]})
            return commits
        except Exception:
            return []

    async def stage(self, files: List[str]) -> bool:
        """Stage files."""
        try:
            for f in files:
                await self._run_git(["add", f])
            return True
        except Exception:
            return False

    async def commit(self, message: str) -> bool:
        """Create commit."""
        try:
            await self._run_git(["commit", "-m", message])
            return True
        except Exception:
            return False

    async def _run_git(self, args: List[str]) -> str:
        """Run git command."""
        proc = await asyncio.create_subprocess_exec(
            "git", *args, cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(stderr.decode() or "Unknown error")
        return stdout.decode()


# Global instances
_indexer: Optional[RepositoryIndexer] = None


def get_indexer() -> RepositoryIndexer:
    """Get global indexer."""
    global _indexer
    if _indexer is None:
        _indexer = RepositoryIndexer()
    return _indexer
