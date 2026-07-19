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


class CodeMetrics:
    """Calculate code metrics for a project."""
    
    COMPLEXITY_PATTERNS = {
        "nested_loops": r"(for|while).*:\s*(for|while)",
        "deep_nesting": r":\s*:\s*:\s*:\s*:",  # 5+ levels
        "long_functions": None,  # Check by line count
        "complex_conditions": r"\b(if|and|or)\b.*\b(if|and|or)\b",
    }
    
    @classmethod
    def calculate_complexity(cls, content: str) -> Dict[str, Any]:
        """Calculate code complexity metrics."""
        lines = content.split('\n')
        
        metrics = {
            "lines": len(lines),
            "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "cyclomatic_complexity": 1,  # Base complexity
            "nesting_depth": 0,
            "max_nesting": 0,
        }
        
        # Count complexity
        for line in lines:
            stripped = line.strip()
            metrics["cyclomatic_complexity"] += len(re.findall(r'\b(if|elif|else|for|while|and|or|except|case)\b', stripped))
            
            # Track nesting
            indent = len(line) - len(line.lstrip())
            current_depth = indent // 4
            metrics["max_nesting"] = max(metrics["max_nesting"], current_depth)
        
        return metrics
    
    @classmethod
    def detect_code_smells(cls, content: str, file_path: str) -> List[str]:
        """Detect code smells."""
        smells = []
        lines = content.split('\n')
        
        # Long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                smells.append(f"L{i}: Line exceeds 120 characters ({len(line)} chars)")
        
        # Long functions (heuristic: 100+ lines without blank line)
        consecutive = 0
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                consecutive += 1
                if consecutive > 100:
                    smells.append(f"Function may be too long (>100 lines)")
                    break
            else:
                consecutive = 0
        
        # TODO/FIXME/HACK
        for i, line in enumerate(lines, 1):
            if 'TODO' in line:
                smells.append(f"L{i}: TODO comment found")
            if 'FIXME' in line:
                smells.append(f"L{i}: FIXME comment found")
        
        # Hardcoded values
        for i, line in enumerate(lines, 1):
            if re.search(r'\b\d{7,}\b', line):  # Magic numbers > 10M
                smells.append(f"L{i}: Possible magic number")
        
        return smells[:10]  # Limit to first 10


class CodeFormatter:
    """Format code according to language standards."""
    
    FORMATTERS = {
        "python": ["black", "ruff", " autopep8"],
        "javascript": ["prettier", "eslint --fix"],
        "typescript": ["prettier", "eslint --fix"],
        "rust": ["rustfmt"],
        "go": ["gofmt"],
    }
    
    @classmethod
    def format_file(cls, file_path: str) -> Dict[str, Any]:
        """Format a code file."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".rs": "rust", ".go": "go", ".java": "java",
        }
        language = language_map.get(ext, "unknown")
        
        if language not in cls.FORMATTERS:
            return {"success": False, "error": f"No formatter for {language}"}
        
        formatter = cls.FORMATTERS[language][0]
        
        # Check if formatter is available
        import shutil
        if not shutil.which(formatter):
            return {"success": False, "error": f"{formatter} not installed"}
        
        # Run formatter
        import subprocess
        try:
            result = subprocess.run(
                [formatter, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "formatter": formatter,
                "output": result.stdout if result.stdout else result.stderr,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class CodeDocumentation:
    """Generate documentation for code."""
    
    @classmethod
    def generate_readme(cls, project_path: str) -> str:
        """Generate README.md for a project."""
        indexer = RepositoryIndexer(Path(project_path))
        project_map = asyncio.run(indexer.index())
        
        lines = [
            f"# {project_map.root.name}",
            "",
            "## Project Overview",
            "",
            "## Features",
            "",
            "## Installation",
            "",
            "## Usage",
            "",
            "## Project Structure",
            "",
            "```",
            f"Total Files: {project_map.file_count}",
            f"Total Lines: {project_map.total_lines}",
            "```",
            "",
            "## Language Statistics",
            "",
        ]
        
        for lang, count in sorted(project_map.language_stats.items()):
            lines.append(f"- {lang}: {count} files")
        
        return "\n".join(lines)
    
    @classmethod
    def document_file(cls, file_path: str) -> str:
        """Generate documentation for a single file."""
        try:
            content = Path(file_path).read_text()
            ext = Path(file_path).suffix.lower()
            
            # Extract docstring if Python
            if ext == ".py":
                match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                if match:
                    return match.group(1).strip()
            
            return f"# {Path(file_path).name}\n\nNo documentation found."
        except Exception as e:
            return f"Error: {e}"


class DependencyGraph:
    """Analyze and visualize dependencies."""
    
    @classmethod
    def build_graph(cls, project_path: str) -> Dict[str, List[str]]:
        """Build a dependency graph."""
        import ast
        
        dependencies: Dict[str, List[str]] = {}
        project = Path(project_path)
        
        for py_file in project.rglob("*.py"):
            if any(skip in str(py_file) for skip in [".git", "node_modules", "__pycache__"]):
                continue
            
            try:
                content = py_file.read_text()
                tree = ast.parse(content)
                
                module_name = py_file.relative_to(project).stem
                deps = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and not node.module.startswith('_'):
                            deps.append(node.module.split('.')[0])
                
                dependencies[str(module_name)] = list(set(deps))
            except (SyntaxError, ValueError):
                continue
        
        return dependencies
    
    @classmethod
    def format_graph(cls, dependencies: Dict[str, List[str]]) -> str:
        """Format dependency graph as text."""
        lines = ["[Dependency Graph]", "=" * 40, ""]
        
        for module, deps in sorted(dependencies.items()):
            if deps:
                lines.append(f"{module}:")
                for dep in sorted(deps):
                    lines.append(f"  └─ {dep}")
                lines.append("")
        
        return "\n".join(lines)


class CodeSearch:
    """Search code across files."""
    
    @classmethod
    def search_pattern(cls, project_path: str, pattern: str, file_pattern: str = "*.py") -> List[Dict[str, Any]]:
        """Search for a pattern in code files."""
        import re
        
        results = []
        project = Path(project_path)
        regex = re.compile(pattern, re.IGNORECASE)
        
        for file_path in project.rglob(file_pattern):
            if any(skip in str(file_path) for skip in [".git", "node_modules", "__pycache__"]):
                continue
            
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        results.append({
                            "file": str(file_path.relative_to(project)),
                            "line": i,
                            "content": line.strip(),
                        })
            except (OSError, UnicodeDecodeError):
                continue
        
        return results[:50]  # Limit results
    
    @classmethod
    def format_search_results(cls, results: List[Dict[str, Any]]) -> str:
        """Format search results."""
        if not results:
            return "No results found."
        
        lines = [f"[Search Results: {len(results)} matches]", "=" * 40, ""]
        
        current_file = None
        for result in results:
            if result["file"] != current_file:
                current_file = result["file"]
                lines.append(f"\n{current_file}:")
            
            lines.append(f"  L{result['line']}: {result['content'][:80]}")
        
        return "\n".join(lines)


# Extend get_indexer to include new capabilities
def analyze_code_metrics(project_path: str) -> Dict[str, Any]:
    """Calculate code metrics for a project."""
    metrics = {
        "files": 0,
        "lines": 0,
        "functions": 0,
        "classes": 0,
        "complexity": 0,
    }
    
    project = Path(project_path)
    for py_file in project.rglob("*.py"):
        if any(skip in str(py_file) for skip in [".git", "node_modules", "__pycache__"]):
            continue
        
        try:
            content = py_file.read_text()
            m = CodeMetrics.calculate_complexity(content)
            metrics["files"] += 1
            metrics["lines"] += m["lines"]
            metrics["complexity"] += m["cyclomatic_complexity"]
            
            # Count functions and classes
            metrics["functions"] += len(re.findall(r'\ndef\s+\w+', content))
            metrics["classes"] += len(re.findall(r'\bclass\s+\w+', content))
        except (SyntaxError, ValueError, OSError):
            continue
    
    return metrics


def search_code(project_path: str, query: str) -> str:
    """Search code in project."""
    results = CodeSearch.search_pattern(project_path, query)
    return CodeSearch.format_search_results(results)


def get_dependency_graph(project_path: str) -> str:
    """Get dependency graph for project."""
    deps = DependencyGraph.build_graph(project_path)
    return DependencyGraph.format_graph(deps)
