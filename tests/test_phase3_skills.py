"""
Phase 3 Self-Improving Skill System Tests
"""

import pytest

from jarvis.skills.manager import SkillManager


@pytest.fixture
def manager():
    return SkillManager()


def test_register_skill(manager):
    manager.register("echo", lambda x: x)
    assert manager.get("echo") is not None


def test_record_execution_updates_metrics(manager):
    manager.register("echo", lambda x: x)
    manager.record_execution("echo", {"success": True, "duration_ms": 100.0})
    metrics = manager.get_metrics("echo")
    assert metrics.total_executions == 1
    assert metrics.success_rate == 1.0


def test_record_failed_execution(manager):
    manager.register("echo", lambda x: x)
    manager.record_execution("echo", {"success": False, "error": "timeout", "duration_ms": 5000.0})
    metrics = manager.get_metrics("echo")
    assert metrics.failure_rate == 1.0
    assert "timeout" in metrics.common_errors


def test_optimize_prompt_no_prompts(manager):
    manager.register("echo", lambda x: x)
    assert manager.optimize_prompt("echo") is None


def test_optimize_prompt_with_prompts(manager):
    manager.register("echo", lambda x: x)
    manager._metrics["echo"].optimized_prompts = ["prompt_v1", "prompt_v2"]
    best = manager.optimize_prompt("echo")
    assert best == "prompt_v2"
