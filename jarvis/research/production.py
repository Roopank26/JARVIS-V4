"""
JARVIS Production Research Agent
Professional research with multi-source search and citations.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("jarvis.research")


class CitationFormat(Enum):
    """Citation format styles."""

    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"


@dataclass
class Source:
    """A research source."""

    title: str
    url: str
    content: str = ""
    author: str = ""
    publisher: str = ""
    published_date: str = ""
    accessed_date: str = ""
    source_type: str = "web"  # web, article, paper, book, etc.
    relevance_score: float = 0.0

    def to_citation(self, format: CitationFormat) -> str:
        """Generate citation in specified format."""
        date = self.published_date or self.accessed_date or datetime.now().strftime("%Y")

        if format == CitationFormat.APA:
            author = f"{self.author} " if self.author else ""
            date_str = f"({date})" if date else "(n.d.)"
            title = f"{self.title}. "
            url = f"{self.url}" if self.url else ""
            return f"{author}{date_str} {title}{url}"

        elif format == CitationFormat.MLA:
            author = f"{self.author}. " if self.author else ""
            title = f'"{self.title}." ' if self.title else ""
            publisher = f"{self.publisher}, " if self.publisher else ""
            date_str = f"{date}. " if date else ""
            url = f"{self.url}" if self.url else ""
            return f"{author}{title}{publisher}{date_str}{url}"

        elif format == CitationFormat.IEEE:
            author = f"{self.author}, " if self.author else ""
            title = f'"{self.title}," ' if self.title else ""
            publisher = f"{self.publisher}, " if self.publisher else ""
            date_str = f"{date}. " if date else ""
            url = f"[Online]. Available: {self.url}" if self.url else ""
            return f"{author}{title}{publisher}{date_str}{url}"

        elif format == CitationFormat.CHICAGO:
            author = f"{self.author}. " if self.author else ""
            title = f'"{self.title}." ' if self.title else ""
            publisher = f"{self.publisher}. " if self.publisher else ""
            date_str = f"{date}. " if date else ""
            url = f"{self.url}" if self.url else ""
            return f"{author}{title}{publisher}{date_str}{url}"

        return f"{self.title}. {self.url}"


@dataclass
class ProductionResearchResult:
    """Result from production research query."""

    query: str
    findings: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    summary: str = ""
    citations: list[str] = field(default_factory=list)
    conflicting_info: list[dict[str, str]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class WebSearchProvider(ABC):
    """Abstract base for web search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[Source]:
        """Search for sources."""
        pass

    @abstractmethod
    async def extract_content(self, url: str) -> str:
        """Extract content from URL."""
        pass


class DuckDuckGoSearch(WebSearchProvider):
    """DuckDuckGo search provider."""

    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[Source]:
        """Search using DuckDuckGo."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                # DuckDuckGo Instant Answer API
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    sources = []

                    # Extract from Related Topics
                    for topic in data.get("RelatedTopics", [])[:num_results]:
                        if "Text" in topic and "FirstURL" in topic:
                            sources.append(
                                Source(
                                    title=topic.get("Text", "")[:100],
                                    url=topic.get("FirstURL", ""),
                                    content=topic.get("Text", ""),
                                    source_type="web",
                                )
                            )

                    return sources

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")

        return []

    async def extract_content(self, url: str) -> str:
        """Extract content from URL."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    # Simple HTML to text
                    html = response.text
                    text = re.sub(r"<[^>]+>", " ", html)
                    text = re.sub(r"\s+", " ", text)
                    return text[:5000]  # Limit length

        except Exception as e:
            logger.error(f"Content extraction error: {e}")

        return ""


class WikipediaSearch(WebSearchProvider):
    """Wikipedia search provider."""

    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[Source]:
        """Search Wikipedia."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "srlimit": num_results,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    sources = []

                    for result in data.get("query", {}).get("search", []):
                        title = result.get("title", "")

                        sources.append(
                            Source(
                                title=title,
                                url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                content=result.get("snippet", ""),
                                source_type="encyclopedia",
                                relevance_score=result.get("size", 0) / 1000,
                            )
                        )

                    return sources

        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")

        return []

    async def extract_content(self, url: str) -> str:
        """Extract content from Wikipedia page."""
        try:
            import httpx

            # Extract page title from URL
            match = re.search(r"wikipedia\.org/wiki/([^/]+)", url)
            if not match:
                return ""

            title = match.group(1)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "titles": title,
                        "prop": "extracts",
                        "explaintext": True,
                        "format": "json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    pages = data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        return page.get("extract", "")[:5000]

        except Exception as e:
            logger.error(f"Wikipedia extraction error: {e}")

        return ""


class GitHubSearch(WebSearchProvider):
    """GitHub search provider."""

    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[Source]:
        """Search GitHub repositories."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": query, "per_page": num_results},
                    headers={"Accept": "application/vnd.github.v3+json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    sources = []

                    for repo in data.get("items", []):
                        sources.append(
                            Source(
                                title=repo.get("full_name", ""),
                                url=repo.get("html_url", ""),
                                content=repo.get("description", ""),
                                author=repo.get("owner", {}).get("login", ""),
                                published_date=repo.get("created_at", "")[:4],
                                source_type="repository",
                            )
                        )

                    return sources

        except Exception as e:
            logger.error(f"GitHub search error: {e}")

        return []

    async def extract_content(self, url: str) -> str:
        """GitHub doesn't support direct content extraction."""
        return ""


class ArxivSearch(WebSearchProvider):
    """arXiv paper search."""

    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[Source]:
        """Search arXiv papers."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "http://export.arxiv.org/api/query",
                    params={
                        "search_query": f"all:{query}",
                        "max_results": num_results,
                    },
                )

                if response.status_code == 200:
                    # Parse XML response
                    xml = response.text
                    sources = []

                    # Simple regex extraction (in production, use proper XML parsing)
                    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)

                    for entry in entries:
                        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
                        link = re.search(r"<id>(.*?)</id>", entry)
                        author = re.search(r"<name>(.*?)</name>", entry)
                        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)

                        sources.append(
                            Source(
                                title=title.group(1).strip().replace("\n", " ") if title else "",
                                url=link.group(1) if link else "",
                                content=summary.group(1)[:500] if summary else "",
                                author=author.group(1) if author else "",
                                source_type="paper",
                            )
                        )

                    return sources

        except Exception as e:
            logger.error(f"arXiv search error: {e}")

        return []

    async def extract_content(self, url: str) -> str:
        """Extract paper abstract."""
        # arXiv content extraction is complex, skip for now
        return ""


class ResearchAgent:
    """
    Professional research agent with multi-source search and citations.

    Features:
    - DuckDuckGo web search
    - Wikipedia encyclopedia
    - GitHub repositories
    - arXiv papers
    - Automatic citation generation
    - Source comparison
    - Conflict detection
    """

    def __init__(self):
        self._providers: dict[str, WebSearchProvider] = {
            "duckduckgo": DuckDuckGoSearch(),
            "wikipedia": WikipediaSearch(),
            "github": GitHubSearch(),
            "arxiv": ArxivSearch(),
        }

        self._default_providers = ["duckduckgo", "wikipedia"]

    async def research(
        self,
        query: str,
        providers: list[str] | None = None,
        num_results: int = 10,
        citation_format: CitationFormat = CitationFormat.APA,
    ) -> ProductionResearchResult:
        """
        Conduct research on a topic.

        Args:
            query: Research query
            providers: List of providers to use (default: duckduckgo, wikipedia)
            num_results: Number of results per provider
            citation_format: Format for citations

        Returns:
            ProductionResearchResult with findings, sources, and citations
        """
        logger.info(f"Researching: {query}")

        providers = providers or self._default_providers
        result = ProductionResearchResult(query=query)

        # Search all providers
        for provider_name in providers:
            if provider_name in self._providers:
                try:
                    sources = await self._providers[provider_name].search(query, num_results)
                    result.sources.extend(sources)
                except Exception as e:
                    logger.error(f"{provider_name} search failed: {e}")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_sources = []
        for source in result.sources:
            if source.url and source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)
        result.sources = unique_sources

        # Generate citations
        result.citations = [source.to_citation(citation_format) for source in result.sources]

        # Detect conflicts
        result.conflicting_info = self._detect_conflicts(result.sources)

        # Generate summary
        result.summary = self._generate_summary(query, result.sources)

        logger.info(f"Research complete: {len(result.sources)} sources found")

        return result

    def _detect_conflicts(
        self,
        sources: list[Source],
    ) -> list[dict[str, str]]:
        """Detect conflicting information."""
        conflicts = []

        # Simple conflict detection based on content similarity
        for i, source1 in enumerate(sources):
            for source2 in sources[i + 1 :]:
                # Check if content is contradictory (very simplified)
                content1 = source1.content.lower()
                content2 = source2.content.lower()

                # Look for negation patterns
                negations = ["not", "never", "no ", "don't", "doesn't", "isn't", "aren't"]
                has_negation1 = any(neg in content1[:200] for neg in negations)
                has_negation2 = any(neg in content2[:200] for neg in negations)

                if has_negation1 != has_negation2:
                    conflicts.append(
                        {
                            "source1": source1.title[:50],
                            "source2": source2.title[:50],
                            "type": "potential_contradiction",
                        }
                    )

        return conflicts[:5]  # Limit to 5 conflicts

    def _generate_summary(
        self,
        query: str,
        sources: list[Source],
    ) -> str:
        """Generate a summary of findings."""
        if not sources:
            return "No sources found."

        lines = [
            f"## Research Summary: {query}",
            "",
            f"Found {len(sources)} relevant sources.",
            "",
            "### Key Findings",
            "",
        ]

        for i, source in enumerate(sources[:5], 1):
            lines.append(f"{i}. **{source.title}**")
            if source.content:
                # Truncate content
                content = source.content[:200]
                lines.append(f"   {content}...")
            lines.append("")

        return "\n".join(lines)

    async def compare_sources(
        self,
        sources: list[str],
    ) -> str:
        """
        Compare multiple sources on a topic.

        Args:
            sources: List of URLs to compare

        Returns:
            Comparison report
        """
        lines = ["## Source Comparison", ""]

        source_data = []
        for url in sources:
            provider = self._get_provider_for_url(url)
            if provider:
                content = await provider.extract_content(url)
                source_data.append((url, content))

        # Generate comparison
        if source_data:
            lines.append(f"Compared {len(source_data)} sources.")
            lines.append("")

            for url, content in source_data:
                lines.append(f"### {url}")
                lines.append(f"{content[:500]}...")
                lines.append("")

        return "\n".join(lines)

    def _get_provider_for_url(self, url: str) -> WebSearchProvider | None:
        """Get appropriate provider for URL."""
        if "wikipedia.org" in url:
            return self._providers.get("wikipedia")
        elif "github.com" in url:
            return self._providers.get("github")
        elif "arxiv.org" in url:
            return self._providers.get("arxiv")
        elif url:
            return self._providers.get("duckduckgo")
        return None

    async def generate_report(
        self,
        research: ProductionResearchResult,
        title: str = "Research Report",
        citation_format: CitationFormat = CitationFormat.APA,
    ) -> str:
        """
        Generate a full research report.

        Args:
            research: ProductionResearchResult to format
            title: Report title
            citation_format: Citation format

        Returns:
            Formatted report
        """
        lines = [
            f"# {title}",
            "",
            f"**Query:** {research.query}",
            f"**Date:** {research.timestamp.strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
        ]

        # Summary
        if research.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(research.summary)
            lines.append("")

        # Findings
        if research.findings:
            lines.append("## Key Findings")
            lines.append("")
            for finding in research.findings:
                lines.append(f"- {finding}")
            lines.append("")

        # Conflicts
        if research.conflicting_info:
            lines.append("## Potential Conflicts")
            lines.append("")
            for conflict in research.conflicting_info:
                lines.append(
                    f"- **{conflict['type']}** between {conflict['source1']} and {conflict['source2']}"
                )
            lines.append("")

        # Sources
        if research.sources:
            lines.append("## Sources")
            lines.append("")
            for source in research.sources:
                citation = source.to_citation(citation_format)
                lines.append(f"- {citation}")
            lines.append("")

        return "\n".join(lines)

    def add_provider(self, name: str, provider: WebSearchProvider) -> None:
        """Add a search provider."""
        self._providers[name] = provider

    def get_status(self) -> dict[str, Any]:
        """Get research agent status."""
        return {
            "providers": list(self._providers.keys()),
            "default_providers": self._default_providers,
        }
