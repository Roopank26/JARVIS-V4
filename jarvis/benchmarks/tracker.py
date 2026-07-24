"""
JARVIS Phase 5 — Benchmark Tracker.

Tracks monthly improvements for:
- Reasoning quality
- Planning quality
- Coding quality
- Research quality
- Automation success
- Memory retrieval
- Voice latency
- Vision latency
- Repository understanding
- Knowledge growth

Builds on evolution.benchmark.BenchmarkEngine and adds time-series trend tracking.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.evolution.benchmark import BenchmarkEngine, BenchmarkResult

logger = logging.getLogger(__name__)


@dataclass
class MonthlyBenchmark:
    month: str
    metrics: dict[str, float] = field(default_factory=dict)
    samples: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "metrics": {k: round(v, 3) for k, v in self.metrics.items()},
            "samples": self.samples,
            "timestamp": self.timestamp,
        }


class BenchmarkTracker:
    """
    Stores monthly benchmark snapshots and computes trend deltas.

    Does NOT replace BenchmarkEngine. Uses it for weighted scoring and stores
    time-series data separately for trend analysis.
    """

    METRIC_NAMES = [
        "reasoning_quality",
        "planning_quality",
        "coding_quality",
        "research_quality",
        "automation_success",
        "memory_retrieval",
        "voice_latency",
        "vision_latency",
        "repository_understanding",
        "knowledge_growth",
    ]

    def __init__(self, storage_path: Path | None = None) -> None:
        self._engine = BenchmarkEngine()
        self._storage_path = storage_path or Path.home() / ".jarvis" / "benchmarks" / "monthly.json"
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._monthly: dict[str, MonthlyBenchmark] = {}
        self._load()

    def record_monthly_scores(self, scores: dict[str, float], samples: int = 1) -> None:
        month_key = datetime.now().strftime("%Y-%m")
        if month_key not in self._monthly:
            self._monthly[month_key] = MonthlyBenchmark(month=month_key)
        mb = self._monthly[month_key]
        for metric, value in scores.items():
            if metric in self.METRIC_NAMES:
                mb.metrics[metric] = (mb.metrics.get(metric, 0.0) * mb.samples + value) / (mb.samples + samples)
        mb.samples += samples
        mb.timestamp = time.time()
        self._persist()

    def record_benchmark_result(self, result: BenchmarkResult) -> None:
        self._engine.history.append(result)

    def get_monthly(self, month: str | None = None) -> dict[str, Any]:
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        mb = self._monthly.get(month)
        if mb is None:
            return {"status": "no_data", "month": month}
        return mb.to_dict()

    def get_trend(self, metric: str, months: int = 6) -> list[dict[str, Any]]:
        trend: list[dict[str, Any]] = []
        sorted_months = sorted(self._monthly.keys())
        for m in sorted_months[-months:]:
            mb = self._monthly[m]
            if metric in mb.metrics:
                trend.append({"month": m, "value": round(mb.metrics[metric], 3), "samples": mb.samples})
        return trend

    def get_all_trends(self, months: int = 6) -> dict[str, list[dict[str, Any]]]:
        return {metric: self.get_trend(metric, months) for metric in self.METRIC_NAMES}

    def get_deltas(self, months: int = 2) -> dict[str, float]:
        sorted_months = sorted(self._monthly.keys())
        if len(sorted_months) < 2:
            return {}
        current = self._monthly[sorted_months[-1]]
        previous = self._monthly[sorted_months[-2]]
        deltas: dict[str, float] = {}
        for metric in self.METRIC_NAMES:
            curr_val = current.metrics.get(metric, 0.0)
            prev_val = previous.metrics.get(metric, 0.0)
            deltas[metric] = round(curr_val - prev_val, 3) if prev_val > 0 else 0.0
        return deltas

    def get_summary(self) -> dict[str, Any]:
        if not self._monthly:
            return {"status": "no_data"}
        latest_month = max(self._monthly.keys())
        latest = self._monthly[latest_month]
        deltas = self.get_deltas()
        improving = [m for m, d in deltas.items() if d > 0.01]
        declining = [m for m, d in deltas.items() if d < -0.01]
        return {
            "latest_month": latest_month,
            "metrics": {k: round(v, 3) for k, v in latest.metrics.items()},
            "samples": latest.samples,
            "improving_metrics": improving,
            "declining_metrics": declining,
            "stable_metrics": [m for m in self.METRIC_NAMES if m not in improving and m not in declining],
        }

    def _persist(self) -> None:
        try:
            data = {month: mb.to_dict() for month, mb in self._monthly.items()}
            self._storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.debug("Benchmark persistence failed: %s", exc)

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            for month, mb_data in data.items():
                mb = MonthlyBenchmark(
                    month=mb_data.get("month", month),
                    metrics=mb_data.get("metrics", {}),
                    samples=mb_data.get("samples", 0),
                    timestamp=mb_data.get("timestamp", time.time()),
                )
                self._monthly[month] = mb
        except Exception as exc:
            logger.debug("Benchmark load failed: %s", exc)


_tracker: BenchmarkTracker | None = None


def get_benchmark_tracker() -> BenchmarkTracker:
    global _tracker
    if _tracker is None:
        _tracker = BenchmarkTracker()
    return _tracker


def reset_benchmark_tracker() -> None:
    global _tracker
    _tracker = None
