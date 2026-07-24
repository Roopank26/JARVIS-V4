"""
JARVIS-V7 Evolution — Experience Collection Engine.

Continuously collects structured experience from every interaction,
tool usage, git activity, file operation, research, planning, etc.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_STORE_DIR = Path.home() / ".jarvis" / "evolution"
DEFAULT_EXPERIENCE_FILE = "experiences.jsonl"


@dataclass
class Experience:
    experience_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = "unknown"
    category: str = "general"
    task_id: str = ""
    input_text: str = ""
    output_text: str = ""
    success: bool = False
    duration_ms: float = 0.0
    provider: str | None = None
    model: str | None = None
    tool: str | None = None
    agent: str | None = None
    git_commit: str | None = None
    file_path: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    mistakes: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "source": self.source,
            "category": self.category,
            "task_id": self.task_id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "provider": self.provider,
            "model": self.model,
            "tool": self.tool,
            "agent": self.agent,
            "git_commit": self.git_commit,
            "file_path": self.file_path,
            "context": self.context,
            "mistakes": self.mistakes,
            "lessons": self.lessons,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class ExperienceStore:
    def __init__(self, store_dir: Path | None = None):
        self.store_dir = store_dir or DEFAULT_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.store_dir / DEFAULT_EXPERIENCE_FILE
        self._recent: list[Experience] = []
        self._load_recent()

    def _load_recent(self, limit: int = 5000) -> None:
        self._recent = []
        if not self.path.exists():
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self._recent.append(Experience(**data))
                    except Exception:
                        continue
                    if len(self._recent) >= limit:
                        break
        except Exception:
            pass
        self._recent = self._recent[-limit:]

    def append(self, experience: Experience) -> None:
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(experience.to_dict(), ensure_ascii=False) + "\n")
            self._recent.append(experience)
            if len(self._recent) > 5000:
                self._recent = self._recent[-5000:]
        except Exception as exc:
            logger.debug("ExperienceStore append failed: %s", exc)

    def get_recent(self, limit: int = 100) -> list[Experience]:
        return list(self._recent[-limit:])

    def get_by_category(self, category: str, limit: int = 100) -> list[Experience]:
        return [e for e in self._recent if e.category == category][-limit:]

    def get_success_rate(self, category: str | None = None, window: int = 500) -> float:
        items = self._recent[-window:]
        if category:
            items = [e for e in items if e.category == category]
        if not items:
            return 0.0
        return sum(1 for e in items if e.success) / len(items)


class ExperienceCollector:
    def __init__(self, store_dir: Path | None = None):
        self.store = ExperienceStore(store_dir)

    def record(
        self,
        source: str,
        category: str,
        input_text: str = "",
        output_text: str = "",
        success: bool = False,
        duration_ms: float = 0.0,
        provider: str | None = None,
        model: str | None = None,
        tool: str | None = None,
        agent: str | None = None,
        git_commit: str | None = None,
        file_path: str | None = None,
        mistakes: list[str] | None = None,
        lessons: list[str] | None = None,
        context: dict[str, Any] | None = None,
        task_id: str = "",
    ) -> Experience:
        experience = Experience(
            source=source,
            category=category,
            task_id=task_id,
            input_text=input_text,
            output_text=output_text,
            success=success,
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            tool=tool,
            agent=agent,
            git_commit=git_commit,
            file_path=file_path,
            mistakes=mistakes or [],
            lessons=lessons or [],
            context=context or {},
        )
        self.store.append(experience)
        return experience

    def record_task(self, task_id: str, input_text: str, output_text: str, success: bool, duration_ms: float = 0.0, **kwargs) -> Experience:
        return self.record(
            source="orchestrator",
            category="task",
            task_id=task_id,
            input_text=input_text,
            output_text=output_text,
            success=success,
            duration_ms=duration_ms,
            **kwargs,
        )

    def record_tool_use(self, tool_name: str, input_text: str, output_text: str, success: bool, duration_ms: float = 0.0, **kwargs) -> Experience:
        return self.record(
            source="tool",
            category="tool_use",
            tool=tool_name,
            input_text=input_text,
            output_text=output_text,
            success=success,
            duration_ms=duration_ms,
            **kwargs,
        )

    def record_research(self, query: str, output_text: str, success: bool, **kwargs) -> Experience:
        return self.record(
            source="research",
            category="research",
            input_text=query,
            output_text=output_text,
            success=success,
            **kwargs,
        )

    def record_coding(self, task_type: str, input_text: str, output_text: str, success: bool, file_path: str | None = None, **kwargs) -> Experience:
        return self.record(
            source="coding",
            category="coding",
            input_text=input_text,
            output_text=output_text,
            success=success,
            file_path=file_path,
            context={"task_type": task_type},
            **kwargs,
        )

    def record_git_activity(self, commit_hash: str, action: str, success: bool, output_text: str = "", **kwargs) -> Experience:
        return self.record(
            source="git",
            category="git_activity",
            input_text=action,
            output_text=output_text,
            success=success,
            git_commit=commit_hash,
            **kwargs,
        )

    def record_memory_interaction(self, operation: str, key: str, success: bool, **kwargs) -> Experience:
        return self.record(
            source="memory",
            category="memory",
            input_text=operation,
            output_text=key,
            success=success,
            **kwargs,
        )

    def record_autonomous_action(self, action_type: str, description: str, success: bool, **kwargs) -> Experience:
        return self.record(
            source="autonomous",
            category="autonomous",
            input_text=action_type,
            output_text=description,
            success=success,
            **kwargs,
        )

    def get_insights(self, window: int = 1000) -> dict[str, Any]:
        recent = self.store.get_recent(window)
        if not recent:
            return {"total_experiences": 0}
        success_rate = sum(1 for e in recent if e.success) / len(recent)
        avg_duration = sum(e.duration_ms for e in recent) / len(recent)
        by_category: dict[str, int] = {}
        by_tool: dict[str, int] = {}
        by_model: dict[str, int] = {}
        for e in recent:
            by_category[e.category] = by_category.get(e.category, 0) + 1
            if e.tool:
                by_tool[e.tool] = by_tool.get(e.tool, 0) + 1
            if e.model:
                by_model[e.model] = by_model.get(e.model, 0) + 1
        common_mistakes: dict[str, int] = {}
        for e in recent:
            for m in e.mistakes:
                common_mistakes[m] = common_mistakes.get(m, 0) + 1
        return {
            "total_experiences": len(recent),
            "success_rate": round(success_rate, 3),
            "avg_duration_ms": round(avg_duration, 1),
            "by_category": dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_tool": dict(sorted(by_tool.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_model": dict(sorted(by_model.items(), key=lambda x: x[1], reverse=True)[:10]),
            "common_mistakes": dict(sorted(common_mistakes.items(), key=lambda x: x[1], reverse=True)[:10]),
        }


_collector_instance: ExperienceCollector | None = None


def get_experience_collector() -> ExperienceCollector:
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = ExperienceCollector()
    return _collector_instance


def reset_experience_collector() -> None:
    global _collector_instance
    _collector_instance = None
