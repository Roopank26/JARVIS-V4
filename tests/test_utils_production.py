"""
Tests for JARVIS production utilities.
"""

import asyncio

import pytest

from jarvis.utils.exceptions import (
    ConfigurationError,
    JarvisError,
    ProviderError,
    format_exception,
)
from jarvis.utils.lifecycle import (
    LifecycleComponent,
    LifecycleManager,
    LifecycleState,
)
from jarvis.utils.logging import configure_logging, get_logger


class TestLogging:
    """Test logging utilities."""

    def test_get_logger(self):
        """Test getting a logger."""
        logger = get_logger("test")
        assert logger is not None
        assert "jarvis.test" in logger.name

    def test_configure_logging(self):
        """Test configuring logging."""
        configure_logging(level="DEBUG")
        logger = get_logger("test")
        assert logger.level <= 10  # DEBUG level


class TestExceptions:
    """Test exception classes."""

    def test_jarvis_error(self):
        """Test base JarvisError."""
        error = JarvisError("Test error", recoverable=True)
        assert str(error) == "Test error"
        assert error.recoverable is True

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Invalid config")
        assert isinstance(error, JarvisError)

    def test_provider_error(self):
        """Test ProviderError."""
        error = ProviderError("Provider failed", provider="ollama")
        assert error.provider == "ollama"

    def test_format_exception(self):
        """Test exception formatting."""
        error = JarvisError("Test error")
        assert format_exception(error) == "Test error"

        # Test unknown exception
        assert "Exception:" in format_exception(Exception("Test"))


class _TestableLifecycleComponent(LifecycleComponent):
    """Test lifecycle component (renamed to avoid pytest collection)."""

    def __init__(self, name: str = "test"):
        super().__init__(name)
        self.started = False
        self.stopped = False

    async def _on_start(self):
        self.started = True

    async def _on_stop(self):
        self.stopped = True


class TestLifecycle:
    """Test lifecycle management."""

    @pytest.mark.asyncio
    async def test_component_start_stop(self):
        """Test component start and stop."""
        component = _TestableLifecycleComponent()

        # Start
        assert await component.start()
        assert component.is_running
        assert component.state == LifecycleState.RUNNING
        assert component.started

        # Stop
        assert await component.stop()
        assert not component.is_running
        assert component.state == LifecycleState.STOPPED
        assert component.stopped

    @pytest.mark.asyncio
    async def test_lifecycle_manager(self):
        """Test lifecycle manager."""
        manager = LifecycleManager()
        component = _TestableLifecycleComponent()

        manager.register(component)

        assert await manager.start_all()
        assert component.is_running

        assert await manager.stop_all()
        assert not component.is_running

    @pytest.mark.asyncio
    async def test_component_add_task(self):
        """Test adding tasks to component."""
        component = _TestableLifecycleComponent()

        async def background_task():
            await asyncio.sleep(0.1)

        task = component.add_task(background_task())
        assert task in component._tasks

        await component.start()
        await asyncio.sleep(0.05)
        await component.stop()

        # Task should be cancelled



