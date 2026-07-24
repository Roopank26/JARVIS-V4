"""
JARVIS-V4 CAE — Executive Reports.

Generates continuous executive reporting:
- Daily summaries
- Weekly summaries
- Monthly reports
- Learning progress
- Repository health
- Research backlog
- Deadline tracking
- Technology watchlist
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_REPORTS_DIR = Path.home() / ".jarvis" / "evolution" / "reports"


@dataclass
class ExecutiveReport:
    report_type: str
    period_start: float
    period_end: float
    generated_at: float = field(default_factory=time.time)
    sections: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "sections": self.sections,
            "summary": self.summary,
        }


class ExecutiveReports:
    def __init__(self, reports_dir: Path | None = None) -> None:
        self.reports_dir = reports_dir or DEFAULT_REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def daily_summary(self) -> ExecutiveReport:
        now = time.time()
        start = now - 86400.0
        return self._build_report("daily", start, now)

    def weekly_summary(self) -> ExecutiveReport:
        now = time.time()
        start = now - 7 * 86400.0
        return self._build_report("weekly", start, now)

    def monthly_report(self) -> ExecutiveReport:
        now = time.time()
        start = now - 30 * 86400.0
        return self._build_report("monthly", start, now)

    def _build_report(self, report_type: str, start: float, end: float) -> ExecutiveReport:
        report = ExecutiveReport(report_type=report_type, period_start=start, period_end=end)
        report.sections.append(self._experience_section(start, end))
        report.sections.append(self._reflection_section(start, end))
        report.sections.append(self._model_section(start, end))
        report.sections.append(self._knowledge_section(start, end))
        report.sections.append(self._research_section(start, end))
        report.sections.append(self._health_section(start, end))
        report.sections.append(self._repo_section(start, end))
        report.summary = self._summarize(report.sections)
        self._persist(report)
        return report

    def _experience_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.experience_collector import get_experience_collector
            collector = get_experience_collector()
            all_items = collector.store.get_recent(5000)
            items = [e for e in all_items if start <= e.timestamp <= end]
            success_rate = sum(1 for e in items if e.success) / len(items) if items else 0.0
            by_category: dict[str, int] = {}
            for e in items:
                by_category[e.category] = by_category.get(e.category, 0) + 1
            return {
                "title": "Experience & Learning",
                "total_experiences": len(items),
                "success_rate": round(success_rate, 3),
                "top_categories": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]),
            }
        except Exception as exc:
            logger.debug("Experience section failed: %s", exc)
            return {"title": "Experience & Learning", "error": str(exc)}

    def _reflection_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.self_review import get_self_review_engine
            reviewer = get_self_review_engine()
            recent = [r for r in reviewer.history if start <= r.timestamp <= end]
            failure_rate = sum(1 for r in recent if not r.success) / len(recent) if recent else 0.0
            high_severity = [r for r in recent if r.severity in ("high", "critical")]
            return {
                "title": "Self-Reflection",
                "reviews": len(recent),
                "failure_rate": round(failure_rate, 3),
                "high_severity_issues": len(high_severity),
                "top_improvements": self._top_improvements(recent),
            }
        except Exception as exc:
            logger.debug("Reflection section failed: %s", exc)
            return {"title": "Self-Reflection", "error": str(exc)}

    def _top_improvements(self, reviews: list[Any]) -> list[str]:
        all_imp: dict[str, int] = {}
        for r in reviews:
            for imp in r.improvements:
                all_imp[imp] = all_imp.get(imp, 0) + 1
        return [
            f"{imp} ({count}x)"
            for imp, count in sorted(all_imp.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

    def _model_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.model_registry import get_model_registry
            registry = get_model_registry()
            all_records = registry.list_all()
            recent = [r for r in all_records if start <= r.updated_at <= end]
            production = registry.get_production()
            return {
                "title": "Model Evolution",
                "total_models": len(all_records),
                "recent_updates": len(recent),
                "production_model": production.name if production else "none",
                "stages": registry.get_stats().get("by_stage", {}),
            }
        except Exception as exc:
            logger.debug("Model section failed: %s", exc)
            return {"title": "Model Evolution", "error": str(exc)}

    def _knowledge_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.knowledge_graph_v2 import get_knowledge_graph
            graph = get_knowledge_graph()
            stats = graph.get_stats()
            return {
                "title": "Knowledge Graph",
                "nodes": stats.get("nodes", 0),
                "edges": stats.get("edges", 0),
                "node_types": stats.get("node_types", []),
            }
        except Exception as exc:
            logger.debug("Knowledge section failed: %s", exc)
            return {"title": "Knowledge Graph", "error": str(exc)}

    def _research_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.research_engine import get_research_engine
            engine = get_research_engine()
            log = engine.log
            if log.path.exists():
                recent = []
                try:
                    with open(log.path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                task = __import__("jarvis.evolution.research_engine", fromlist=["ResearchTask"]).ResearchTask(**__import__("json").loads(line))
                                if start <= task.timestamp <= end:
                                    recent.append(task)
                            except Exception:
                                continue
                except Exception:
                    pass
                return {
                    "title": "Research Activity",
                    "research_cycles": len(recent),
                    "completed": sum(1 for t in recent if t.status == "complete"),
                }
        except Exception as exc:
            logger.debug("Research section failed: %s", exc)
        return {"title": "Research Activity", "research_cycles": 0}

    def _health_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.system_resource_monitor import get_resource_monitor
            monitor = get_resource_monitor()
            history = monitor.get_history()
            period = [h for h in history if start <= h.get("timestamp", 0) <= end]
            if period:
                avg_cpu = sum(h.get("cpu_percent", 0.0) for h in period) / len(period)
                avg_ram = sum(h.get("ram_percent", 0.0) for h in period) / len(period)
                return {
                    "title": "System Health",
                    "samples": len(period),
                    "avg_cpu": round(avg_cpu, 1),
                    "avg_ram": round(avg_ram, 1),
                    "high_intensity_events": sum(1 for h in period if h.get("high_intensity")),
                }
        except Exception as exc:
            logger.debug("Health section failed: %s", exc)
        return {"title": "System Health"}

    def _repo_section(self, start: float, end: float) -> dict[str, Any]:
        try:
            from jarvis.evolution.repo_watcher import get_repo_watcher
            watcher = get_repo_watcher()
            return {
                "title": "Repository Health",
                "watched_repos": len(watcher.list_repos()),
            }
        except Exception as exc:
            logger.debug("Repo section failed: %s", exc)
            return {"title": "Repository Health"}

    def _summarize(self, sections: list[dict[str, Any]]) -> str:
        lines = []
        for section in sections:
            title = section.get("title", "Report")
            lines.append(f"{title}:")
            for key, value in section.items():
                if key == "title":
                    continue
                lines.append(f"  {key}: {value}")
            lines.append("")
        return "\n".join(lines)

    def _persist(self, report: ExecutiveReport) -> None:
        try:
            path = self.reports_dir / f"{report.report_type}_{int(report.period_start)}.json"
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.debug("Report persist failed: %s", exc)

    def get_recent(self, report_type: str = "daily", limit: int = 10) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        try:
            pattern = f"{report_type}_*.json"
            files = sorted(self.reports_dir.glob(pattern), reverse=True)[:limit]
            for path in files:
                try:
                    with open(path, encoding="utf-8") as f:
                        reports.append(__import__("json").load(f))
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("Get recent reports failed: %s", exc)
        return reports


_reports_instance: ExecutiveReports | None = None


def get_executive_reports() -> ExecutiveReports:
    global _reports_instance
    if _reports_instance is None:
        _reports_instance = ExecutiveReports()
    return _reports_instance


def reset_executive_reports() -> None:
    global _reports_instance
    _reports_instance = None
