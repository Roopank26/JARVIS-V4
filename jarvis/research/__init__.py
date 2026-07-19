"""
Research module for JARVIS.
Provides web research, news monitoring, citation generation, and report generation.
"""

from jarvis.research.research_agent import (
    ResearchAgent,
    get_research_agent,
    ResearchSource,
    ResearchResult,
    WebSearcher,
    NewsMonitor,
    CitationGenerator,
    ReportGenerator,
)
from jarvis.research.production import Source, CitationFormat

__all__ = [
    "ResearchAgent",
    "get_research_agent",
    "ResearchSource",
    "ResearchResult",
    "WebSearcher",
    "NewsMonitor",
    "CitationGenerator",
    "ReportGenerator",
    "Source",
    "CitationFormat",
]
