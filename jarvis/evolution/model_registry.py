"""
JARVIS-V7 Evolution — Model Registry.

Manages model lifecycle stages: Production, Candidate, Experimental, Archive.
Never loses older models. Promotions are logged and reversible.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_DIR = Path.home() / ".jarvis" / "evolution"
DEFAULT_REGISTRY_FILE = "model_registry.json"


class ModelStage(StrEnum):
    PRODUCTION = "production"
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    ARCHIVE = "archive"


@dataclass
class ModelRecord:
    name: str
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: str = ModelStage.EXPERIMENTAL.value
    provider: str = "unknown"
    path: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    training_history: list[dict[str, Any]] = field(default_factory=list)
    benchmark_history: list[dict[str, Any]] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    promotion_history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def promote(self, from_stage: str, to_stage: str, reason: str, authorized_by: str = "") -> None:
        entry = {
            "from": from_stage,
            "to": to_stage,
            "reason": reason,
            "authorized_by": authorized_by,
            "timestamp": time.time(),
        }
        self.promotion_history.append(entry)
        self.stage = to_stage
        self.updated_at = time.time()

    def add_training_run(self, dataset: str, metrics: dict[str, Any]) -> None:
        entry = {
            "dataset": dataset,
            "metrics": metrics,
            "timestamp": time.time(),
        }
        self.training_history.append(entry)
        self.updated_at = time.time()

    def add_benchmark(self, benchmark_name: str, scores: dict[str, Any]) -> None:
        entry = {
            "name": benchmark_name,
            "scores": scores,
            "timestamp": time.time(),
        }
        self.benchmark_history.append(entry)
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelRecord:
        return cls(**data)


class ModelRegistry:
    _MAX_RECORDS = 10000

    def __init__(self, registry_dir: Path | None = None):
        self.registry_dir = registry_dir or DEFAULT_REGISTRY_DIR
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.registry_dir / DEFAULT_REGISTRY_FILE
        self._records: dict[str, ModelRecord] = {}
        self._load()

    def _warn_if_limit_exceeded(self) -> None:
        if len(self._records) >= self._MAX_RECORDS:
            logger.warning("Model registry record limit (%d) reached. Consider archiving old experimental models.", self._MAX_RECORDS)

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            for r in data.get("models", []):
                record = ModelRecord.from_dict(r)
                self._records[record.model_id] = record
        except Exception as exc:
            logger.debug("Model registry load failed: %s", exc)

    def _save(self) -> None:
        try:
            from jarvis.evolution import atomic_write_json
            atomic_write_json(
                self.path,
                {"models": [r.to_dict() for r in self._records.values()]},
            )
        except Exception:
            logger.debug("Model registry save failed", exc_info=True)

    def register(self, model: ModelRecord) -> ModelRecord:
        self._warn_if_limit_exceeded()
        self._records[model.model_id] = model
        self._save()
        logger.info("Registered model %s in stage %s", model.name, model.stage)
        return model

    def get(self, model_id: str) -> ModelRecord | None:
        return self._records.get(model_id)

    def get_by_name(self, name: str) -> ModelRecord | None:
        for record in self._records.values():
            if record.name == name:
                return record
        return None

    def get_stage(self, stage: str) -> list[ModelRecord]:
        return [r for r in self._records.values() if r.stage == stage]

    def list_all(self) -> list[ModelRecord]:
        return list(self._records.values())

    def promote(self, model_id: str, to_stage: str, reason: str, authorized_by: str = "") -> ModelRecord | None:
        record = self._records.get(model_id)
        if not record:
            return None
        from_stage = record.stage
        record.promote(from_stage, to_stage, reason, authorized_by)
        self._save()
        logger.info("Promoted model %s: %s -> %s", record.name, from_stage, to_stage)
        return record

    def add_training_run(self, model_id: str, dataset: str, metrics: dict[str, Any]) -> ModelRecord | None:
        record = self._records.get(model_id)
        if not record:
            return None
        record.add_training_run(dataset, metrics)
        self._save()
        return record

    def add_benchmark(self, model_id: str, benchmark_name: str, scores: dict[str, Any]) -> ModelRecord | None:
        record = self._records.get(model_id)
        if not record:
            return None
        record.add_benchmark(benchmark_name, scores)
        self._save()
        return record

    def rollback(self, model_id: str, to_stage: str = ModelStage.ARCHIVE.value, rollback_by: str = "") -> ModelRecord | None:
        record = self._records.get(model_id)
        if not record:
            return None
        from_stage = record.stage
        record.promote(from_stage, to_stage, "rollback", rollback_by)
        self._save()
        logger.info("Rolled back model %s: %s -> %s", record.name, from_stage, to_stage)
        return record

    def remove(self, model_id: str) -> bool:
        if model_id in self._records:
            del self._records[model_id]
            self._save()
            return True
        return False

    def get_production(self) -> ModelRecord | None:
        production = self.get_stage(ModelStage.PRODUCTION.value)
        if production:
            return production[-1]
        return None

    def get_candidates(self) -> list[ModelRecord]:
        return self.get_stage(ModelStage.CANDIDATE.value)

    def get_stats(self) -> dict[str, Any]:
        stages: dict[str, int] = {}
        for record in self._records.values():
            stages[record.stage] = stages.get(record.stage, 0) + 1
        return {
            "total_models": len(self._records),
            "by_stage": stages,
        }


_registry_instance: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance


def reset_model_registry() -> None:
    global _registry_instance
    _registry_instance = None
