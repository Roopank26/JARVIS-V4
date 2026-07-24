"""
Tests for JARVIS-V4 Capability Improvement Loop.

Validates the 5-phase improvement cycle:
- Observe
- Analyze
- Improve
- Validate
- Deploy
"""

import pytest

from jarvis.evolution.capability_improvement import (
    ImprovementPhase,
    ImprovementRecord,
    ImprovementStatus,
    PhaseResult,
    get_improvement_loop,
    reset_improvement_loop,
)


class TestCapabilityImprovementLoop:
    @pytest.fixture(autouse=True)
    def _reset_loop(self):
        reset_improvement_loop()

    def test_loop_singleton(self):
        loop1 = get_improvement_loop()
        loop2 = get_improvement_loop()
        assert loop1 is loop2

    def test_record_initialization(self):
        record = ImprovementRecord(
            improvement_id="imp_001",
            title="Test improvement",
            capability="reasoning",
        )
        assert record.improvement_id == "imp_001"
        assert record.capability == "reasoning"
        assert record.status == ImprovementStatus.PENDING.value
        assert record.backward_compatible is True

    def test_observe_phase(self):
        loop = get_improvement_loop()
        result = loop.observe(
            benchmark_scores={"reasoning": 0.7, "coding": 0.8},
            benchmark_latency_ms=150.0,
            failure_count=2,
            success_rate=0.85,
            capability_weaknesses=["reasoning"],
        )
        assert result.phase == ImprovementPhase.OBSERVE.value
        assert result.success is True
        assert "reasoning" in result.details["capability_weaknesses"]
        assert result.details["benchmark_scores"]["reasoning"] == 0.7
        assert result.details["failure_count"] == 2
        assert result.duration_ms >= 0

    def test_observe_phase_with_system_health(self):
        loop = get_improvement_loop()
        result = loop.observe(
            benchmark_scores={"reasoning": 0.5},
            system_health={"cpu_percent": 45.0, "ram_percent": 60.0},
        )
        assert result.phase == ImprovementPhase.OBSERVE.value
        assert result.details["system_health"]["cpu_percent"] == 45.0

    def test_analyze_phase(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.5, "coding": 0.9},
            failure_count=5,
            success_rate=0.6,
            capability_weaknesses=["reasoning"],
        )
        result = loop.analyze(
            observed=observed,
            improvement_ideas=["Improve reasoning by adding more practice examples"],
        )
        assert result.phase == ImprovementPhase.ANALYZE.value
        assert result.success is True
        assert isinstance(result.details["prioritized_improvements"], list)
        assert isinstance(result.details["root_causes"], list)
        assert "history_comparison" in result.details

    def test_analyze_phase_with_root_causes(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.3},
            failure_count=10,
            success_rate=0.3,
            capability_weaknesses=["reasoning"],
        )
        result = loop.analyze(observed=observed)
        assert result.phase == ImprovementPhase.ANALYZE.value

    def test_improve_phase(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.5},
            failure_count=3,
            success_rate=0.7,
            capability_weaknesses=["reasoning"],
        )
        analyzed = loop.analyze(observed=observed)
        result = loop.improve(
            analyzed=analyzed,
            capability_target="reasoning",
        )
        assert result.phase == ImprovementPhase.IMPROVE.value
        assert result.success is True
        assert result.details["capability_target"] == "reasoning"
        assert result.details["total_applied"] >= 0

    def test_improve_phase_with_specific_fn(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.4},
            failure_count=0,
            success_rate=1.0,
            capability_weaknesses=["reasoning"],
        )
        analyzed = loop.analyze(observed=observed)
        result = loop.improve(
            analyzed=analyzed,
            improvement_fn="add_reasoning_examples",
            capability_target="reasoning",
        )
        assert result.phase == ImprovementPhase.IMPROVE.value

    def test_validate_phase(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.7},
            failure_count=0,
            success_rate=1.0,
        )
        improved = loop.observe(
            benchmark_scores={"reasoning": 0.8},
            failure_count=0,
            success_rate=1.0,
        )
        result = loop.validate(
            observed_before=observed,
            improved=improved,
            test_command="echo tests_pass",
            lint_command="echo lint_pass",
        )
        assert result.phase == ImprovementPhase.VALIDATE.value
        assert result.details["quality_gates"]["tests"] == "PASS"
        assert result.details["quality_gates"]["lint"] == "PASS"

    def test_validate_phase_with_regression_check(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.8, "coding": 0.9},
            failure_count=0,
            success_rate=1.0,
        )
        improved = loop.observe(
            benchmark_scores={"reasoning": 0.85, "coding": 0.85},
            failure_count=0,
            success_rate=1.0,
        )
        result = loop.validate(
            observed_before=observed,
            improved=improved,
            test_command="echo tests_pass",
            lint_command="echo lint_pass",
        )
        assert result.details["quality_gates"]["regression"] == "PASS"

    def test_validate_phase_failing_tests(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.5},
            failure_count=0,
            success_rate=1.0,
        )
        improved = loop.observe(
            benchmark_scores={"reasoning": 0.6},
            failure_count=0,
            success_rate=1.0,
        )
        result = loop.validate(
            observed_before=observed,
            improved=improved,
            test_command="exit 1",
        )
        assert result.details["quality_gates"]["tests"] == "FAIL"

    def test_deploy_phase(self):
        loop = get_improvement_loop()
        record = ImprovementRecord(
            improvement_id="imp_002",
            phase=ImprovementPhase.DEPLOY.value,
            title="Deploy test improvement",
            capability="coding",
        )
        record.status = ImprovementStatus.COMPLETED.value
        result = loop.deploy(record=record)
        assert result.phase == ImprovementPhase.DEPLOY.value
        assert result.success is True
        assert result.details["deployed"] is True
        assert record in loop.records

    def test_deploy_phase_blocked_by_failed_gate(self):
        loop = get_improvement_loop()
        record = ImprovementRecord(
            improvement_id="imp_003",
            phase=ImprovementPhase.DEPLOY.value,
            title="Blocked deploy",
            capability="reasoning",
        )
        record.status = ImprovementStatus.FAILED.value
        mock_validate = PhaseResult(
            phase=ImprovementPhase.VALIDATE.value,
            success=False,
            details={"quality_gates": {"tests": "FAIL"}},
        )
        result = loop.deploy(record=record, validate_result=mock_validate)
        assert result.success is False
        assert result.details["deployed"] is False

    def test_full_cycle(self):
        loop = get_improvement_loop()
        summary = loop.run_cycle(
            improvement_id="cycle_001",
            title="Test full improvement cycle",
            capability="reasoning",
            benchmark_scores_current={"reasoning": 0.8, "coding": 0.9},
            benchmark_scores_previous={"reasoning": 0.5, "coding": 0.7},
            benchmark_latency_ms=200.0,
            failure_count=2,
            success_rate=0.8,
            weakness_list=["reasoning"],
            improvement_ideas=["Add more reasoning practice examples"],
            test_command="echo tests_ok",
            lint_command="echo lint_ok",
        )
        assert summary["cycle_id"] == "cycle_001"
        assert summary["capability"] == "reasoning"
        assert "phases" in summary
        assert ImprovementPhase.OBSERVE.value in summary["phases"]
        assert ImprovementPhase.ANALYZE.value in summary["phases"]
        assert ImprovementPhase.IMPROVE.value in summary["phases"]
        assert ImprovementPhase.VALIDATE.value in summary["phases"]
        assert ImprovementPhase.DEPLOY.value in summary["phases"]
        assert summary["all_gates_passed"] is True

    def test_full_cycle_with_failing_test(self):
        loop = get_improvement_loop()
        summary = loop.run_cycle(
            improvement_id="cycle_002",
            title="Test cycle with failing test gate",
            capability="coding",
            benchmark_scores_current={"coding": 0.8},
            failure_count=0,
            success_rate=1.0,
            weakness_list=[],
            improvement_ideas=["Improve coding"],
            test_command="exit 1",
            lint_command="echo lint_ok",
        )
        assert summary["all_gates_passed"] is False

    def test_cycle_history(self):
        loop = get_improvement_loop()
        assert len(loop.get_cycle_history()) == 0
        loop.run_cycle(
            improvement_id="cycle_003",
            title="History test",
            capability="memory",
            benchmark_scores_current={"memory": 0.9},
            test_command="echo ok",
            lint_command="echo ok",
        )
        history = loop.get_cycle_history()
        assert len(history) == 1
        assert history[0]["capability"] == "memory"

    def test_improvement_trend(self):
        loop = get_improvement_loop()
        trend = loop.get_improvement_trend("reasoning")
        assert trend["capability"] == "reasoning"
        assert trend["trend"] == "no_data"

    def test_get_quality_gate_summary_empty(self):
        loop = get_improvement_loop()
        summary = loop.get_quality_gate_summary()
        assert summary["total_cycles"] == 0
        assert summary["gates_passed"] == 0

    def test_phase_result_serialization(self):
        loop = get_improvement_loop()
        result = loop.observe(
            benchmark_scores={"reasoning": 0.7},
            failure_count=1,
            success_rate=0.9,
        )
        d = result.to_dict()
        assert d["phase"] == ImprovementPhase.OBSERVE.value
        assert d["success"] is True
        assert d["duration_ms"] >= 0

    def test_improvement_record_serialization(self):
        record = ImprovementRecord(
            improvement_id="imp_004",
            phase=ImprovementPhase.DEPLOY.value,
            title="Serialization test",
            capability="research",
            metrics_before={"research": 0.5},
            metrics_after={"research": 0.7},
            delta={"research": 0.2},
        )
        d = record.to_dict()
        assert d["improvement_id"] == "imp_004"
        assert d["capability"] == "research"
        assert d["metrics_before"]["research"] == 0.5
        assert d["metrics_after"]["research"] == 0.7
        assert d["delta"]["research"] == 0.2
        assert d["backward_compatible"] is True
        assert d["documented"] is False

    def test_observe_empty_inputs(self):
        loop = get_improvement_loop()
        result = loop.observe()
        assert result.success is True
        assert result.details["benchmark_scores"] == {}
        assert result.details["capability_weaknesses"] == []

    def test_improve_with_no_ideas(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.5},
            failure_count=0,
            success_rate=1.0,
        )
        analyzed = loop.analyze(observed=observed)
        result = loop.improve(analyzed=analyzed)
        assert result.phase == ImprovementPhase.IMPROVE.value

    def test_validate_skips_benchmark_when_no_command(self):
        loop = get_improvement_loop()
        observed = loop.observe(
            benchmark_scores={"reasoning": 0.7},
            failure_count=0,
            success_rate=1.0,
        )
        improved = loop.observe(
            benchmark_scores={"reasoning": 0.8},
            failure_count=0,
            success_rate=1.0,
        )
        result = loop.validate(
            observed_before=observed,
            improved=improved,
            test_command="echo ok",
            lint_command="echo ok",
        )
        assert result.details["quality_gates"]["benchmarks"] == "SKIPPED"

    def test_multiple_cycles_history(self):
        loop = get_improvement_loop()
        for i in range(3):
            loop.run_cycle(
                improvement_id=f"cycle_multi_{i}",
                title=f"Multi test {i}",
                capability="reasoning",
                benchmark_scores_current={"reasoning": 0.7 + i * 0.1},
                test_command="echo ok",
                lint_command="echo ok",
            )
        history = loop.get_cycle_history(limit=2)
        assert len(history) == 2