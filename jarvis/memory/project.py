"""
Project memory system for JARVIS.
Maintains context for each project the user works on.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Context for a single project."""
    path: Path
    name: str
    language: str = ""
    frameworks: List[str] = field(default_factory=list)
    recent_files: List[str] = field(default_factory=list)
    git_branch: str = ""
    git_status: str = ""
    todos: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    last_active: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["path"] = self.path.as_posix()  # Use POSIX format for cross-platform compatibility
        data["last_active"] = self.last_active.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectContext":
        """Create from dictionary."""
        data["path"] = Path(data["path"])
        data["last_active"] = datetime.fromisoformat(data.get("last_active", datetime.now().isoformat()))
        data["created_at"] = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        return cls(**data)


class ProjectMemory:
    """
    Manages context for multiple projects.
    Automatically detects projects from git repositories.
    """

    def __init__(self, storage_path: Path = None):
        if storage_path is None:
            storage_path = Path.home() / ".jarvis" / "projects.json"
        
        self.storage_path = storage_path
        self.projects: Dict[str, ProjectContext] = {}
        self.active_project: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load projects from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                
                self.projects = {
                    name: ProjectContext.from_dict(pdata)
                    for name, pdata in data.items()
                }
                self.active_project = data.get("_active_project")
                
                logger.info(f"Loaded {len(self.projects)} projects")
            except Exception as e:
                logger.error(f"Failed to load projects: {e}")

    def _save(self) -> None:
        """Save projects to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            name: p.to_dict()
            for name, p in self.projects.items()
        }
        if self.active_project:
            data["_active_project"] = self.active_project
        
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_project(self, path: Path, name: str = None) -> ProjectContext:
        """
        Add a project or update existing.
        
        Args:
            path: Project directory path
            name: Optional project name (defaults to directory name)
        """
        path = path.resolve()
        name = name or path.name
        
        # Check if already exists
        if name in self.projects:
            project = self.projects[name]
            project.last_active = datetime.now()
        else:
            project = ProjectContext(path=path, name=name)
            self.projects[name] = project
            logger.info(f"Added project: {name}")

        # Auto-detect project info
        self._detect_project_info(project)
        
        self._save()
        return project

    def remove_project(self, name: str) -> bool:
        """Remove a project."""
        if name in self.projects:
            del self.projects[name]
            if self.active_project == name:
                self.active_project = None
            self._save()
            logger.info(f"Removed project: {name}")
            return True
        return False

    def get_project(self, name: str) -> Optional[ProjectContext]:
        """Get project by name."""
        return self.projects.get(name)

    def get_active_project(self) -> Optional[ProjectContext]:
        """Get currently active project."""
        if self.active_project:
            return self.projects.get(self.active_project)
        return None

    def set_active(self, name: str) -> bool:
        """Set active project."""
        if name in self.projects:
            self.active_project = name
            self.projects[name].last_active = datetime.now()
            self._save()
            logger.info(f"Active project: {name}")
            return True
        return False

    def list_projects(self) -> List[Dict]:
        """List all projects with summary info."""
        return [
            {
                "name": p.name,
                "path": str(p.path),
                "language": p.language,
                "git_branch": p.git_branch,
                "last_active": p.last_active.isoformat(),
                "is_active": p.name == self.active_project,
            }
            for p in self.projects.values()
        ]

    def _detect_project_info(self, project: ProjectContext) -> None:
        """Auto-detect project information."""
        path = project.path
        
        # Git detection
        if (path / ".git").exists():
            try:
                # Current branch
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    project.git_branch = result.stdout.strip()
                
                # Git status
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    untracked = len([l for l in result.stdout.splitlines() if l.startswith("??")])
                    modified = len([l for l in result.stdout.splitlines() if not l.startswith("??")])
                    project.git_status = f"{modified} modified, {untracked} untracked"
            except Exception as e:
                logger.debug(f"Git detection failed: {e}")

        # Language detection
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rb": "Ruby",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        
        extensions = {}
        for ext, lang in language_map.items():
            count = len(list(path.rglob(f"*{ext}")))
            if count > 0:
                extensions[ext] = count
        
        if extensions:
            project.language = max(extensions, key=extensions.get).lstrip(".")
            if project.language == "js":
                project.language = "JavaScript"
            elif project.language == "ts":
                project.language = "TypeScript"

        # Framework detection
        if (path / "package.json").exists():
            project.frameworks.append("Node.js")
        if (path / "requirements.txt").exists() or (path / "setup.py").exists():
            project.frameworks.append("Python")
        if (path / "Cargo.toml").exists():
            project.frameworks.append("Rust/Cargo")
        if (path / "go.mod").exists():
            project.frameworks.append("Go modules")
        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            project.frameworks.append("Java build")

    def update_todos(self, project_name: str, todos: List[str]) -> bool:
        """Update TODO list for project."""
        project = self.projects.get(project_name)
        if project:
            project.todos = todos
            project.last_active = datetime.now()
            self._save()
            return True
        return False

    def add_note(self, project_name: str, note: str) -> bool:
        """Add note to project."""
        project = self.projects.get(project_name)
        if project:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            project.notes += f"\n[{timestamp}] {note}"
            project.last_active = datetime.now()
            self._save()
            return True
        return False

    async def auto_detect_projects(self, search_paths: List[Path] = None) -> List[str]:
        """
        Auto-detect projects from git repositories.
        
        Args:
            search_paths: Directories to search (defaults to home)
        """
        if search_paths is None:
            search_paths = [Path.home()]

        detected = []
        for search_path in search_paths:
            if not search_path.exists():
                continue

            for git_dir in search_path.rglob(".git"):
                project_path = git_dir.parent
                name = project_path.name
                
                if name not in self.projects:
                    self.add_project(project_path, name)
                    detected.append(name)
                    logger.info(f"Auto-detected project: {name}")

        return detected

    def get_project_summary(self, name: str) -> str:
        """Get formatted project summary."""
        project = self.projects.get(name)
        if not project:
            return f"Project '{name}' not found"

        lines = [
            f"# {project.name}",
            f"Path: {project.path}",
            f"Language: {project.language or 'Unknown'}",
            f"Frameworks: {', '.join(project.frameworks) if project.frameworks else 'None'}",
            "",
            f"Git Branch: {project.git_branch or 'N/A'}",
            f"Git Status: {project.git_status or 'Clean'}",
            "",
        ]

        if project.todos:
            lines.append("TODOs:")
            for todo in project.todos:
                lines.append(f"  - {todo}")
            lines.append("")

        if project.notes:
            lines.append("Notes:")
            lines.append(project.notes[-500:])  # Last 500 chars

        return "\n".join(lines)
