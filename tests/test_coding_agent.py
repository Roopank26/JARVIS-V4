"""
Tests for Coding Agent - Repository Intelligence System.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

from jarvis.coding.coding_agent import (
    RepositoryIndexer,
    CodeAnalyzer,
    GitIntegration,
    CodeFile,
    ProjectMap,
)


class TestRepositoryIndexer:
    """Tests for RepositoryIndexer."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("class Main:\n    def run(self): pass\ndef main(): Main().run()")
            (root / "utils.py").write_text("def helper(): pass\ndef process(): pass")
            js_dir = root / "src"
            js_dir.mkdir()
            (js_dir / "app.js").write_text("const app = () => { console.log('Hello'); };")
            (root / "README.md").write_text("# Test Project\n## Features")
            yield root

    @pytest.mark.asyncio
    async def test_index_python_repo(self, temp_repo):
        """Test indexing a Python repository."""
        indexer = RepositoryIndexer(temp_repo)
        project_map = await indexer.index()
        
        assert project_map.file_count >= 3
        assert "python" in project_map.language_stats
        assert project_map.language_stats["python"] >= 2

    @pytest.mark.asyncio
    async def test_extract_from_project_map(self, temp_repo):
        """Test extracting from indexed project."""
        indexer = RepositoryIndexer(temp_repo)
        project_map = await indexer.index()
        
        main_file = project_map.files.get("main.py")
        assert main_file is not None
        assert main_file.language == "python"
        assert "Main" in main_file.classes

    @pytest.mark.asyncio
    async def test_analyze_file(self, temp_repo):
        """Test file analysis."""
        indexer = RepositoryIndexer(temp_repo)
        project_map = await indexer.index()
        analyzer = CodeAnalyzer(project_map)
        analysis = analyzer.analyze_file("main.py")
        
        assert "path" in analysis
        assert analysis["language"] == "python"
        assert analysis["lines"] > 0

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_file(self, temp_repo):
        """Test analyzing non-existent file."""
        indexer = RepositoryIndexer(temp_repo)
        project_map = await indexer.index()
        analyzer = CodeAnalyzer(project_map)
        analysis = analyzer.analyze_file("nonexistent.py")
        
        assert "error" in analysis

    def test_format_summary(self, temp_repo):
        """Test project summary formatting."""
        indexer = RepositoryIndexer(temp_repo)
        asyncio.run(indexer.index())
        summary = indexer.format_summary()
        
        assert "Project" in summary
        assert "Files" in summary
        assert "Languages" in summary


class TestGitIntegration:
    """Tests for GitIntegration."""

    def test_init(self):
        """Test GitIntegration initialization."""
        git = GitIntegration()
        assert git.repo_path == Path.cwd()

    def test_custom_repo_path(self):
        """Test custom repo path."""
        path = Path("/tmp/test")
        git = GitIntegration(path)
        assert git.repo_path == path

    @pytest.mark.asyncio
    async def test_get_branch(self):
        """Test getting current branch."""
        git = GitIntegration()
        branch = await git.get_branch()
        assert isinstance(branch, str)


class TestProjectMap:
    """Tests for ProjectMap."""

    def test_create(self):
        """Test creating a ProjectMap."""
        pm = ProjectMap(root=Path("/tmp"))
        assert pm.root == Path("/tmp")
        assert pm.files == {}
        assert pm.language_stats == {}


class TestCodeFile:
    """Tests for CodeFile."""

    def test_create(self):
        """Test creating a CodeFile."""
        cf = CodeFile(path=Path("test.py"), language="python", lines=100, size=1024)
        assert cf.path == Path("test.py")
        assert cf.language == "python"
        assert cf.lines == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
