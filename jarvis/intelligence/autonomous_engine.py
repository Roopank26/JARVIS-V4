"""
JARVIS Phase 5 — Autonomous Intelligence Engine.

Orchestrates all Phase 5 modules:
- Meta Reasoning
- Long-Horizon Planning
- Context Fusion
- Tool Intelligence
- Self Evaluation
- Root Cause Learning
- Benchmark Tracking

Hooks into JarvisAgent.process() as a non-invasive enhancement layer.
Does NOT modify JarvisAgent. Provides a wrapper and callbacks.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from jarvis.benchmarks.tracker import get_benchmark_tracker
from jarvis.core.self_evaluation import get_self_evaluation_engine
from jarvis.evolution.root_cause import get_root_cause_learner
from jarvis.goals.long_horizon import get_long_horizon_planner
from jarvis.intelligence.context_fusion import get_context_fusion_engine
from jarvis.intelligence.meta_reasoning import get_meta_reasoning_engine
from jarvis.tools.intelligence import ToolOutcome, get_tool_intelligence_engine

logger = logging.getLogger(__name__)


class AutonomousIntelligenceEngine:
    """
    Phase 5 orchestrator. Wraps existing agent behavior with autonomous intelligence.

    Usage:
        engine = AutonomousIntelligenceEngine()
        response = await engine.process_with_intelligence(agent, user_input)
    """

    def __init__(self) -> None:
        self._meta = get_meta_reasoning_engine()
        self._long_horizon = get_long_horizon_planner()
        self._fusion = get_context_fusion_engine()
        self._tool_intel = get_tool_intelligence_engine()
        self._eval_engine = get_self_evaluation_engine()
        self._root_cause = get_root_cause_learner()
        self._benchmarks = get_benchmark_tracker()
        self._active_task_id: str | None = None

    async def process_with_intelligence(self, agent: Any, user_input: str) -> str:
        """
        Wrap agent.process with Phase 5 intelligence layers.

        Order:
        1. Context Fusion (enrich input)
        2. Agent.process (existing behavior)
        3. Self Evaluation (score output)
        4. Meta Reasoning (reflect on outcome)
        5. Tool Intelligence (learn from tool results if applicable)
        """
        task_id = uuid.uuid4().hex[:12]
        self._active_task_id = task_id
        start = time.perf_counter()

        fused = await self._fusion.fuse(user_input)
        enriched_input = user_input
        if fused.fused_summary:
            enriched_input = f"{user_input}\n\n[CONTEXT]\n{fused.fused_summary[:4000]}"

        try:
            response = await agent.process(enriched_input)
        except Exception as exc:
            response = f"I encountered an issue: {exc}"
            self._meta.evaluate_task(
                task_id=task_id,
                description=user_input,
                result=response,
                duration_ms=(time.perf_counter() - start) * 1000.0,
                metadata={"error": str(exc)},
            )
            self._root_cause.analyze_failure(task_id, user_input, response, duration_ms=(time.perf_counter() - start) * 1000.0)
            return response

        duration_ms = (time.perf_counter() - start) * 1000.0
        confidence = self._estimate_response_confidence(response)
        area_scores = {
            "reasoning": confidence,
            "planning": confidence * 0.9,
            "memory": min(1.0, len(fused.memory_facts) / 5.0),
            "research": len(fused.document_excerpts) / 5.0,
            "coding": len(fused.repository_context) / 3.0,
            "voice": 0.5,
            "vision": 0.5 if fused.screen_context.get("available") else 0.0,
            "automation": 1.0 if "error" not in response.lower() else 0.3,
        }
        self._eval_engine.evaluate_response(
            response_id=task_id,
            reasoning_steps=1,
            plan_steps=0,
            memory_hits=len(fused.memory_facts),
            tools_used=0,
            success="error" not in response.lower() and "failed" not in response.lower(),
            latency_ms=duration_ms,
            confidence=confidence,
            output_length=len(response),
            area_scores=area_scores,
        )
        self._meta.evaluate_task(
            task_id=task_id,
            description=user_input,
            result=response,
            duration_ms=duration_ms,
            metadata={
                "memory_hits": len(fused.memory_facts),
                "sources_used": len(fused.sources_used),
                "reasoning_steps": 1,
            },
        )
        if "error" in response.lower() and "no error" not in response.lower():
            self._root_cause.analyze_failure(task_id, user_input, response, duration_ms=duration_ms)
        self._benchmarks.record_monthly_scores({
            "reasoning_quality": area_scores["reasoning"],
            "planning_quality": area_scores["planning"],
            "coding_quality": area_scores["coding"],
            "research_quality": area_scores["research"],
            "automation_success": area_scores["automation"],
            "memory_retrieval": area_scores["memory"],
            "voice_latency": area_scores["voice"],
            "vision_latency": area_scores["vision"],
            "repository_understanding": area_scores["coding"],
            "knowledge_growth": len(fused.knowledge_graph_edges) / 10.0,
        })
        return response

    def estimate_tool(self, tool_name: str, context: str = "") -> dict[str, Any]:
        return self._tool_intel.estimate(tool_name, context).to_dict()

    def record_tool_outcome(self, tool_name: str, success: bool, latency_ms: float, error: str | None = None) -> None:
        outcome = ToolOutcome(
            tool_name=tool_name,
            success=success,
            latency_ms=latency_ms,
            error=error,
        )
        self._tool_intel.record_outcome(outcome)

    def get_autonomous_insights(self) -> dict[str, Any]:
        return {
            "meta_reasoning": self._meta.get_autonomous_insights(),
            "long_horizon": {
                "goal_engine_health": self._long_horizon._engine.health_check(),
                "prediction_enabled": True,
                "adaptive_replanning_enabled": True,
            },
            "context_fusion": {
                "retrieval_precision": self._fusion.get_retrieval_precision(),
                "last_fusion_available": self._fusion._last_fusion is not None,
            },
            "tool_intelligence": {
                "top_tools": self._tool_intel.get_top_tools(5),
                "underperforming": self._tool_intel.get_underperforming_tools(),
            },
            "self_evaluation": self._eval_engine.get_monthly_summary(),
            "root_cause": {
                "recurring_failures": self._root_cause.get_recurring_failures(5),
                "prevention_rules": len(self._root_cause._prevention_rules),
            },
            "benchmarks": self._benchmarks.get_summary(),
        }


_autonomous_engine: AutonomousIntelligenceEngine | None = None


def get_autonomous_intelligence_engine() -> AutonomousIntelligenceEngine:
    global _autonomous_engine
    if _autonomous_engine is None:
        _autonomous_engine = AutonomousIntelligenceEngine()
    return _autonomous_engine


def reset_autonomous_intelligence_engine() -> None:
    global _autonomous_engine
    _autonomous_engine = None
