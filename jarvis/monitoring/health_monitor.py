"""
JARVIS Phase 1 — Unified Health Monitor.

Monitors all registered services, provides auto-recovery on failure,
detects memory leaks, and exposes structured health reports.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import tracemalloc
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceRecord:
    name: str
    healthy: bool = True
    restart_count: int = 0
    max_restarts: int = 3
    last_error: str | None = None
    last_check: float = field(default_factory=time.time)
    started_at: float = field(default_factory=time.time)
    memory_baseline: int = 0
    memory_current: int = 0
    memory_peak: int = 0
    memory_threshold_bytes: int = 0
    pauseable: bool = False
    is_paused: bool = False


@dataclass
class HealthReport:
    overall: str = "ok"
    services: dict[str, ServiceRecord] = field(default_factory=dict)
    memory_leaks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    high_load: bool = False
    load_signals: list[str] = field(default_factory=list)


class HealthMonitor:
    def __init__(self) -> None:
        self._services: dict[str, ServiceRecord] = {}
        self._starters: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self._stoppers: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self._pausers: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self._resumers: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._interrupt = asyncio.Event()
        self._reports: list[HealthReport] = []
        self._max_reports = 100
        self._tracemalloc_started = False
        self._resource_monitor: Any = None

    def register(
        self,
        name: str,
        starter: Callable[[], Coroutine[Any, Any, None]],
        stopper: Callable[[], Coroutine[Any, Any, None]] | None = None,
        *,
        memory_threshold_bytes: int = 0,
        pauseable: bool = False,
    ) -> None:
        rec = ServiceRecord(name=name, memory_threshold_bytes=memory_threshold_bytes, pauseable=pauseable)
        self._services[name] = rec
        self._starters[name] = starter
        if stopper:
            self._stoppers[name] = stopper

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._interrupt.clear()
        if not self._tracemalloc_started:
            tracemalloc.start()
            self._tracemalloc_started = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor started")

    async def stop(self) -> None:
        self._running = False
        self._interrupt.set()
        if self._task is not None:
            self._task.cancel()
            self._task = None
        logger.info("HealthMonitor stopped")

    async def _monitor_loop(self) -> None:
        while self._running and not self._interrupt.is_set():
            try:
                await asyncio.sleep(30)
                if not self._running:
                    break
                report = await self.run_checks()
                self._sample_resource_snapshot(report)
                self._reports.append(report)
                if len(self._reports) > self._max_reports:
                    self._reports = self._reports[-self._max_reports:]
                await self._attempt_recovery(report)
                self._adjust_load(report)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("HealthMonitor loop error: %s", exc)

    def _sample_resource_snapshot(self, report: HealthReport) -> None:
        try:
            if self._resource_monitor is None:
                try:
                    from jarvis.evolution.system_resource_monitor import (
                        ResourceSnapshot,
                        get_resource_monitor,
                    )
                    self._resource_monitor = get_resource_monitor()
                except Exception:
                    self._resource_monitor = None
            if self._resource_monitor is not None:
                try:
                    snap = self._resource_monitor.get_latest()
                    if snap is None:
                        snap = ResourceSnapshot()
                    report.high_load = snap.high_intensity
                    report.load_signals = snap.intensity_signals
                    if snap.high_intensity:
                        report.overall = "warning"
                        report.warnings.extend(snap.intensity_signals)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("Resource snapshot sampling failed: %s", exc)

    async def _adjust_load(self, report: HealthReport) -> None:
        if self._resource_monitor is None:
            return
        try:
            snap = self._resource_monitor.get_latest()
            if snap is None:
                return
            for name, rec in self._services.items():
                if rec.pauseable and not rec.is_paused:
                    if snap.high_intensity:
                        try:
                            stopper = self._stoppers.get(name)
                            if stopper:
                                await stopper()
                            rec.is_paused = True
                            logger.info("Paused high-load service: %s", name)
                        except Exception as exc:
                            logger.debug("Failed to pause %s: %s", name, exc)
                elif rec.pauseable and rec.is_paused and self._resource_monitor.can_resume(snap) and rec.healthy:
                        try:
                            starter = self._starters.get(name)
                            if starter:
                                await starter()
                            rec.is_paused = False
                            rec.restart_count = 0
                            logger.info("Resumed service: %s", name)
                        except Exception as exc:
                            logger.debug("Failed to resume %s: %s", name, exc)
        except Exception as exc:
            logger.debug("Load adjustment failed: %s", exc)

    async def run_checks(self) -> HealthReport:
        report = HealthReport()
        for name, starter in self._starters.items():
            rec = self._services.setdefault(name, ServiceRecord(name=name))
            try:
                await asyncio.wait_for(starter(), timeout=10)
                rec.healthy = True
                rec.last_error = None
                rec.last_check = time.time()
                current, _ = tracemalloc.get_traced_memory() if self._tracemalloc_started else (0, 0)
                if rec.memory_baseline == 0 and current > 0:
                    rec.memory_baseline = current
            except Exception as exc:
                rec.healthy = False
                rec.last_error = str(exc)
                rec.last_check = time.time()
                report.warnings.append(f"{name}: {exc}")
            report.services[name] = rec

        report.overall = "ok" if not report.warnings else "degraded"
        report.memory_leaks = self._detect_leaks()
        if report.memory_leaks:
            report.overall = "warning"
        return report

    async def _attempt_recovery(self, report: HealthReport) -> None:
        for name, rec in report.services.items():
            if not rec.healthy and rec.restart_count < rec.max_restarts:
                stopper = self._stoppers.get(name)
                if stopper:
                    with contextlib.suppress(Exception):
                        await stopper()
                try:
                    await self._starters[name]()
                    rec.restart_count += 1
                    rec.healthy = True
                    rec.last_error = None
                    logger.info("Auto-recovered service: %s (attempt %d)", name, rec.restart_count)
                except Exception as exc:
                    rec.last_error = str(exc)
                    logger.warning("Auto-recovery failed for %s: %s", name, exc)

    def _detect_leaks(self) -> list[str]:
        leaks: list[str] = []
        try:
            if not self._tracemalloc_started:
                return leaks
            current, peak = tracemalloc.get_traced_memory()
            for name, rec in self._services.items():
                if rec.memory_baseline > 0 and current > rec.memory_baseline * 3:
                    leaks.append(f"{name}: memory grew from {rec.memory_baseline} to {current}")
                if rec.memory_threshold_bytes > 0 and current > rec.memory_threshold_bytes:
                    leaks.append(f"{name}: process memory {current} exceeded threshold {rec.memory_threshold_bytes}")
                rec.memory_current = current
                rec.memory_peak = peak
        except Exception as exc:
            logger.debug("Memory leak detection failed: %s", exc)
        return leaks

    def get_report(self, limit: int = 20) -> list[HealthReport]:
        return list(self._reports)[-limit:]

    def get_service_status(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "healthy": rec.healthy,
                "restart_count": rec.restart_count,
                "last_error": rec.last_error,
                "last_check": rec.last_check,
            }
            for name, rec in self._services.items()
        }


_instance: HealthMonitor | None = None


def get_health_monitor() -> HealthMonitor:
    global _instance
    if _instance is None:
        _instance = HealthMonitor()
    return _instance


def reset_health_monitor() -> None:
    global _instance
    _instance = None
