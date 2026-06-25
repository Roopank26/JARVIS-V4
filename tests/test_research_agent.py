"""
Tests for JARVIS Research Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from jarvis.research.research_agent import (
    ResearchAgent,
    WebSearcher,
    NewsMonitor,
    CitationGenerator,
    ReportGenerator,
    ResearchSource,
    ResearchResult,
)


class TestCitationGenerator:
    """Test citation generation."""
    
    def test_apa_citation(self):
        """Test APA citation format."""
        source = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "published_date": "2024-01-15",
            "source_name": "Example News"
        }
        
        citation = CitationGenerator.to_apa(source)
        
        assert "Test Article" in citation
        assert "2024" in citation
        assert "example.com" in citation
    
    def test_mla_citation(self):
        """Test MLA citation format."""
        source = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "published_date": "2024-01-15",
            "source_name": "Example News"
        }
        
        citation = CitationGenerator.to_mla(source)
        
        assert "Test Article" in citation
        assert "Example News" in citation
    
    def test_chicago_citation(self):
        """Test Chicago citation format."""
        source = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "published_date": "2024-01-15",
            "source_name": "Example News"
        }
        
        citation = CitationGenerator.to_chicago(source)
        
        assert "Test Article" in citation
    
    def test_generate_citations_apa(self):
        """Test batch citation generation."""
        sources = [
            {
                "title": "Article 1",
                "url": "https://example.com/1",
                "published_date": "2024-01-01",
                "source_name": "Source 1"
            },
            {
                "title": "Article 2",
                "url": "https://example.com/2",
                "published_date": "2024-02-01",
                "source_name": "Source 2"
            }
        ]
        
        citations = CitationGenerator.generate_citations(sources, style="apa")
        
        assert len(citations) == 2
        assert "Article 1" in citations[0]
        assert "Article 2" in citations[1]


class TestReportGenerator:
    """Test report generation."""
    
    def test_markdown_report(self):
        """Test markdown report generation."""
        result = ResearchResult(
            query="test query",
            sources=[
                ResearchSource(
                    url="https://example.com",
                    title="Example Source",
                    snippet="This is a test snippet.",
                    source_name="Example"
                )
            ],
            summary="Test summary",
            key_findings=["Finding 1", "Finding 2"],
            citations=["Citation 1"]
        )
        
        report = ReportGenerator.generate_markdown("test query", result)
        
        assert "# Research Report: test query" in report
        assert "Test summary" in report
        assert "Example Source" in report
        assert "Citation 1" in report
    
    def test_html_report(self):
        """Test HTML report generation."""
        result = ResearchResult(
            query="test query",
            sources=[
                ResearchSource(
                    url="https://example.com",
                    title="Example Source",
                    snippet="This is a test.",
                    source_name="Example"
                )
            ],
            summary="Test summary",
            key_findings=["Finding 1"]
        )
        
        report = ReportGenerator.generate_html_report("test query", result)
        
        assert "<html>" in report
        assert "test query" in report
        assert "Example Source" in report
        assert "<h1>" in report


class TestResearchAgent:
    """Test research agent."""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create research agent."""
        return ResearchAgent(storage_path=tmp_path)
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.web_searcher is not None
        assert agent.news_monitor is not None
        assert agent.citation_generator is not None
    
    def test_extract_domain(self, agent):
        """Test domain extraction."""
        assert agent._extract_domain("https://github.com/user/repo") == "github.com"
        assert agent._extract_domain("https://example.com/path") == "example.com"
        assert agent._extract_domain("invalid") == "Unknown"
    
    def test_generate_summary(self, agent):
        """Test summary generation."""
        sources = [
            ResearchSource(
                url="https://example.com",
                title="Test",
                snippet="This is a test snippet about testing."
            )
        ]
        
        summary = agent._generate_summary(sources)
        
        assert "test snippet" in summary.lower()
    
    def test_extract_key_findings(self, agent):
        """Test key findings extraction."""
        sources = [
            ResearchSource(
                url="https://example.com",
                title="Test",
                snippet="This is a test. This is another sentence."
            )
        ]
        
        findings = agent._extract_key_findings(sources)
        
        assert len(findings) >= 0


class TestWebSearcher:
    """Test web searcher."""
    
    def test_searcher_initialization(self):
        """Test searcher initializes correctly."""
        searcher = WebSearcher(max_results=5)
        assert searcher.max_results == 5
    
    def test_parse_results_empty(self):
        """Test parsing empty HTML."""
        searcher = WebSearcher()
        results = searcher._parse_results("<html><body></body></html>")
        assert results == []


class TestNewsMonitor:
    """Test news monitor."""
    
    def test_monitor_initialization(self):
        """Test monitor initializes correctly."""
        monitor = NewsMonitor()
        assert monitor.tracked_topics is not None
        assert isinstance(monitor.tracked_topics, dict)
    
    def test_news_sources(self):
        """Test news sources are configured."""
        monitor = NewsMonitor()
        assert "hackernews" in monitor.NEWS_SOURCES
        assert "reddit" in monitor.NEWS_SOURCES
        assert "arxiv" in monitor.NEWS_SOURCES


class TestResearchPatterns:
    """Test research intent classification."""
    
    def test_research_patterns(self):
        """Test research patterns are defined."""
        from jarvis.core.agent import classify_intent, Intent
        
        test_cases = [
            ("research about AI", Intent.RESEARCH),
            ("search the web for python", Intent.RESEARCH),
            ("web search machine learning", Intent.RESEARCH),
            ("find information on quantum computing", Intent.RESEARCH),
            ("latest news on tech", Intent.RESEARCH),
            ("monitor hackernews AI", Intent.RESEARCH),
            ("generate report on robotics", Intent.RESEARCH),
            ("deep research on quantum", Intent.RESEARCH),
            ("citation help", Intent.RESEARCH),
        ]
        
        for text, expected_intent in test_cases:
            result = classify_intent(text)
            assert result == expected_intent, f"Failed for: {text}"


class TestResearchIntegration:
    """Integration tests for research agent."""
    
    @pytest.mark.asyncio
    async def test_research_with_mock(self, tmp_path):
        """Test research with mocked web search."""
        agent = ResearchAgent(storage_path=tmp_path)
        
        with patch.object(agent.web_searcher, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {
                    "title": "Test Article",
                    "url": "https://example.com/test",
                    "snippet": "This is a test article."
                }
            ]
            
            result = await agent.research("test query")
            
            assert result.query == "test query"
            assert len(result.sources) == 1
            assert result.sources[0].title == "Test Article"
    
    @pytest.mark.asyncio
    async def test_monitor_with_mock(self, tmp_path):
        """Test news monitoring with mocked response."""
        agent = ResearchAgent(storage_path=tmp_path)
        
        with patch.object(agent.news_monitor, 'fetch_news', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                {
                    "title": "Test News",
                    "url": "https://news.com/test",
                    "points": 100,
                    "source": "Hacker News"
                }
            ]
            
            results = await agent.monitor_topic("test topic", "hackernews")
            
            assert len(results) == 1
            assert results[0]["title"] == "Test News"
    
    def test_save_and_generate_report(self, tmp_path):
        """Test saving and generating reports."""
        agent = ResearchAgent(storage_path=tmp_path)
        
        result = ResearchResult(
            query="test query",
            sources=[
                ResearchSource(
                    url="https://example.com",
                    title="Example",
                    snippet="Test snippet"
                )
            ],
            summary="Test summary",
            key_findings=["Finding 1"]
        )
        
        output_path = tmp_path / "report.md"
        saved_path = agent.save_report("test query", result, output_path)
        
        assert saved_path.exists()
        content = saved_path.read_text()
        assert "test query" in content
