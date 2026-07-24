"""
JARVIS-V7 Evolution — Autonomous AI Evolution System.

Core package for continuous AI evolution, self-improvement, knowledge management,
model evolution, benchmarking, and autonomous research.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from jarvis.evolution.auto_start import AutoStartManager, get_auto_start_manager
from jarvis.evolution.benchmark import (
    BenchmarkEngine,
    BenchmarkResult,
    BenchmarkSuite,
    PromotionGate,
    get_promotion_gate,
)
from jarvis.evolution.capability_improvement import (
    CapabilityImprovementLoop,
    ImprovementPhase,
    ImprovementRecord,
    ImprovementStatus,
    PhaseResult,
    get_improvement_loop,
    reset_improvement_loop,
)
from jarvis.evolution.evolution_engine import (
    BackgroundEvolutionEngine,
    EvolutionState,
    get_evolution_engine,
)
from jarvis.evolution.experience_collector import (
    ExperienceCollector,
    ExperienceStore,
    get_experience_collector,
)
from jarvis.evolution.knowledge_graph_v2 import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphEngine,
    get_knowledge_graph,
)
from jarvis.evolution.learning_pipeline import (
    CandidateTrainer,
    DatasetFactory,
    OfflineLearningPipeline,
    TrainingDataset,
    TrainingRun,
    get_learning_pipeline,
)
from jarvis.evolution.model_registry import (
    ModelRecord,
    ModelRegistry,
    ModelStage,
    get_model_registry,
)
from jarvis.evolution.owner import OwnerModel, get_owner_model
from jarvis.evolution.repo_watcher import RepositoryWatcher, get_repo_watcher
from jarvis.evolution.reports import ExecutiveReports, get_executive_reports
from jarvis.evolution.research_engine import (
    AutonomousResearchEngine,
    ResearchLog,
    ResearchTask,
    get_research_engine,
)
from jarvis.evolution.self_review import SelfReview, SelfReviewEngine, get_self_review_engine
from jarvis.evolution.system_resource_monitor import SystemResourceMonitor, get_resource_monitor
from jarvis.evolution.v7_orchestrator import V7JarvisOrchestrator, get_v7_orchestrator

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        bak_path = path.with_suffix(path.suffix + ".bak")
        if path.exists():
            with contextlib.suppress(Exception):
                path.replace(bak_path)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(Exception):
            os.unlink(tmp_path)
        raise


__all__ = [
    "atomic_write_json",
    "OwnerModel",
    "get_owner_model",
    "ExperienceCollector",
    "ExperienceStore",
    "get_experience_collector",
    "KnowledgeGraphEngine",
    "GraphNode",
    "GraphEdge",
    "get_knowledge_graph",
    "ModelRegistry",
    "ModelRecord",
    "ModelStage",
    "get_model_registry",
    "BenchmarkEngine",
    "BenchmarkResult",
    "BenchmarkSuite",
    "PromotionGate",
    "get_promotion_gate",
    "CapabilityImprovementLoop",
    "ImprovementPhase",
    "ImprovementRecord",
    "ImprovementStatus",
    "PhaseResult",
    "get_improvement_loop",
    "reset_improvement_loop",
    "SelfReviewEngine",
    "SelfReview",
    "get_self_review_engine",
    "AutonomousResearchEngine",
    "ResearchTask",
    "ResearchLog",
    "get_research_engine",
    "OfflineLearningPipeline",
    "DatasetFactory",
    "CandidateTrainer",
    "TrainingDataset",
    "TrainingRun",
    "get_learning_pipeline",
    "BackgroundEvolutionEngine",
    "EvolutionState",
    "get_evolution_engine",
    "V7JarvisOrchestrator",
    "get_v7_orchestrator",
    "ExecutiveReports",
    "get_executive_reports",
    "RepositoryWatcher",
    "get_repo_watcher",
    "SystemResourceMonitor",
    "get_resource_monitor",
    "AutoStartManager",
    "get_auto_start_manager",
]
