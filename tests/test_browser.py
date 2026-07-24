"""
Tests for the persistent browser manager.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.browser.config import BrowserConfig
from jarvis.browser.manager import PersistentBrowserManager
from jarvis.browser.state import BrowserState


class TestBrowserConfig:
    def test_default_config(self):
        config = BrowserConfig()
        assert config.headless is True
        assert config.browser == "chromium"
        assert config.timeout == 30
        assert config.window_size == (1920, 1080)

    def test_storage_path_defaults_to_jarvis_dir(self):
        config = BrowserConfig()
        assert config.storage_path == Path.home() / ".jarvis" / "browser"


class TestBrowserState:
    def test_state_roundtrip(self, tmp_path: Path):
        state = BrowserState(tmp_path, "test.json")
        state.update(running=True, pid=12345)
        loaded = state.load()
        assert loaded["running"] is True
        assert loaded["pid"] == 12345

    def test_state_clear(self, tmp_path: Path):
        state = BrowserState(tmp_path, "test.json")
        state.update(running=True)
        state.clear()
        assert state.load() == {}

    def test_state_atomic_write(self, tmp_path: Path):
        state = BrowserState(tmp_path, "test.json")
        state.update(running=True)
        assert not (tmp_path / "test.json.tmp").exists()


class TestPersistentBrowserManager:
    @pytest.mark.asyncio
    async def test_singleton(self):
        PersistentBrowserManager.reset()
        m1 = PersistentBrowserManager.instance()
        m2 = PersistentBrowserManager.instance()
        assert m1 is m2
        PersistentBrowserManager.reset()

    @pytest.mark.asyncio
    async def test_start_and_health(self):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        manager.config.headless = True
        manager.config.idle_timeout = 60
        try:
            await manager.start()
            assert manager.is_running is True
            assert await manager.health_check() is True
        finally:
            await manager.shutdown()
            PersistentBrowserManager.reset()

    @pytest.mark.asyncio
    async def test_health_check_when_not_running(self):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        assert await manager.health_check() is False

    @pytest.mark.asyncio
    async def test_navigate_and_get_title(self):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        manager.config.headless = True
        manager.config.idle_timeout = 60
        try:
            await manager.start()
            result = await manager.navigate("https://example.com")
            assert "Navigated to https://example.com" in result
            assert "title" in result.lower() or "Example" in result
        finally:
            await manager.shutdown()
            PersistentBrowserManager.reset()

    @pytest.mark.asyncio
    async def test_screenshot(self, tmp_path: Path):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        manager.config.headless = True
        manager.config.idle_timeout = 60
        manager.config.storage_path = tmp_path / "browser"
        try:
            await manager.start()
            await manager.navigate("https://example.com")
            result = await manager.screenshot(path=str(tmp_path / "shot.png"))
            assert "Screenshot saved" in result
            assert (tmp_path / "shot.png").exists()
        finally:
            await manager.shutdown()
            PersistentBrowserManager.reset()

    @pytest.mark.asyncio
    async def test_new_tab_and_list(self):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        manager.config.headless = True
        manager.config.idle_timeout = 60
        try:
            await manager.start()
            await manager.navigate("https://example.com", tab_id="default")
            new_tab = await manager.new_tab("https://example.org")
            assert "Opened new tab" in new_tab
            tabs = await manager.list_tabs()
            assert len(tabs) >= 2
            await manager.close_tab("tab_1")
            tabs = await manager.list_tabs()
            assert len(tabs) == 1
        finally:
            await manager.shutdown()
            PersistentBrowserManager.reset()

    @pytest.mark.asyncio
    async def test_cookie_persistence_cycle(self, tmp_path: Path):
        PersistentBrowserManager.reset()
        manager = PersistentBrowserManager.instance()
        manager.config.headless = True
        manager.config.idle_timeout = 60
        manager.config.storage_path = tmp_path / "browser"
        try:
            await manager.start()
            await manager.navigate("https://example.com")
            await manager.fill("input[type='search']", "jarvis-test")
            await manager.save_storage_state()
            storage_dir = manager.config.storage_path
            assert (storage_dir / "storage_state.json").exists()
        finally:
            await manager.shutdown()
            PersistentBrowserManager.reset()
