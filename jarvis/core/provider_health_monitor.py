"""
JARVIS Provider Health Monitor
===============================
Independent background service that continuously monitors the health,
latency, availability, failures, and recovery of all AI providers.

Responsibilities:
- Background health checks (periodic async loop)
- Track latency (ms), availability, failures, recovery, cooldowns, statistics
- Emit EventType.PROVIDER_AVAILABLE / EventType.PROVIDER_UNAVAILABLE on EventBus
- Expose get_healthy_providers() for ProviderManager
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from jarvis.events import EventType, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Detailed health record for a single provider."""

    name: str
    available: bool = True
    latency_ms: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_check_ts: float = 0.0
    cooldown_until_ts: float = 0.0
    last_error: str | None = None

    @property
    def is_healthy(self) -> bool:
        now = time.time()
        if not self.available:
            return False
        return not now < self.cooldown_until_ts


class ProviderHealthMonitor:
    """
    Background service for tracking provider health metrics and availability.
    """

    def __init__(self, check_interval: float = 30.0) -> None:
        self.check_interval = check_interval
        self._health: dict[str, ProviderHealth] = {}
        self._bus = get_event_bus()
        self._task: asyncio.Task | None = None
        self._running = False

    def record_success(self, provider_name: str, latency_ms: float = 0.0) -> None:
        rec = self._health.setdefault(provider_name, ProviderHealth(name=provider_name))
        rec.available = True
        rec.success_count += 1
        rec.latency_ms = latency_ms
        rec.failure_count = max(0, rec.failure_count - 1)
        rec.last_check_ts = time.time()

    def record_failure(self, provider_name: str, error: str, cooldown_seconds: float = 60.0) -> None:
        rec = self._health.setdefault(provider_name, ProviderHealth(name=provider_name))
        rec.failure_count += 1
        rec.last_error = error
        rec.last_check_ts = time.time()
        if rec.failure_count >= 3:
            rec.available = False
            rec.cooldown_until_ts = time.time() + cooldown_seconds
            logger.warning("[ProviderHealthMonitor] Provider %s cooling down for %.1fs: %s", provider_name, cooldown_seconds, error)
            self._bus.emit(EventType.PROVIDER_UNAVAILABLE, {"provider": provider_name, "error": error})

    def is_healthy(self, provider_name: str) -> bool:
        rec = self._health.get(provider_name)
        if rec is None:
            return True
        return rec.is_healthy

    def get_healthy_providers(self) -> list[str]:
        return [name for name, h in self._health.items() if h.is_healthy]

    def get_status(self) -> dict[str, Any]:
        return {
            name: {
                "available": h.available,
                "healthy": h.is_healthy,
                "latency_ms": round(h.latency_ms, 2),
                "success_count": h.success_count,
                "failure_count": h.failure_count,
                "last_error": h.last_error,
            }
            for name, h in self._health.items()
        }

    def record_latency(self, provider_name: str, model: str, ms: float) -> None:
        """Record a latency sample for a specific provider and model."""
        rec = self._health.setdefault(provider_name, ProviderHealth(name=provider_name))
        rec.latency_ms = ms
        rec.last_check_ts = time.time()
        logger.debug("[ProviderHealthMonitor] Latency recorded: provider=%s model=%s ms=%.2f", provider_name, model, ms)

    def get_latency_stats(self, provider_name: str | None = None) -> dict[str, Any]:
        """Return latency statistics, optionally filtered by provider."""
        if provider_name is not None:
            rec = self._health.get(provider_name)
            if rec is None:
                return {"provider": provider_name, "latency_ms": 0.0, "samples": 0}
            return {
                "provider": provider_name,
                "latency_ms": round(rec.latency_ms, 2),
                "samples": 1,
            }

        result: dict[str, Any] = {}
        for name, rec in self._health.items():
            result[name] = {
                "latency_ms": round(rec.latency_ms, 2),
                "samples": 1,
            }
        return result

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("[ProviderHealthMonitor] Background monitor started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with asyncio.suppress(asyncio.CancelledError):
                await self._task

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                # Periodic recovery check for cooling-down providers
                now = time.time()
                for name, h in self._health.items():
                    if not h.available and now >= h.cooldown_until_ts and h.cooldown_until_ts > 0:
                        h.available = True
                        h.failure_count = 0
                        h.cooldown_until_ts = 0.0
                        logger.info("[ProviderHealthMonitor] Provider %s recovered", name)
                        self._bus.emit(EventType.PROVIDER_AVAILABLE, {"provider": name})
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("[ProviderHealthMonitor] Loop error: %s", e)


_health_monitor: ProviderHealthMonitor | None = None


def get_provider_health_monitor() -> ProviderHealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ProviderHealthMonitor()
    return _health_monitor
