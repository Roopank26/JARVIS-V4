"""Browser tools for JARVIS backed by the persistent Playwright manager."""

from __future__ import annotations

import logging
from typing import Any

from jarvis.browser.config import BrowserConfig
from jarvis.browser.manager import PersistentBrowserManager, get_manager
from jarvis.tools.base import ReadOnlyTool, ToolResult

logger = logging.getLogger(__name__)


class PersistentBrowserTool(ReadOnlyTool):
    """Persistent browser tool using Playwright daemon."""

    CATEGORY = "browser"
    name = "browser"
    description = "Persistent web browser - navigate, click, fill, extract"

    def __init__(self, config: BrowserConfig | None = None):
        self.config = config or BrowserConfig()
        self._manager = get_manager()

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
                        "new_tab",
                        "close_tab",
                        "list_tabs",
                        "snapshot",
                    ],
                    "description": "Browser action to perform",
                },
                "url": {"type": "string", "description": "URL for navigate/open actions"},
                "selector": {"type": "string", "description": "CSS selector for element"},
                "value": {"type": "string", "description": "Value for fill/submit actions"},
                "tab_id": {"type": "string", "description": "Tab identifier (default: default)"},
                "timeout": {"type": "number", "description": "Action timeout in seconds"},
                "full_page": {"type": "boolean", "description": "Capture full page screenshot"},
            },
            "required": ["action"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        action = input_data.get("action", "")
        url = input_data.get("url")
        selector = input_data.get("selector")
        value = input_data.get("value")
        tab_id = input_data.get("tab_id", "default")
        timeout = input_data.get("timeout")
        full_page = input_data.get("full_page", False)

        if timeout:
            self.config.timeout = timeout

        manager = self._manager
        try:
            if action == "open":
                if not url:
                    return ToolResult(success=False, output="URL required for 'open' action")
                result = await manager.new_tab(url)
                return ToolResult(success=True, output=result)

            elif action == "navigate":
                if not url:
                    return ToolResult(success=False, output="URL required for 'navigate' action")
                result = await manager.navigate(url, tab_id=tab_id)
                return ToolResult(success=not result.startswith("Navigation failed"), output=result)

            elif action == "click":
                if not selector:
                    return ToolResult(success=False, output="Selector required for 'click' action")
                result = await manager.click(selector, tab_id=tab_id)
                return ToolResult(success=not result.startswith("Click failed"), output=result)

            elif action == "fill":
                if not selector or value is None:
                    return ToolResult(
                        success=False, output="Selector and value required for 'fill' action"
                    )
                result = await manager.fill(selector, value, tab_id=tab_id)
                return ToolResult(success=not result.startswith("Fill failed"), output=result)

            elif action == "submit":
                if not selector:
                    return ToolResult(success=False, output="Selector required for 'submit' action")
                result = await manager.click(selector, tab_id=tab_id)
                return ToolResult(success=not result.startswith("Click failed"), output=result)

            elif action == "get_text":
                if not selector:
                    return ToolResult(
                        success=False, output="Selector required for 'get_text' action"
                    )
                result = await manager.get_text(selector, tab_id=tab_id)
                return ToolResult(
                    success=not result.startswith("Text extraction failed"), output=result
                )

            elif action == "get_html":
                if not selector:
                    msg = "Selector required for 'get_html' action"
                    return ToolResult(success=False, output=msg)
                result = await manager.get_html(selector, tab_id=tab_id)
                return ToolResult(
                    success=not result.startswith("HTML extraction failed"), output=result
                )

            elif action == "screenshot":
                result = await manager.screenshot(tab_id=tab_id, full_page=full_page)
                return ToolResult(success=not result.startswith("Screenshot failed"), output=result)

            elif action == "back":
                result = await manager.back(tab_id=tab_id)
                return ToolResult(success=not result.startswith("Back failed"), output=result)

            elif action == "forward":
                result = await manager.forward(tab_id=tab_id)
                return ToolResult(success=not result.startswith("Forward failed"), output=result)

            elif action == "refresh":
                result = await manager.refresh(tab_id=tab_id)
                return ToolResult(success=not result.startswith("Refresh failed"), output=result)

            elif action == "close":
                await manager.shutdown()
                PersistentBrowserManager.reset()
                return ToolResult(success=True, output="Browser closed")

            elif action == "new_tab":
                result = await manager.new_tab(url)
                return ToolResult(success=not result.startswith("Opened new tab"), output=result)

            elif action == "close_tab":
                result = await manager.close_tab(tab_id)
                return ToolResult(success=True, output=result)

            elif action == "list_tabs":
                tabs = await manager.list_tabs()
                return ToolResult(success=True, output=str(tabs))

            elif action == "snapshot":
                result = await manager.snapshot(tab_id=tab_id)
                return ToolResult(success=not result.startswith("Snapshot failed"), output=result)

            else:
                return ToolResult(success=False, output=f"Unknown action: {action}")

        except Exception as exc:
            logger.error("Persistent browser action failed: %s", exc, exc_info=True)
            return ToolResult(success=False, output=f"Browser error: {exc}", error=str(exc))


class PersistentSearchTool(ReadOnlyTool):
    """Web search using the persistent browser."""

    CATEGORY = "browser"
    name = "search_web"
    description = "Search the web using persistent browser"

    def __init__(self, config: BrowserConfig | None = None):
        self.config = config or BrowserConfig()
        self._manager = get_manager()

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        query = input_data.get("query", "")
        if not query:
            return ToolResult(success=False, output="Query required")
        manager = self._manager
        url = f"https://www.google.com/search?q={query}"
        result = await manager.navigate(url)
        if result.startswith("Navigation failed"):
            return ToolResult(success=False, output=result)
        content = await manager.get_html("div.g")
        if content.startswith("HTML extraction failed"):
            return ToolResult(success=False, output=content)
        return ToolResult(success=True, output=content[:5000])


class PersistentScrapeTool(ReadOnlyTool):
    """Web scraping using the persistent browser."""

    CATEGORY = "browser"
    name = "scrape_web"
    description = "Scrape content from a web page"

    def __init__(self, config: BrowserConfig | None = None):
        self.config = config or BrowserConfig()
        self._manager = get_manager()

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

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        url = input_data.get("url", "")
        selector = input_data.get("selector")
        if not url:
            return ToolResult(success=False, output="URL required")
        manager = self._manager
        result = await manager.navigate(url)
        if result.startswith("Navigation failed"):
            return ToolResult(success=False, output=result)
        if selector:
            content = await manager.get_html(selector)
        else:
            content = await manager.get_html("body")
        if content.startswith("HTML extraction failed"):
            return ToolResult(success=False, output=content)
        return ToolResult(success=True, output=content[:5000])


def get_browser_tools(
    use_persistent: bool = True,
) -> list[PersistentBrowserTool | object]:
    """Get browser tools. Returns persistent tools when Playwright is available."""
    if not use_persistent:
        from jarvis.tools.browser_tools import get_browser_tools as _legacy  # noqa: F401

        return _legacy()
    try:
        from jarvis.browser.manager import PersistentBrowserManager

        PersistentBrowserManager.instance()
    except Exception:
        from jarvis.tools.browser_tools import get_browser_tools as _legacy

        return _legacy()
    return [
        PersistentBrowserTool(),
        PersistentSearchTool(),
        PersistentScrapeTool(),
    ]
