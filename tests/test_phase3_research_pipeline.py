"""
Phase 3 Research Pipeline Tests
"""

import pytest

from jarvis.research.pipeline import ResearchPipeline


@pytest.mark.asyncio
async def test_pipeline_run_unavailable():
    pipeline = ResearchPipeline()
    pipeline._agent = None
    result = await pipeline.run("AI trends")
    assert result.query == "AI trends"
    assert result.confidence == 0.0


def test_estimate_confidence_no_sources():
    pipeline = ResearchPipeline()
    result = pipeline._estimate_confidence(type("R", (), {"sources": [], "citations": []})())
    assert result == 0.0


def test_generate_report():
    pipeline = ResearchPipeline()
    result = type("R", (), {
        "query": "test",
        "summary": "summary text",
        "key_findings": ["a", "b"],
        "sources": [type("S", (), {"url": "http://a.com", "title": "A", "source_name": "Web"})(), type("S", (), {"url": "http://b.com", "title": "B", "source_name": "Web"})()],
        "citations": ["cite1"],
    })()
    report = pipeline._generate_report(result)
    assert "# Research Report: test" in report
    assert "summary text" in report
