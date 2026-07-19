"""
JARVIS Research Agent - Autonomous Research System
Provides web search, news monitoring, citation generation, and report creation.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ResearchSource:
    """A research source."""
    url: str
    title: str
    snippet: str = ""
    source_name: str = ""
    published_date: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class ResearchResult:
    """Results from a research query."""
    query: str
    sources: List[ResearchSource]
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class WebSearcher:
    """Web search functionality using Tavily API or DuckDuckGo Lite."""
    
    def __init__(self, max_results: int = 10, api_key: str = None):
        self.max_results = max_results
        self.api_key = api_key
        self._tavily_available = False
        self._init_tavily()
    
    def _init_tavily(self):
        """Initialize Tavily API if available."""
        try:
            import os
            self.api_key = self.api_key or os.environ.get("TAVILY_API_KEY")
            if self.api_key:
                self._tavily_available = True
                logger.info("Tavily API configured for web search")
        except Exception:
            pass
    
    async def search(self, query: str, source: str = "auto", max_results: int = None) -> List[Dict[str, str]]:
        """
        Search the web for a query with automatic fallback chain.
        
        Args:
            query: Search query
            source: Search source (auto, tavily, duckduckgo)
            max_results: Override default max results
            
        Returns:
            List of search results with title, url, snippet
        """
        # Override max_results if provided
        original_max = self.max_results
        if max_results is not None:
            self.max_results = max_results
        
        try:
            # Try sources in order until we get results
            
            # 1. Try Tavily first if available
            if self._tavily_available and source in ("auto", "tavily"):
                results = await self._search_tavily(query)
                if results:
                    logger.info(f"Using Tavily: {len(results)} results")
                    return results
            
            # 2. Try Wikipedia API (free, reliable)
            results = await self._search_wikipedia(query)
            if results:
                logger.info(f"Using Wikipedia: {len(results)} results")
                return results
            
            # 3. Try DuckDuckGo Lite
            results = await self._search_duckduckgo(query)
            if results:
                logger.info(f"Using DuckDuckGo Lite: {len(results)} results")
                return results
            
            # 4. Try DuckDuckGo HTML as final fallback
            results = await self._search_ddg_html(query)
            if results:
                logger.info(f"Using DuckDuckGo HTML: {len(results)} results")
                return results
            
            logger.warning(f"No search results for: {query}")
            return []
        finally:
            # Restore original max_results
            self.max_results = original_max

    async def _search_wikipedia(self, query: str) -> List[Dict[str, str]]:
        """Search using Wikipedia API (free, no key needed)."""
        try:
            import aiohttp
            
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": query,
                "limit": self.max_results,
                "format": "json"
            }
            
            headers = {
                "User-Agent": "JARVIS-Research/1.0 (research agent)"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        
                        # Wikipedia API returns a list: [query, titles, descriptions, urls]
                        if isinstance(data, list) and len(data) >= 4:
                            titles = data[1]
                            descriptions = data[2]
                            urls = data[3]
                            
                            for i, title in enumerate(titles[:self.max_results]):
                                results.append({
                                    "url": urls[i] if i < len(urls) else f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    "title": title,
                                    "snippet": descriptions[i] if i < len(descriptions) else "",
                                    "source": "Wikipedia"
                                })
                        
                        return results
                        
        except Exception as e:
            logger.debug(f"Wikipedia search error: {e}")
        
        return []

    async def _search_ddg_html(self, query: str) -> List[Dict[str, str]]:
        """Final fallback: DuckDuckGo HTML."""
        try:
            import aiohttp
            
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        return self._parse_ddg_html_results(html)
                        
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML fallback error: {e}")
        
        return []

    def _parse_ddg_html_results(self, html: str) -> List[Dict[str, str]]:
        """Parse results from DuckDuckGo HTML."""
        results = []
        
        result_pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
        
        for match in re.finditer(result_pattern, html):
            url = match.group(1)
            title = re.sub(r'<[^>]+>', '', match.group(2))
            
            if url.startswith("http"):
                results.append({
                    "url": url,
                    "title": title.strip(),
                    "snippet": ""
                })
            
            if len(results) >= self.max_results:
                break
        
        return results
    
    async def _search_tavily(self, query: str) -> List[Dict[str, str]]:
        """Search using Tavily API."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = "https://api.tavily.com/search"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": self.max_results,
                    "include_answer": True,
                    "include_raw_content": False
                }
                
                async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        for item in data.get("results", []):
                            results.append({
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "snippet": item.get("content", "")[:300]
                            })
                        logger.info(f"Tavily returned {len(results)} results")
                        return results
                    else:
                        logger.warning(f"Tavily search failed: HTTP {resp.status}")
                        return []
                        
        except Exception as e:
            logger.warning(f"Tavily search error: {e}")
            return []
    
    async def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """Search using DuckDuckGo Lite."""
        try:
            import aiohttp
            
            # Use the lite version
            url = f"https://lite.duckduckgo.com/lite/?q={query.replace(' ', '+')}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        return self._parse_ddg_results(html)
                    else:
                        # Try Bing API as final fallback
                        return await self._search_bing(query)
                        
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")
            return []
    
    async def _search_bing(self, query: str) -> List[Dict[str, str]]:
        """Search using Bing API (free tier)."""
        try:
            import aiohttp
            
            # Bing Search API v7 (limited free tier)
            # Note: This requires a subscription for production use
            url = "https://api.bing.microsoft.com/v7.0/search"
            api_key = os.environ.get("BING_API_KEY")
            
            if not api_key:
                logger.debug("Bing API key not configured")
                return []
            
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {"q": query, "count": self.max_results}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = []
                        for item in data.get("webPages", {}).get("value", []):
                            results.append({
                                "url": item.get("url", ""),
                                "title": item.get("name", ""),
                                "snippet": item.get("snippet", "")[:300]
                            })
                        return results
                        
        except Exception:
            pass
        
        return []
    
    def _parse_ddg_results(self, html: str) -> List[Dict[str, str]]:
        """Parse search results from DuckDuckGo Lite HTML."""
        results = []
        
        # Pattern for DuckDuckGo Lite results
        result_pattern = r'<a rel="nofollow" href="([^"]+)">([^<]+)</a>'
        snippet_pattern = r'<p class="result-description">([^<]+)</p>'
        
        # Find all result blocks
        blocks = re.split(r'<div class="result">', html)
        
        for block in blocks[1:]:
            url_match = re.search(result_pattern, block)
            snippet_match = re.search(snippet_pattern, block)
            
            if url_match:
                url = url_match.group(1)
                title = re.sub(r'<[^>]+>', '', url_match.group(2))
                snippet = ""
                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1))
                
                if not url.startswith("/"):
                    results.append({
                        "url": url,
                        "title": title.strip(),
                        "snippet": snippet.strip()[:300]
                    })
                
                if len(results) >= self.max_results:
                    break
        
        return results
    
    # Alias for backwards compatibility
    _parse_results = _parse_ddg_results


class NewsMonitor:
    """Monitor news sources for topics."""
    
    NEWS_SOURCES = {
        "hackernews": "https://hn.algolia.com/api/v1/search?query={query}&tags=story",
        "reddit": "https://www.reddit.com/search.json?q={query}&sort=top",
        "arxiv": "https://export.arxiv.org/api/query?search_query=all:{query}&max_results=5",
    }
    
    # AI-focused news sources
    AI_NEWS_SOURCES = {
        "techcrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "venturebeat_ai": "https://venturebeat.com/category/ai/feed/",
        "arxiv_cs_ai": "https://export.arxiv.org/rss/cs.AI",
        "mit_ai": "https://news.mit.edu/rss/topic/artificial-intelligence2",
    }
    
    def __init__(self):
        self.tracked_topics: Dict[str, datetime] = {}
    
    async def fetch_news(self, query: str, source: str = "hackernews") -> List[Dict[str, Any]]:
        """
        Fetch news for a topic.
        
        Args:
            query: Topic to search
            source: News source (hackernews, reddit, arxiv)
            
        Returns:
            List of news items
        """
        try:
            import aiohttp
            
            url_template = self.NEWS_SOURCES.get(source, self.NEWS_SOURCES["hackernews"])
            url = url_template.format(query=query.replace(" ", "+"))
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        
                        if "json" in content_type:
                            data = await resp.json()
                            return self._parse_json_news(data, source)
                        else:
                            text = await resp.text()
                            return self._parse_atom_news(text)
                    
                    return []
                    
        except Exception as e:
            logger.warning(f"News fetch error ({source}): {e}")
            return []
    
    async def fetch_latest_ai_news(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Fetch the latest AI news from multiple sources.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of latest AI news items sorted by date
        """
        all_news = []
        
        # Try Hacker News AI topic
        try:
            import aiohttp
            url = "https://hn.algolia.com/api/v1/search?query=AI+artificial+intelligence&tags=story&numericFilters=created_at_i>{}".format(
                int((datetime.now() - timedelta(hours=hours)).timestamp())
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for hit in data.get("hits", [])[:15]:
                            all_news.append({
                                "title": hit.get("title", ""),
                                "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                                "points": hit.get("points", 0),
                                "date": hit.get("created_at", ""),
                                "source": "Hacker News",
                                "source_icon": "📰"
                            })
        except Exception as e:
            logger.warning(f"HN fetch error: {e}")
        
        # Try TechCrunch AI
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.AI_NEWS_SOURCES["techcrunch"], timeout=15) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        items = self._parse_rss_news(text, "TechCrunch")
                        all_news.extend(items)
        except Exception as e:
            logger.warning(f"TechCrunch fetch error: {e}")
        
        # Try MIT AI
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.AI_NEWS_SOURCES["mit_ai"], timeout=15) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        items = self._parse_rss_news(text, "MIT News")
                        all_news.extend(items)
        except Exception as e:
            logger.warning(f"MIT AI fetch error: {e}")
        
        # Sort by date (newest first)
        all_news.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return all_news[:20]
    
    def _parse_rss_news(self, xml: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse RSS/Atom news feed."""
        results = []
        
        entries = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        for entry in entries[:10]:
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', entry)
            link_match = re.search(r'<link[^>]*>([^<]+)</link>', entry)
            date_match = re.search(r'<pubDate>([^<]+)</pubDate>', entry)
            desc_match = re.search(r'<description[^>]*>([^<]+)</description>', entry)
            
            if title_match:
                results.append({
                    "title": title_match.group(1).strip(),
                    "url": link_match.group(1).strip() if link_match else "",
                    "date": date_match.group(1).strip() if date_match else "",
                    "snippet": desc_match.group(1)[:200] if desc_match else "",
                    "source": source_name,
                    "source_icon": "📰"
                })
        
        return results
    
    def _parse_json_news(self, data: Dict, source: str) -> List[Dict[str, Any]]:
        """Parse JSON news response."""
        results = []
        
        if source == "hackernews":
            for hit in data.get("hits", [])[:10]:
                results.append({
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "points": hit.get("points", 0),
                    "date": hit.get("created_at", ""),
                    "source": "Hacker News"
                })
        
        elif source == "reddit":
            for post in data.get("data", {}).get("children", [])[:10]:
                post_data = post.get("data", {})
                results.append({
                    "title": post_data.get("title", ""),
                    "url": post_data.get("url", ""),
                    "score": post_data.get("score", 0),
                    "comments": post_data.get("num_comments", 0),
                    "source": "Reddit"
                })
        
        return results
    
    def _parse_atom_news(self, xml: str) -> List[Dict[str, Any]]:
        """Parse Atom/RSS news response."""
        results = []
        
        entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
        for entry in entries[:10]:
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', entry)
            link_match = re.search(r'<link[^>]*href="([^"]+)"', entry)
            date_match = re.search(r'<published>([^<]+)</published>', entry)
            
            if title_match:
                results.append({
                    "title": title_match.group(1).strip(),
                    "url": link_match.group(1) if link_match else "",
                    "date": date_match.group(1) if date_match else "",
                    "source": "arXiv"
                })
        
        return results


class CitationGenerator:
    """Generate citations for sources."""
    
    @staticmethod
    def to_apa(source: Dict[str, str]) -> str:
        """Generate APA citation."""
        date = source.get("published_date", "n.d.")
        title = source.get("title", "Untitled")
        url = source.get("url", "")
        site = source.get("source_name", "Unknown")
        
        if date == "n.d.":
            citation = f"{site}. ({date}). {title}. Retrieved from {url}"
        else:
            year = date[:4] if len(date) >= 4 else date
            citation = f"{site}. ({year}). {title}. Retrieved from {url}"
        
        return citation
    
    @staticmethod
    def to_mla(source: Dict[str, str]) -> str:
        """Generate MLA citation."""
        date = source.get("published_date", "n.d.")
        title = source.get("title", "Untitled")
        url = source.get("url", "")
        site = source.get("source_name", "Unknown")
        
        citation = f'"{title}." {site}, {date}, {url}.'
        return citation
    
    @staticmethod
    def to_chicago(source: Dict[str, str]) -> str:
        """Generate Chicago citation."""
        date = source.get("published_date", "")
        title = source.get("title", "Untitled")
        url = source.get("url", "")
        site = source.get("source_name", "Unknown")
        
        citation = f'{site}. "{title}." {date}. {url}.'
        return citation
    
    @classmethod
    def generate_citations(cls, sources: List[Dict[str, str]], style: str = "apa") -> List[str]:
        """
        Generate citations in specified format.
        
        Args:
            sources: List of source dictionaries
            style: Citation style (apa, mla, chicago)
            
        Returns:
            List of formatted citations
        """
        citations = []
        
        for source in sources:
            if style.lower() == "apa":
                citations.append(cls.to_apa(source))
            elif style.lower() == "mla":
                citations.append(cls.to_mla(source))
            elif style.lower() == "chicago":
                citations.append(cls.to_chicago(source))
            else:
                # Default to APA
                citations.append(cls.to_apa(source))
        
        return citations


class ReportGenerator:
    """Generate research reports."""
    
    @staticmethod
    def generate_markdown(
        query: str,
        results: ResearchResult,
        include_citations: bool = True
    ) -> str:
        """Generate a markdown research report."""
        lines = [
            f"# Research Report: {query}",
            "",
            f"**Generated:** {results.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**Sources:** {len(results.sources)}",
            "",
            "---",
            "",
            "## Summary",
            "",
            results.summary or "No summary available.",
            "",
            "---",
            "",
            "## Key Findings",
            "",
        ]
        
        if results.key_findings:
            for i, finding in enumerate(results.key_findings, 1):
                lines.append(f"{i}. {finding}")
        else:
            lines.append("No key findings identified.")
        
        lines.extend([
            "",
            "---",
            "",
            "## Sources",
            "",
        ])
        
        for i, source in enumerate(results.sources, 1):
            lines.append(f"### {i}. {source.title}")
            lines.append(f"**URL:** {source.url}")
            if source.snippet:
                lines.append(f"**Excerpt:** {source.snippet}")
            lines.append("")
        
        if include_citations and results.citations:
            lines.extend([
                "---",
                "",
                "## Citations",
                "",
            ])
            for citation in results.citations:
                lines.append(f"- {citation}")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_html_report(
        query: str,
        results: ResearchResult,
        include_citations: bool = True
    ) -> str:
        """Generate an HTML research report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Research Report: {query}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }}
        h2 {{ color: #0066cc; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .source {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .source h3 {{ margin: 0 0 10px 0; }}
        .source a {{ color: #0066cc; }}
        .snippet {{ font-style: italic; color: #555; }}
        .citation {{ font-family: monospace; background: #eee; padding: 5px; }}
    </style>
</head>
<body>
    <h1>Research Report: {query}</h1>
    <div class="meta">
        <strong>Generated:</strong> {results.timestamp.strftime('%Y-%m-%d %H:%M')}<br>
        <strong>Sources:</strong> {len(results.sources)}
    </div>
    
    <h2>Summary</h2>
    <p>{results.summary or 'No summary available.'}</p>
    
    <h2>Key Findings</h2>
    <ul>
"""
        
        for finding in results.key_findings or ["No key findings identified."]:
            html += f"        <li>{finding}</li>\n"
        
        html += "    </ul>\n\n    <h2>Sources</h2>\n"
        
        for i, source in enumerate(results.sources, 1):
            html += f'''
    <div class="source">
        <h3>{i}. {source.title}</h3>
        <p><strong>URL:</strong> <a href="{source.url}">{source.url}</a></p>
'''
            if source.snippet:
                html += f'        <p class="snippet">"{source.snippet}"</p>\n'
            html += "    </div>\n"
        
        if include_citations and results.citations:
            html += "    <h2>Citations</h2>\n    <ul>\n"
            for citation in results.citations:
                html += f'        <li class="citation">{citation}</li>\n'
            html += "    </ul>\n"
        
        html += """
</body>
</html>"""
        
        return html


class ResearchAgent:
    """
    Autonomous research agent for JARVIS.
    
    Capabilities:
    - Web search
    - News monitoring (Hacker News, Reddit, arXiv)
    - Citation generation (APA, MLA, Chicago)
    - Report generation (Markdown, HTML)
    - Topic tracking
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".jarvis" / "research"
        self.web_searcher = WebSearcher()
        self.news_monitor = NewsMonitor()
        self.citation_generator = CitationGenerator()
        self.report_generator = ReportGenerator()
        self._history: List[ResearchResult] = []
    
    async def research(
        self,
        query: str,
        num_results: int = 10,
        generate_citations: bool = True,
        citation_style: str = "apa"
    ) -> ResearchResult:
        """
        Perform research on a topic.
        
        Args:
            query: Research query
            num_results: Number of results to fetch
            generate_citations: Whether to generate citations
            citation_style: Citation format (apa, mla, chicago)
            
        Returns:
            ResearchResult with sources, summary, and citations
        """
        # Search the web
        search_results = await self.web_searcher.search(query, max_results=num_results)
        
        # Create source objects
        sources = []
        for result in search_results:
            source = ResearchSource(
                url=result.get("url", ""),
                title=result.get("title", ""),
                snippet=result.get("snippet", ""),
                source_name=result.get("source_name", self._extract_domain(result.get("url", "")))
            )
            sources.append(source)
        
        # Generate summary (simple extraction)
        summary = self._generate_summary(sources)
        
        # Generate key findings
        key_findings = self._extract_key_findings(sources)
        
        # Generate citations
        citations = []
        if generate_citations:
            citation_sources = [
                {"url": s.url, "title": s.title, "source_name": s.source_name}
                for s in sources
            ]
            citations = self.citation_generator.generate_citations(citation_sources, citation_style)
        
        result = ResearchResult(
            query=query,
            sources=sources,
            summary=summary,
            key_findings=key_findings,
            citations=citations
        )
        
        self._history.append(result)
        return result
    
    async def monitor_topic(
        self,
        topic: str,
        source: str = "hackernews",
        max_items: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Monitor a topic across news sources.
        
        Args:
            topic: Topic to monitor
            source: News source (hackernews, reddit, arxiv)
            max_items: Maximum items to return
            
        Returns:
            List of news items
        """
        return await self.news_monitor.fetch_news(topic, source)
    
    async def get_latest_ai_news(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get the latest AI news from multiple sources.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of latest AI news items
        """
        return await self.news_monitor.fetch_latest_ai_news(hours=hours)
    
    def generate_report(
        self,
        query: str,
        results: ResearchResult,
        format: str = "markdown",
        include_citations: bool = True
    ) -> str:
        """
        Generate a research report.
        
        Args:
            query: Research query
            results: ResearchResult from research()
            format: Output format (markdown, html)
            include_citations: Include citations in report
            
        Returns:
            Formatted report string
        """
        if format.lower() == "html":
            return self.report_generator.generate_html_report(query, results, include_citations)
        else:
            return self.report_generator.generate_markdown(query, results, include_citations)
    
    def save_report(
        self,
        query: str,
        results: ResearchResult,
        output_path: Path,
        format: str = "markdown"
    ) -> Path:
        """
        Save a research report to file.
        
        Args:
            query: Research query
            results: ResearchResult
            output_path: Output file path
            format: Output format
            
        Returns:
            Path to saved file
        """
        report = self.generate_report(query, results, format)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add appropriate extension
        if not output_path.suffix:
            output_path = output_path.with_suffix(".md" if format == "markdown" else ".html")
        
        output_path.write_text(report)
        logger.info(f"Report saved to: {output_path}")
        
        return output_path
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else "Unknown"
    
    def _generate_summary(self, sources: List[ResearchSource]) -> str:
        """Generate a simple summary from sources."""
        if not sources:
            return "No sources found."
        
        # Combine snippets
        combined = " ".join([s.snippet for s in sources if s.snippet])
        
        if not combined:
            return f"Research on '{sources[0].title if sources else 'unknown'}' found {len(sources)} sources."
        
        # Simple truncation if too long
        if len(combined) > 500:
            combined = combined[:500] + "..."
        
        return combined
    
    def _extract_key_findings(self, sources: List[ResearchSource]) -> List[str]:
        """Extract key findings from sources."""
        findings = []
        
        for source in sources[:5]:  # Top 5 sources
            if source.snippet:
                # Extract first meaningful sentence
                sentences = re.split(r'[.!?]', source.snippet)
                if sentences and sentences[0].strip():
                    findings.append(sentences[0].strip() + ".")
        
        return findings[:5]  # Return top 5 findings
    
    def get_history(self) -> List[ResearchResult]:
        """Get research history."""
        return self._history


# Global research agent instance
_research_agent: Optional[ResearchAgent] = None


def get_research_agent() -> ResearchAgent:
    """Get or create global research agent."""
    global _research_agent
    if _research_agent is None:
        _research_agent = ResearchAgent()
    return _research_agent
