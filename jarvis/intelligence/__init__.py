"""
Intelligence module for JARVIS.
"""

from jarvis.intelligence.autonomous_engine import (
    AutonomousIntelligenceEngine,
    get_autonomous_intelligence_engine,
    reset_autonomous_intelligence_engine,
)
from jarvis.intelligence.context_fusion import (
    ContextFusionEngine,
    SourceWeight,
    UnifiedContext,
    get_context_fusion_engine,
    reset_context_fusion_engine,
)
from jarvis.intelligence.distributed import (
    DistributedIntelligence,
    DistributedResult,
)
from jarvis.intelligence.meta_reasoning import (
    ConfidenceEstimate,
    MetaLesson,
    MetaReasoningEngine,
    WeaknessReport,
    get_meta_reasoning_engine,
    reset_meta_reasoning_engine,
)

__all__ = [
    "AutonomousIntelligenceEngine",
    "ConfidenceEstimate",
    "ContextFusionEngine",
    "DistributedIntelligence",
    "DistributedResult",
    "MetaLesson",
    "MetaReasoningEngine",
    "SourceWeight",
    "UnifiedContext",
    "WeaknessReport",
    "get_autonomous_intelligence_engine",
    "get_context_fusion_engine",
    "get_meta_reasoning_engine",
    "reset_autonomous_intelligence_engine",
    "reset_context_fusion_engine",
    "reset_meta_reasoning_engine",
]
