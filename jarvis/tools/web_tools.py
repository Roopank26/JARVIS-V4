"""
Web content utilities for JARVIS.
Provides fetching, content extraction, and text summarization.
"""

import asyncio

import requests
from bs4 import BeautifulSoup


class WebTools:
    """Web content utilities."""

    @staticmethod
    async def fetch_content(url: str) -> str:
        """Fetch a URL and return its text content using requests + BeautifulSoup."""
        try:
            response = await asyncio.to_thread(requests.get, url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except Exception as e:
            return f"Error fetching {url}: {e!s}"

    @staticmethod
    def extract_main_content(html: str) -> str:
        """Extract main article text from HTML, removing boilerplate."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["nav", "aside", "footer", "header", "script", "style", "noscript", "iframe"]):
                tag.decompose()

            main_content = soup.find("article")
            if not main_content:
                main_content = soup.find("main")
            if not main_content:
                main_content = soup.find(id="content")
            if not main_content:
                main_content = soup.body

            if not main_content:
                return ""
            return main_content.get_text(separator="\n", strip=True)
        except Exception as e:
            return f"Error extracting content: {e!s}"

    @staticmethod
    def summarize_text(text: str, max_length: int = 500) -> str:
        """Summarize text by keeping first paragraphs, trimming to max_length."""
        if not text:
            return ""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        result = ""
        for p in paragraphs:
            if len(result) + len(p) + 1 > max_length:
                break
            result += p + "\n"
        if len(result) > max_length:
            result = result[:max_length].rstrip() + "..."
        return result.strip()
