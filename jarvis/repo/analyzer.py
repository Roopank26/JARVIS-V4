"""
Repository Analyzer for JARVIS.
Provides code analysis, architecture overview, and repository intelligence.
"""

import ast
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class FileAnalysis:
    """Analysis of a single file."""

    path: str
    language: str
    lines_of_code: int
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    complexity: int = 0
    issues: list[str] = field(default_factory=list)


@dataclass
class RepositoryStats:
    """Repository statistics."""

    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    complexity: int = 0


class RepositoryAnalyzer:
    """
    Analyze code repositories and provide insights.

    Capabilities:
    - AST-based code analysis
    - Dependency graph generation
    - Complexity analysis
    - Security vulnerability scanning
    - Architecture overview
    - Dead code detection
    """

    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }

    def __init__(self, repo_path: str | None = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self._file_cache: dict[str, FileAnalysis] = {}
        self._code_files_cache: list[Path] | None = None
        self._dependency_graph: dict[str, set[str]] = defaultdict(set)

    def analyze(self) -> dict[str, Any]:
        """Run full repository analysis."""
        stats = self.get_statistics()
        architecture = self.get_architecture()
        dependencies = self.get_dependencies()
        todos = self.find_todos()
        security = self.scan_security()

        return {
            "stats": stats.__dict__,
            "architecture": architecture,
            "dependencies": dependencies,
            "todos": todos,
            "security": security,
            "analyzed_at": datetime.now().isoformat(),
        }

    def get_statistics(self) -> RepositoryStats:
        """Get repository statistics."""
        stats = RepositoryStats()

        for file_path in self._get_code_files():
            try:
                analysis = self.analyze_file(file_path)
                stats.total_files += 1
                stats.total_lines += analysis.lines_of_code
                stats.total_functions += len(analysis.functions)
                stats.total_classes += len(analysis.classes)
                stats.complexity += analysis.complexity

                lang = analysis.language
                stats.languages[lang] = stats.languages.get(lang, 0) + 1
            except Exception:
                continue

        return stats

    def _get_code_files(self) -> list[Path]:
        """Get all code files in repository (cached)."""
        if self._code_files_cache is not None:
            return self._code_files_cache

        code_files = []
        exclude_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".idea",
            ".vscode",
            "env",
            ".env",
        }

        for root, dirs, files in os.walk(self.repo_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                ext = Path(file).suffix
                if ext in self.SUPPORTED_EXTENSIONS:
                    code_files.append(Path(root) / file)

        self._code_files_cache = code_files
        return code_files

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single file."""
        cache_key = str(file_path)
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        analysis = FileAnalysis(
            path=str(file_path),
            language=self.SUPPORTED_EXTENSIONS.get(file_path.suffix, "unknown"),
            lines_of_code=0,
        )

        try:
            content = file_path.read_text(encoding="utf-8")
            analysis.lines_of_code = len(content.splitlines())

            if file_path.suffix == ".py":
                analysis = self._analyze_python(file_path, content)
            elif file_path.suffix in {".js", ".ts", ".jsx", ".tsx"}:
                analysis = self._analyze_javascript(file_path, content)
        except Exception:
            pass

        self._file_cache[cache_key] = analysis
        return analysis

    def _analyze_python(self, file_path: Path, content: str) -> FileAnalysis:
        """Analyze Python file using AST."""
        analysis = FileAnalysis(
            path=str(file_path),
            language="python",
            lines_of_code=len(content.splitlines()),
        )

        try:
            tree = ast.parse(content)

            # Find imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    analysis.imports.append(node.module)

            # Find classes and functions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    analysis.classes.append(node.name)
                    # Count methods
                    for item in ast.iter_child_nodes(node):
                        if isinstance(item, ast.FunctionDef):
                            analysis.functions.append(f"{node.name}.{item.name}")
                            analysis.complexity += self._complexity(node)
                elif isinstance(node, ast.FunctionDef):
                    analysis.functions.append(node.name)
                    analysis.complexity += self._complexity(node)

        except SyntaxError:
            analysis.issues.append("Syntax error")

        return analysis

    def _analyze_javascript(self, file_path: Path, content: str) -> FileAnalysis:
        """Basic JavaScript analysis."""
        analysis = FileAnalysis(
            path=str(file_path),
            language="javascript",
            lines_of_code=len(content.splitlines()),
        )

        # Find imports
        import_pattern = r'(?:import|require)\s*\([\'"]([^\'"]+)[\'"]\)'
        analysis.imports = re.findall(import_pattern, content)

        # Find functions (basic)
        func_pattern = r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=)"
        matches = re.findall(func_pattern, content)
        for match in matches:
            func_name = match[0] or match[1]
            if func_name:
                analysis.functions.append(func_name)

        return analysis

    def _complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def get_architecture(self) -> dict[str, Any]:
        """Get repository architecture overview."""
        modules = defaultdict(list)

        for file_path in self._get_code_files():
            if file_path.suffix == ".py":
                parts = file_path.relative_to(self.repo_path).parts
                if len(parts) > 1:
                    module = parts[0]
                    modules[module].append(str(file_path.relative_to(self.repo_path)))

        # Build directory tree
        tree = self._build_tree(self.repo_path)

        return {
            "modules": dict(modules),
            "tree": tree,
            "root_files": [f.name for f in self.repo_path.iterdir() if f.is_file()],
        }

    def _build_tree(self, path: Path, depth: int = 0) -> dict[str, Any]:
        """Build directory tree."""
        if depth > 3:  # Limit depth
            return {}

        tree = {"_type": "dir" if path.is_dir() else "file"}

        if path.is_dir():
            children = {}
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                children[item.name] = self._build_tree(item, depth + 1)
            tree["children"] = children

        return tree

    def get_dependencies(self) -> dict[str, Any]:
        """Get dependency graph."""
        dependencies = defaultdict(set)

        for file_path in self._get_code_files():
            if file_path.suffix == ".py":
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                dependencies[file_path.name].add(alias.name)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            dependencies[file_path.name].add(node.module)
                except (SyntaxError, ValueError):
                    pass

        return {k: list(v) for k, v in dependencies.items()}

    def find_todos(self) -> list[dict[str, Any]]:
        """Find TODO comments in code."""
        todos = []
        patterns = ["TODO", "FIXME", "HACK", "XXX", "BUG", "NOTE"]

        for file_path in self._get_code_files():
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if pattern in line:
                            todos.append(
                                {
                                    "file": str(file_path.relative_to(self.repo_path)),
                                    "line": i,
                                    "type": pattern,
                                    "content": line.strip(),
                                }
                            )
            except (OSError, UnicodeDecodeError):
                pass

        return todos

    def scan_security(self) -> list[dict[str, Any]]:
        """Basic security vulnerability scan."""
        issues = []

        # Patterns to look for
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r"eval\s*\(", "Use of eval()"),
            (r"exec\s*\(", "Use of exec()"),
            (r"os\.system\s*\(", "Use of os.system()"),
            (r"subprocess\s*\.\s*call\s*\([^,]*shell\s*=\s*True", "Shell injection risk"),
        ]

        for file_path in self._get_code_files():
            if file_path.suffix not in {".py", ".js", ".ts"}:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    for pattern, issue_type in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append(
                                {
                                    "file": str(file_path.relative_to(self.repo_path)),
                                    "line": i,
                                    "type": issue_type,
                                    "content": line.strip(),
                                }
                            )
            except (OSError, UnicodeDecodeError):
                pass

        return issues

    def generate_documentation(self) -> str:
        """Generate repository documentation."""
        stats = self.get_statistics()
        arch = self.get_architecture()
        todos = self.find_todos()

        lines = [
            "# Repository Analysis",
            "",
            f"**Analyzed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Statistics",
            f"- **Files:** {stats.total_files}",
            f"- **Lines of Code:** {stats.total_lines}",
            f"- **Functions:** {stats.total_functions}",
            f"- **Classes:** {stats.total_classes}",
            f"- **Complexity:** {stats.complexity}",
            "",
            "## Languages",
        ]

        for lang, count in stats.languages.items():
            lines.append(f"- {lang}: {count} files")

        lines.extend(
            [
                "",
                "## Modules",
            ]
        )

        for module, files in arch["modules"].items():
            lines.append(f"### {module}/")
            for f in files[:5]:  # Show first 5 files
                lines.append(f"- `{f}`")
            if len(files) > 5:
                lines.append(f"- ... and {len(files) - 5} more")

        if todos:
            lines.extend(
                [
                    "",
                    "## TODO Items",
                ]
            )
            for todo in todos[:20]:  # Show first 20
                lines.append(f"- [{todo['file']}:{todo['line']}] {todo['content']}")

        return "\n".join(lines)

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        stats = self.get_statistics()
        todos = self.find_todos()
        security = self.scan_security()

        lines = [
            "[Repository Analysis]",
            "=" * 40,
            "",
            f"📁 Files: {stats.total_files}",
            f"📝 Lines: {stats.total_lines:,}",
            f"⚙️ Functions: {stats.total_functions}",
            f"🏛️ Classes: {stats.total_classes}",
            f"📊 Complexity: {stats.complexity}",
            "",
        ]

        if stats.languages:
            lines.append("Languages:")
            for lang, count in stats.languages.items():
                lines.append(f"  • {lang}: {count}")
            lines.append("")

        if todos:
            lines.append(f"📋 TODOs: {len(todos)} found")
        else:
            lines.append("📋 TODOs: None found")

        if security:
            lines.append(f"⚠️ Security Issues: {len(security)} found")
        else:
            lines.append("⚠️ Security Issues: None found")

        return "\n".join(lines)
