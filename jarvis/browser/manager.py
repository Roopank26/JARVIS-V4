"""Persistent browser manager for JARVIS.

Adapts the daemon-model concepts from GStack to a Python/Playwright
runtime. The browser is long-lived: cookies, localStorage, and
multiple tabs survive across tool calls. Health monitoring and
auto-reconnect are built in.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from jarvis.browser.config import BrowserConfig
from jarvis.browser.state import BrowserState

logger = logging.getLogger(__name__)


class PersistentBrowserManager:
    """Long-lived Chromium browser manager backed by Playwright."""

    _instance: PersistentBrowserManager | None = None

    def __init__(self, config: BrowserConfig | None = None):
        if PersistentBrowserManager._instance is not None:
            raise RuntimeError("Use PersistentBrowserManager.instance() or get_manager().")
        self.config = config or BrowserConfig()
        self.state = BrowserState(
            storage_path=self.config.storage_path,
            state_file=self.config.state_file,
        )
        self._playwright = None
        self._browser = None
        self._context = None
        self._default_page = None
        self._tabs: dict[str, Any] = {}
        self._running = False
        self._last_health_ok = False
        self._shutdown = asyncio.Event()

    @classmethod
    def instance(cls) -> PersistentBrowserManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        if cls._instance is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(cls._instance.shutdown())
            except RuntimeError:
                pass
            cls._instance = None

    async def start(self) -> None:
        if self._running and self._browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required for the persistent browser. "
                "Install it with: pip install playwright"
            ) from exc

        self.state.clear()
        pw = await async_playwright().start()
        self._playwright = pw
        self._browser = await pw.chromium.launch(
            headless=self.config.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self.config.window_size[0],
                "height": self.config.window_size[1],
            },
            "locale": "en-US",
            "java_script_enabled": True,
        }
        if self.config.user_data_dir:
            context_kwargs["user_data_dir"] = str(self.config.user_data_dir)
        else:
            storage_path = self.config.storage_path / "storage_state.json"
            if storage_path.exists():
                context_kwargs["storage_state"] = str(storage_path)

        self._context = await self._browser.new_context(**context_kwargs)
        self._default_page = await self._context.new_page()
        self._tabs["default"] = self._default_page
        self._running = True
        self.state.update(running=True, browser=self.config.browser, headless=self.config.headless)
        logger.info("Persistent browser started")

    async def ensure_started(self) -> None:
        if not self._running:
            await self.start()
            return
        if not await self.health_check():
            logger.warning("Browser health check failed, restarting")
            await self.shutdown()
            await self.start()

    async def health_check(self) -> bool:
        if not self._running or self._browser is None:
            return False
        try:
            if self._context is None or self._context.browser is None:
                return False
            await asyncio.wait_for(self._context.pages[0].evaluate("1+1"), timeout=5)
            self._last_health_ok = True
            return True
        except Exception as exc:
            logger.debug("Health check failed: %s", exc)
            self._last_health_ok = False
            return False

    async def navigate(self, url: str, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout * 1000)
        except Exception as exc:
            return f"Navigation failed: {exc}"
        title = await page.title()
        return f"Navigated to {url} (title: {title})"

    async def click(self, selector: str, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.click(selector, timeout=self.config.timeout * 1000)
            return f"Clicked: {selector}"
        except Exception as exc:
            return f"Click failed: {exc}"

    async def fill(self, selector: str, value: str, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.fill(selector, value, timeout=self.config.timeout * 1000)
            return f"Filled '{value}' in: {selector}"
        except Exception as exc:
            return f"Fill failed: {exc}"

    async def get_text(self, selector: str, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            text = await page.text_content(selector, timeout=self.config.timeout * 1000)
            return text or ""
        except Exception as exc:
            return f"Text extraction failed: {exc}"

    async def get_html(self, selector: str, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            html = await page.inner_html(selector, timeout=self.config.timeout * 1000)
            return html
        except Exception as exc:
            return f"HTML extraction failed: {exc}"

    async def screenshot(
        self, path: str | None = None, tab_id: str = "default", full_page: bool = False
    ) -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        dest = path or str(self.config.storage_path / "screenshot.png")
        try:
            await page.screenshot(path=dest, full_page=full_page)
            return f"Screenshot saved to {dest}"
        except Exception as exc:
            return f"Screenshot failed: {exc}"

    async def back(self, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.go_back(timeout=self.config.timeout * 1000)
            return "Navigated back"
        except Exception as exc:
            return f"Back failed: {exc}"

    async def forward(self, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.go_forward(timeout=self.config.timeout * 1000)
            return "Navigated forward"
        except Exception as exc:
            return f"Forward failed: {exc}"

    async def refresh(self, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            await page.reload(wait_until="domcontentloaded", timeout=self.config.timeout * 1000)
            return "Page refreshed"
        except Exception as exc:
            return f"Refresh failed: {exc}"

    async def new_tab(self, url: str | None = None) -> str:
        await self.ensure_started()
        if self._context is None:
            return "Browser not available"
        page = await self._context.new_page()
        tab_id = f"tab_{len(self._tabs)}"
        self._tabs[tab_id] = page
        self.state.update(tab_count=len(self._tabs))
        if url:
            await self.navigate(url, tab_id=tab_id)
        return f"Opened new tab: {tab_id}"

    async def close_tab(self, tab_id: str) -> str:
        page = self._tabs.pop(tab_id, None)
        if page is None:
            return f"Tab {tab_id} not found"
        try:
            await page.close()
        except Exception as exc:
            logger.debug("Tab close error: %s", exc)
        self.state.update(tab_count=len(self._tabs))
        return f"Closed tab: {tab_id}"

    async def list_tabs(self) -> list[dict[str, Any]]:
        await self.ensure_started()
        tabs = []
        for tid, page in self._tabs.items():
            try:
                url = page.url
                title = await page.title()
            except Exception:
                url = ""
                title = ""
            tabs.append({"tab_id": tid, "url": url, "title": title})
        return tabs

    async def snapshot(self, tab_id: str = "default") -> str:
        await self.ensure_started()
        page = await self._get_page(tab_id)
        try:
            snapshot = await page.accessibility.snapshot()
            return str(snapshot)
        except Exception as exc:
            return f"Snapshot failed: {exc}"

    async def save_storage_state(self) -> None:
        if self._context is None:
            return
        path = self.config.storage_path / "storage_state.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            await self._context.storage_state(path=str(path))
        except Exception as exc:
            logger.debug("Storage state save failed: %s", exc)

    async def shutdown(self) -> None:
        self._shutdown.set()
        with suppress(Exception):
            await self.save_storage_state()
        if self._default_page and not self._default_page.is_closed():
            with suppress(Exception):
                await self._default_page.close()
        for tab in list(self._tabs.values()):
            with suppress(Exception):
                await tab.close()
        self._tabs.clear()
        if self._context:
            with suppress(Exception):
                await self._context.close()
            self._context = None
        if self._browser:
            with suppress(Exception):
                await self._browser.close()
            self._browser = None
        if self._playwright:
            with suppress(Exception):
                await self._playwright.stop()
            self._playwright = None
        self._running = False
        self.state.clear()
        logger.info("Persistent browser shut down")

    async def _get_page(self, tab_id: str) -> Any:
        if tab_id not in self._tabs:
            raise ValueError(f"Unknown tab: {tab_id}")
        return self._tabs[tab_id]

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def tab_count(self) -> int:
        return len(self._tabs)


def get_manager() -> PersistentBrowserManager:
    return PersistentBrowserManager.instance()
