"""
System Self-Diagnostics for JARVIS.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.runtime.manager import get_runtime_manager

logger = logging.getLogger(__name__)


@dataclass
class HealthReport:
    overall_status: str = "unknown"
    subsystems: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class SystemSelfDiagnostics:
    def __init__(self) -> None:
        self._reports: list[HealthReport] = []
        self._max_reports = 50
        self._running = False
        self._task: asyncio.Task | None = None
        self._interrupt = asyncio.Event()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._interrupt.clear()
        self._task = asyncio.create_task(self._monitor_loop())

    def stop(self) -> None:
        self._running = False
        self._interrupt.set()
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def shutdown(self) -> None:
        self.stop()

    async def run_diagnostics(self) -> HealthReport:
        report = HealthReport()
        runtime = get_runtime_manager()
        report.subsystems = await runtime.health_check()
        report.warnings = self._warnings_from_report(report.subsystems)
        report.errors = self._errors_from_report(report.subsystems)
        report.overall_status = "ok" if not report.errors else "degraded" if report.warnings else "critical"
        self._reports.append(report)
        if len(self._reports) > self._max_reports:
            self._reports = self._reports[-self._max_reports:]
        return report

    def get_recent(self, limit: int = 10) -> list[HealthReport]:
        return list(self._reports)[-limit:]

    async def _monitor_loop(self) -> None:
        while self._running and not self._interrupt.is_set():
            try:
                await asyncio.sleep(60)
                if not self._running:
                    break
                report = await self.run_diagnostics()
                if report.errors:
                    logger.warning("System diagnostics: %d errors detected", len(report.errors))
                    await self._attempt_recovery(report)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Diagnostics monitor error: %s", exc)

    async def _attempt_recovery(self, report: HealthReport) -> None:
        runtime = get_runtime_manager()
        for name in report.errors:
            clean_name = name.split(":")[0]
            record = runtime.get_subsystem(clean_name)
            if record and record.restart_count < 3:
                await runtime.restart(clean_name)

    def _warnings_from_report(self, subsystems: dict[str, Any]) -> list[str]:
        warnings = []
        for name, status in subsystems.items():
            if not status.get("healthy", True):
                warnings.append(f"{name}: degraded")
        return warnings

    def _errors_from_report(self, subsystems: dict[str, Any]) -> list[str]:
        errors = []
        for name, status in subsystems.items():
            if not status.get("healthy", True) and status.get("error"):
                errors.append(f"{name}: {status.get('error')}")
        return errors

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self._running,
            "reports": len(self._reports),
            "status": "monitoring" if self._running else "stopped",
        }
