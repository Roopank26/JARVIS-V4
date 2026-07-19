"""
Research module for JARVIS.
Provides web research, news monitoring, citation generation, and report generation.
"""

from jarvis.research.production import CitationFormat, Source
from jarvis.research.research_agent import (
    CitationGenerator,
    NewsMonitor,
    ReportGenerator,
    ResearchAgent,
    ResearchResult,
    ResearchSource,
    WebSearcher,
    get_research_agent,
)

__all__ = [
    "CitationFormat",
    "CitationGenerator",
    "NewsMonitor",
    "ReportGenerator",
    "ResearchAgent",
    "ResearchResult",
    "ResearchSource",
    "Source",
    "WebSearcher",
    "get_research_agent",
]
