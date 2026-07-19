"""
JARVIS Lifecycle Management
Handles startup, shutdown, and resource cleanup for all components.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("jarvis.lifecycle")


class LifecycleState(Enum):
    """Component lifecycle states."""

    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class LifecycleEvent:
    """Lifecycle event data."""

    state: LifecycleState
    component: str
    timestamp: datetime = field(default_factory=datetime.now)
    error: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LifecycleComponent(ABC):
    """
    Abstract base class for lifecycle-managed components.

    All JARVIS components should inherit from this class
    to ensure proper startup/shutdown handling.
    """

    def __init__(self, name: str):
        self.name = name
        self._state = LifecycleState.STOPPED
        self._tasks: set[asyncio.Task] = set()
        self._cleanup_callbacks: list[Callable] = []
        self._error: Exception | None = None

    @property
    def state(self) -> LifecycleState:
        """Current lifecycle state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if component is running."""
        return self._state == LifecycleState.RUNNING

    @property
    def error(self) -> Exception | None:
        """Get any error that occurred."""
        return self._error

    @abstractmethod
    async def _on_start(self) -> None:
        """
        Called when component starts.
        Override to perform initialization.
        """
        pass

    @abstractmethod
    async def _on_stop(self) -> None:
        """
        Called when component stops.
        Override to perform cleanup.
        """
        pass

    async def start(self) -> bool:
        """
        Start the component.

        Returns:
            True if started successfully
        """
        if self._state == LifecycleState.RUNNING:
            logger.warning(f"{self.name}: Already running")
            return True

        if self._state == LifecycleState.STOPPING:
            logger.error(f"{self.name}: Cannot start while stopping")
            return False

        self._state = LifecycleState.INITIALIZING
        self._error = None

        try:
            logger.info(f"{self.name}: Starting...")
            await self._on_start()
            self._state = LifecycleState.RUNNING
            logger.info(f"{self.name}: Started successfully")
            return True

        except Exception as e:
            self._state = LifecycleState.ERROR
            self._error = e
            logger.error(f"{self.name}: Failed to start: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop the component.

        Returns:
            True if stopped successfully
        """
        if self._state == LifecycleState.STOPPED:
            logger.warning(f"{self.name}: Already stopped")
            return True

        if self._state == LifecycleState.STOPPING:
            logger.warning(f"{self.name}: Already stopping")
            return True

        self._state = LifecycleState.STOPPING

        try:
            logger.info(f"{self.name}: Stopping...")

            # Cancel all managed tasks
            await self._cancel_tasks()

            # Run cleanup callbacks
            await self._run_cleanup()

            # Call component stop
            await self._on_stop()

            self._state = LifecycleState.STOPPED
            logger.info(f"{self.name}: Stopped successfully")
            return True

        except Exception as e:
            self._state = LifecycleState.ERROR
            self._error = e
            logger.error(f"{self.name}: Error during stop: {e}")
            return False

    async def restart(self) -> bool:
        """
        Restart the component.

        Returns:
            True if restarted successfully
        """
        logger.info(f"{self.name}: Restarting...")
        await self.stop()
        return await self.start()

    def add_task(self, coro) -> asyncio.Task:
        """
        Add a task to be managed by the lifecycle.

        Args:
            coro: Coroutine to run

        Returns:
            Created task
        """
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def remove_task(self, task: asyncio.Task) -> None:
        """
        Remove a task from management.

        Args:
            task: Task to remove
        """
        self._tasks.discard(task)
        if not task.done():
            task.cancel()

    async def _cancel_tasks(self) -> None:
        """Cancel all managed tasks."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

    def add_cleanup(self, callback: Callable) -> None:
        """
        Add a cleanup callback.

        Args:
            callback: Callable to invoke during cleanup
        """
        self._cleanup_callbacks.append(callback)

    async def _run_cleanup(self) -> None:
        """Run all cleanup callbacks."""
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"{self.name}: Cleanup callback error: {e}")

        self._cleanup_callbacks.clear()


class LifecycleManager:
    """
    Manages multiple lifecycle components.
    """

    def __init__(self):
        self._components: dict[str, LifecycleComponent] = {}
        self._start_order: list[str] = []
        self._stop_order: list[str] = []

    def register(
        self,
        component: LifecycleComponent,
        start_order: int = 0,
    ) -> None:
        """
        Register a component.

        Args:
            component: Component to register
            start_order: Order to start (lower = earlier)
        """
        self._components[component.name] = component

        # Insert in start order
        inserted = False
        for i, name in enumerate(self._start_order):
            if start_order < self._get_order(name):
                self._start_order.insert(i, component.name)
                inserted = True
                break
        if not inserted:
            self._start_order.append(component.name)

        # Insert in stop order (reverse)
        self._stop_order.insert(0, component.name)

    def _get_order(self, name: str) -> int:
        """Get start order for a component."""
        return self._start_order.index(name)

    def unregister(self, name: str) -> None:
        """
        Unregister a component.

        Args:
            name: Component name
        """
        if name in self._components:
            del self._components[name]
            self._start_order.remove(name)
            self._stop_order.remove(name)

    async def start_all(self) -> bool:
        """
        Start all registered components.

        Returns:
            True if all started successfully
        """
        logger.info(f"Starting {len(self._components)} components...")
        success = True

        for name in self._start_order:
            component = self._components.get(name)
            if component and not await component.start():
                logger.error(f"Failed to start {name}")
                success = False
                break

        return success

    async def stop_all(self) -> bool:
        """
        Stop all registered components.

        Returns:
            True if all stopped successfully
        """
        logger.info(f"Stopping {len(self._components)} components...")
        success = True

        for name in self._stop_order:
            component = self._components.get(name)
            if component and not await component.stop():
                logger.error(f"Error stopping {name}")
                success = False

        return success

    async def restart_all(self) -> bool:
        """
        Restart all components.

        Returns:
            True if all restarted successfully
        """
        await self.stop_all()
        return await self.start_all()

    def get_component(self, name: str) -> LifecycleComponent | None:
        """Get a registered component."""
        return self._components.get(name)

    def list_components(self) -> list[dict[str, Any]]:
        """List all registered components."""
        return [
            {
                "name": c.name,
                "state": c.state.value,
                "is_running": c.is_running,
                "has_error": c.error is not None,
            }
            for c in self._components.values()
        ]


@asynccontextmanager
async def lifespan_context(manager: LifecycleManager):
    """
    Async context manager for lifecycle management.

    Usage:
        async with lifespan_context(manager):
            # Components are running
            ...
        # Components are stopped
    """
    try:
        await manager.start_all()
        yield manager
    finally:
        await manager.stop_all()


class StartupDiagnostics:
    """
    Collects and reports startup diagnostics.
    """

    def __init__(self):
        self._checks: dict[str, dict[str, Any]] = {}

    def add_check(
        self,
        name: str,
        status: bool,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a diagnostic check result."""
        self._checks[name] = {
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(),
        }

    def is_passed(self, name: str) -> bool:
        """Check if a diagnostic passed."""
        return self._checks.get(name, {}).get("status", False)

    def get_report(self) -> str:
        """Generate a diagnostic report."""
        lines = ["=" * 60, "STARTUP DIAGNOSTICS", "=" * 60, ""]

        passed = sum(1 for c in self._checks.values() if c["status"])
        total = len(self._checks)

        lines.append(f"Result: {passed}/{total} checks passed\n")

        for name, check in self._checks.items():
            status = "✓" if check["status"] else "✗"
            lines.append(f"{status} {name}: {check['message']}")

            if check["details"]:
                for key, value in check["details"].items():
                    lines.append(f"    {key}: {value}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def is_all_passed(self) -> bool:
        """Check if all diagnostics passed."""
        return all(c["status"] for c in self._checks.values())
