"""
Browser automation tools for JARVIS using Selenium.
Provides web browsing, form filling, and element interaction.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup

from jarvis.tools.base import ReadOnlyTool, ToolResult


@dataclass
class BrowserConfig:
    """Browser automation configuration."""

    headless: bool = True
    browser: str = "chrome"  # chrome, firefox, edge
    timeout: int = 30
    window_size: tuple = (1920, 1080)


class BrowserTool(ReadOnlyTool):
    """Base browser tool."""

    CATEGORY = "browser"

    def __init__(self, config: BrowserConfig | None = None):
        self.config = config or BrowserConfig()
        self._driver = None
        self._implicit_wait = 10

    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return "Web browser automation - navigate, click, fill forms, extract content"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "open",
                        "navigate",
                        "click",
                        "fill",
                        "submit",
                        "get_text",
                        "get_html",
                        "screenshot",
                        "back",
                        "forward",
                        "refresh",
                        "close",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {"type": "string", "description": "URL for navigate/open actions"},
                "selector": {"type": "string", "description": "CSS selector or XPath"},
                "value": {"type": "string", "description": "Value for fill/submit actions"},
                "timeout": {"type": "number", "description": "Action timeout in seconds"},
            },
            "required": ["action"],
        }

    def _get_driver(self):
        """Get or create WebDriver instance."""
        if self._driver is None:
            self._init_driver()
        return self._driver

    def _init_driver(self):
        """Initialize WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager

            options = ChromeOptions()
            if self.config.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(
                f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}"
            )

            service = ChromeService(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.implicitly_wait(self._implicit_wait)

        except ImportError as err:
            raise ImportError(
                "Selenium not installed. Run: pip install selenium webdriver-manager"
            ) from err
        except Exception as e:
            raise RuntimeError(f"Failed to initialize browser: {e}") from e

    def _find_element(self, selector: str):
        """Find element by selector (CSS or XPath)."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = self._get_driver()
        timeout = self.config.timeout

        if selector.startswith("//") or selector.startswith("(//"):
            # XPath
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
        else:
            # CSS selector
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

    async def execute(
        self,
        action: str,
        url: str = None,
        selector: str = None,
        value: str = None,
        timeout: int = None,
    ) -> ToolResult:
        """Execute browser action."""
        try:
            if timeout:
                self.config.timeout = timeout

            if action == "open":
                if not url:
                    return ToolResult(success=False, output="URL required for 'open' action")
                driver = self._get_driver()
                driver.get(url)
                return ToolResult(success=True, output=f"Opened: {url}")

            elif action == "navigate":
                if not url:
                    return ToolResult(success=False, output="URL required for 'navigate' action")
                driver = self._get_driver()
                driver.navigate_to(url) if hasattr(driver, "navigate_to") else driver.get(url)
                return ToolResult(success=True, output=f"Navigated to: {url}")

            elif action == "click":
                if not selector:
                    return ToolResult(success=False, output="Selector required for 'click' action")
                element = self._find_element(selector)
                element.click()
                return ToolResult(success=True, output=f"Clicked: {selector}")

            elif action == "fill":
                if not selector or value is None:
                    return ToolResult(
                        success=False, output="Selector and value required for 'fill' action"
                    )
                element = self._find_element(selector)
                element.clear()
                element.send_keys(value)
                return ToolResult(success=True, output=f"Filled '{value}' in: {selector}")

            elif action == "submit":
                if not selector:
                    return ToolResult(success=False, output="Selector required for 'submit' action")
                element = self._find_element(selector)
                element.submit()
                return ToolResult(success=True, output=f"Submitted: {selector}")

            elif action == "get_text":
                if not selector:
                    return ToolResult(
                        success=False, output="Selector required for 'get_text' action"
                    )
                element = self._find_element(selector)
                return ToolResult(success=True, output=element.text)

            elif action == "get_html":
                if not selector:
                    return ToolResult(
                        success=False, output="Selector required for 'get_html' action"
                    )
                element = self._find_element(selector)
                return ToolResult(success=True, output=element.get_attribute("innerHTML"))

            elif action == "screenshot":
                driver = self._get_driver()
                if selector:
                    element = self._find_element(selector)
                    return ToolResult(success=True, output=f"Screenshot of {selector}")
                else:
                    driver.save_screenshot("/tmp/browser_screenshot.png")
                    return ToolResult(
                        success=True, output="Screenshot saved to /tmp/browser_screenshot.png"
                    )

            elif action == "back":
                driver = self._get_driver()
                driver.back()
                return ToolResult(success=True, output="Navigated back")

            elif action == "forward":
                driver = self._get_driver()
                driver.forward()
                return ToolResult(success=True, output="Navigated forward")

            elif action == "refresh":
                driver = self._get_driver()
                driver.refresh()
                return ToolResult(success=True, output="Page refreshed")

            elif action == "close":
                if self._driver:
                    self._driver.quit()
                    self._driver = None
                return ToolResult(success=True, output="Browser closed")

            else:
                return ToolResult(success=False, output=f"Unknown action: {action}")

        except Exception as e:
            return ToolResult(success=False, output=f"Browser error: {e!s}", error=str(e))

    def close(self):
        """Close the browser."""
        if self._driver:
            self._driver.quit()
            self._driver = None


class SearchWebTool(ReadOnlyTool):
    """Web search tool using browser."""

    CATEGORY = "browser"

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return "Search the web using Google"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "number", "description": "Number of results (default: 5)"},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, num_results: int = 5) -> ToolResult:
        """Search the web."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )

            # Navigate to Google
            driver.get(f"https://www.google.com/search?q={query}")
            await asyncio.sleep(2)

            results = []
            search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")[:num_results]

            for result in search_results:
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3").text
                    link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    snippet = result.find_element(By.CSS_SELECTOR, "div.IsZvec").text[:200]
                    results.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}\n")
                except Exception:
                    continue

            driver.quit()

            if results:
                return ToolResult(success=True, output="".join(results))
            else:
                return ToolResult(success=True, output="No results found")

        except Exception as e:
            return ToolResult(success=False, output=f"Search error: {e!s}")


class ScrapeWebTool(ReadOnlyTool):
    """Web scraping tool."""

    CATEGORY = "browser"

    @property
    def name(self) -> str:
        return "scrape_web"

    @property
    def description(self) -> str:
        return "Scrape content from a web page"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "selector": {"type": "string", "description": "CSS selector for content"},
            },
            "required": ["url"],
        }

    async def scrape_article(self, url: str) -> dict[str, Any]:
        """Scrape and extract article content from a URL."""
        try:
            response = await asyncio.to_thread(requests.get, url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup(["nav", "aside", "footer", "header", "script", "style", "noscript", "iframe"]):
                tag.decompose()

            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            author = ""
            author_tag = soup.find(attrs={"name": "author"})
            if author_tag:
                author = author_tag.get("content", "").strip()
            if not author:
                author_tag = soup.find(class_="author")
                if author_tag:
                    author = author_tag.get_text(strip=True)

            publish_date = ""
            date_tag = soup.find(attrs={"property": "article:published_time"})
            if date_tag:
                publish_date = date_tag.get("content", "").strip()

            main_content = soup.find("article")
            if not main_content:
                main_content = soup.find(class_="post-content")
            if not main_content:
                main_content = soup.find(class_="entry-content")
            if not main_content:
                main_content = soup.find("main")
            if not main_content:
                main_content = soup.find(id="content")
            if not main_content:
                main_content = soup.body

            text = ""
            if main_content:
                text = main_content.get_text(separator="\n", strip=True)

            return {
                "title": title,
                "author": author,
                "date": publish_date,
                "content": text,
                "url": url,
            }
        except Exception as e:
            return {
                "title": "",
                "author": "",
                "date": "",
                "content": "",
                "url": url,
                "error": str(e),
            }

    async def summarize_webpage(self, url: str) -> str:
        """Summarize webpage content using web scraping."""
        try:
            article = await self.scrape_article(url)
            if article.get("error"):
                return f"Error: {article['error']}"
            text = article.get("content", "")
            if not text:
                return "No content found"
            if len(text) > 500:
                text = text[:500] + "..."
            return text
        except Exception as e:
            return f"Error: {e!s}"

    async def save_webpage(self, url: str, output_path: str) -> str:
        """Fetch full HTML and save to output_path."""
        try:
            response = await asyncio.to_thread(requests.get, url, timeout=30)
            response.raise_for_status()
            path = __import__("pathlib").Path(output_path)
            await asyncio.to_thread(path.write_text, response.text, encoding="utf-8")
            return f"Saved to: {output_path}"
        except Exception as e:
            return f"Error saving webpage: {e!s}"

    async def execute(self, url: str, selector: str = None) -> ToolResult:
        """Scrape web page."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )

            driver.get(url)
            await asyncio.sleep(2)

            if selector:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                content = "\n".join([el.text for el in elements])
            else:
                content = driver.page_source[:5000]

            driver.quit()

            return ToolResult(success=True, output=content)

        except Exception as e:
            return ToolResult(success=False, output=f"Scraping error: {e!s}")


def get_browser_tools() -> list[object]:
    """Get all browser tools. Prefers persistent Playwright tools when available."""
    try:
        from jarvis.browser.manager import get_manager

        get_manager().instance()
        from jarvis.browser.tools import (
            PersistentBrowserTool,
            PersistentScrapeTool,
            PersistentSearchTool,
        )

        return [PersistentBrowserTool(), PersistentSearchTool(), PersistentScrapeTool()]
    except Exception:
        return [BrowserTool(), SearchWebTool(), ScrapeWebTool()]
