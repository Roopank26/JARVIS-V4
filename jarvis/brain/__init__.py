"""
JARVIS Brain — Autonomous Cognitive Architecture

This is the central intelligence coordinator of JARVIS.
The brain owns the cognitive loop; external models are optional substrates.

Architecture:
    INPUT → Perception → Context → Memory → Reasoning → Decision →
    Planning → Execution → Observation → Evaluation → Learning → RESPONSE
"""

from jarvis.brain.cognitive_core import CognitiveCore
from jarvis.brain.context_engine import ContextEngine
from jarvis.brain.confidence_engine import ConfidenceEngine
from jarvis.brain.decision_engine import DecisionEngine
from jarvis.brain.native_intelligence import NativeIntelligenceCore
from jarvis.brain.planning_engine import PlanningEngine
from jarvis.brain.reasoning_engine import ReasoningEngine
from jarvis.brain.self_reflection import SelfReflection

__all__ = [
    "CognitiveCore",
    "NativeIntelligenceCore",
    "ReasoningEngine",
    "DecisionEngine",
    "PlanningEngine",
    "ConfidenceEngine",
    "SelfReflection",
    "ContextEngine",
]
