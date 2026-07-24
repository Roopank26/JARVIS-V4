"""
Tests for JARVIS Repository Reasoning.
"""

from pathlib import Path

from jarvis.repo.analyzer import RepositoryAnalyzer


class TestRepositoryReasoning:
    def test_heuristic_insights_returns_list(self, tmp_path: Path):
        analyzer = RepositoryAnalyzer(str(tmp_path))
        result = analyzer.get_llm_insights()
        assert isinstance(result, dict)
        assert "source" in result
        assert "insights" in result
        assert isinstance(result["insights"], str)
        assert len(result["insights"]) > 0

    def test_heuristic_insights_without_llm(self, tmp_path: Path, monkeypatch):
        class DummyClient:
            def is_available(self):
                return False

        monkeypatch.setattr("jarvis.api.gemini.SimpleLLMClient", lambda: DummyClient(), raising=False)
        analyzer = RepositoryAnalyzer(str(tmp_path))
        result = analyzer.get_llm_insights()
        assert result["source"] == "heuristic"

    def test_llm_insights_with_query(self, tmp_path: Path, monkeypatch):
        class FakeClient:
            def is_available(self):
                return True

            async def generate(self, system="", prompt="", temperature=0.2, max_tokens=1024, model=None):
                return "Consider breaking large functions into smaller, testable units."

        monkeypatch.setattr("jarvis.api.gemini.SimpleLLMClient", lambda: FakeClient(), raising=False)
        analyzer = RepositoryAnalyzer(str(tmp_path))
        result = analyzer.get_llm_insights(query="improve testing")
        assert result["source"] == "llm"
        assert "smaller" in result["insights"]
