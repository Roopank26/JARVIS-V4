"""
JARVIS Observability & Metrics System
=====================================
Single responsibility: Track, compute, and expose system operational metrics
for real-time diagnostics and enterprise dashboards.

Tracked metrics:
- Planner latency (ms)
- Capability match latency (ms)
- Provider latency (ms)
- Execution latency (ms)
- Success / failure counts & rates
- Tool usage frequency
- Provider usage frequency
- Streaming duration (s)
- Cancellation count & rate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    total_calls: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    tool_counts: dict[str, int] = field(default_factory=dict)
    provider_counts: dict[str, int] = field(default_factory=dict)
    cancellations: int = 0
    streaming_duration_s: float = 0.0


class ObservabilityManager:
    """
    Central operational metrics collector.
    """

    def __init__(self) -> None:
        self._record = MetricRecord()

    def record_planner(self, latency_ms: float) -> None:
        logger.debug("[Observability] Planner latency: %.2fms", latency_ms)

    def record_capability_match(self, capability_name: str, latency_ms: float) -> None:
        logger.debug("[Observability] Router match latency (%s): %.2fms", capability_name, latency_ms)

    def record_execution(
        self, tool_name: str, latency_ms: float, success: bool, provider: str = ""
    ) -> None:
        rec = self._record
        rec.total_calls += 1
        if not success:
            rec.total_errors += 1
        rec.total_latency_ms += latency_ms
        rec.tool_counts[tool_name] = rec.tool_counts.get(tool_name, 0) + 1
        if provider:
            rec.provider_counts[provider] = rec.provider_counts.get(provider, 0) + 1

    def record_cancellation(self) -> None:
        self._record.cancellations += 1

    def record_streaming(self, duration_s: float) -> None:
        self._record.streaming_duration_s += duration_s

    def get_metrics_summary(self) -> dict[str, Any]:
        rec = self._record
        avg_latency = (
            round(rec.total_latency_ms / rec.total_calls, 2)
            if rec.total_calls > 0
            else 0.0
        )
        success_rate = (
            round(((rec.total_calls - rec.total_errors) / rec.total_calls) * 100, 1)
            if rec.total_calls > 0
            else 100.0
        )
        return {
            "total_requests": rec.total_calls,
            "total_errors": rec.total_errors,
            "success_rate_percent": success_rate,
            "avg_execution_latency_ms": avg_latency,
            "tool_usage_frequency": dict(rec.tool_counts),
            "provider_usage_frequency": dict(rec.provider_counts),
            "total_cancellations": rec.cancellations,
            "total_streaming_duration_seconds": round(rec.streaming_duration_s, 2),
        }


_observability: ObservabilityManager | None = None


def get_observability() -> ObservabilityManager:
    global _observability
    if _observability is None:
        _observability = ObservabilityManager()
    return _observability
