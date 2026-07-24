"""
Tests for Phase 2.0 - Goal Memory.

Validates goal CRUD, goal-aware prompt formatting,
and integration with MemoryManager and EnhancedMemoryManager.
"""

from pathlib import Path

import pytest

from jarvis.core.goal import Goal, GoalPriority
from jarvis.memory.base import MemoryCategory
from jarvis.memory.enhanced import EnhancedMemoryManager
from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.memory_manager import MemoryManager


class TestGoalCategory:
    def test_goals_in_memory_category(self):
        assert MemoryCategory.GOALS == "goals"
        assert "goals" in MemoryCategory.ALL


class TestLongTermGoalOps:
    def test_goal_save_and_recall(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")

        updated = ltm.save_goal("build_jarvis", "Evolve JARVIS into an AI OS", status="active", priority="high")
        assert updated is True

        goal = ltm.get_goal("build_jarvis")
        assert goal is not None
        assert goal["value"] == "Evolve JARVIS into an AI OS"
        assert goal["status"] == "active"
        assert goal["priority"] == "high"

    def test_goal_update_idempotent(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")

        first = ltm.save_goal("task", "Do work")
        second = ltm.save_goal("task", "Do work")

        assert first is True
        assert second is False

    def test_goal_listing_and_filtering(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")

        ltm.save_goal("goal_a", "Alpha", status="active", priority="high")
        ltm.save_goal("goal_b", "Beta", status="completed", priority="medium")
        ltm.save_goal("goal_c", "Gamma", status="blocked", priority="low")

        all_goals = ltm.get_goals()
        assert len(all_goals) == 3

        active = ltm.get_goals_by_status("active")
        assert len(active) == 1
        assert active[0]["key"] == "goal_a"

        current = ltm.get_current_goal()
        assert current["key"] == "goal_a"

    def test_goal_status_update(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")

        ltm.save_goal("goal", "Task", status="active")
        ok = ltm.update_goal_status("goal", "completed")
        assert ok is True
        assert ltm.get_current_goal() is None

    def test_goal_removal(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")
        assert ltm.save_goal("goal", "Task") is True
        assert ltm.remove_goal("goal") is True
        assert ltm.get_goal("goal") is None

    def test_format_goals_for_prompt(self, tmp_path: Path):
        ltm = LongTermMemory(tmp_path / "ltm.json")
        assert ltm.format_goals_for_prompt() == ""

        ltm.save_goal("g1", "Ship feature", status="active", priority="high")
        ltm.save_goal("g2", "Write docs", status="completed", priority="medium")

        out = ltm.format_goals_for_prompt()
        assert "Ship feature" in out
        assert "high" in out


class TestMemoryManagerGoalFacade:
    def test_memory_manager_goal_methods(self, tmp_path: Path):
        mgr = MemoryManager(tmp_path / "memory.json")

        assert mgr.save_goal("m1", "Master goal") is True
        assert mgr.get_goal("m1") is not None
        assert len(mgr.get_goals()) == 1
        assert mgr.get_current_goal() is not None
        assert mgr.update_goal_status("m1", "completed") is True
        assert mgr.get_current_goal() is None
        assert "Current Goals" in mgr.get_goal_context() or mgr.get_goal_context() == ""

    def test_goal_context_empty_when_none(self, tmp_path: Path):
        mgr = MemoryManager(tmp_path / "memory.json")
        assert mgr.get_goal_context() == ""

    def test_goal_persists_across_instances(self, tmp_path: Path):
        MemoryManager(tmp_path / "memory.json").save_goal("p1", "Persisted goal")
        mgr2 = MemoryManager(tmp_path / "memory.json")
        assert mgr2.get_goal("p1") is not None


class TestEnhancedMemoryGoalIntegration:
    def test_format_for_prompt_includes_goals(self, tmp_path: Path):
        mgr = MemoryManager(tmp_path / "memory.json")
        enhanced = EnhancedMemoryManager(memory_manager=mgr, user_profile=None)

        mgr.save_goal("prompt_goal", "Visible in prompt", status="active")
        out = enhanced.format_for_prompt()
        assert "Visible in prompt" in out
        assert "Current Goals" in out

    def test_handle_goal_command_save(self):
        mgr = MemoryManager()
        enhanced = EnhancedMemoryManager(memory_manager=mgr, user_profile=None)

        response = enhanced.handle_goal_command("Set my current goal as ship phase 2.0")
        assert "saved" in response.lower() or "goal" in response.lower()

    def test_handle_goal_command_query(self):
        mgr = MemoryManager()
        enhanced = EnhancedMemoryManager(memory_manager=mgr, user_profile=None)

        response = enhanced.handle_goal_command("What are my goals?")
        assert response is not None and len(response) > 0


class TestMasterAgentFacade:
    @pytest.mark.asyncio
    async def test_master_agent_process_delegates(self, tmp_path: Path):
        from jarvis.core.master_agent import MasterAgent

        agent = MasterAgent()
        await agent.process("hello")
        # Should not raise; defaults to chat mode

    @pytest.mark.asyncio
    async def test_master_agent_goal_threading(self, tmp_path: Path):
        from jarvis.core.master_agent import MasterAgent

        agent = MasterAgent()
        goal = Goal("p1", "Ship phase 2", priority=GoalPriority.HIGH)
        await agent.process("hello", goal=goal)
        assert agent.get_goal() is goal

    @pytest.mark.asyncio
    async def test_master_agent_set_goal(self):
        from jarvis.core.master_agent import MasterAgent

        agent = MasterAgent()
        goal = Goal("p2", "Run tests", priority=GoalPriority.MEDIUM)
        agent.set_goal(goal)
        assert agent.get_goal() == goal

    @pytest.mark.asyncio
    async def test_master_agent_interrupt_delegates(self):
        from jarvis.core.master_agent import MasterAgent

        agent = MasterAgent()
        agent.set_goal(None)
        agent.request_interrupt()
        agent.clear_interrupt()
