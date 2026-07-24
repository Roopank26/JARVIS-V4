"""
Tests for AI OS Dashboard.
"""

from unittest.mock import patch

from jarvis.core.dashboard import AIOSDashboard, DashboardSnapshot, get_dashboard


class TestAIOSDashboard:
    def test_snapshot_returns_snapshot(self):
        dashboard = AIOSDashboard()
        snap = dashboard.snapshot()
        assert isinstance(snap, DashboardSnapshot)

    def test_get_dashboard_singleton(self):
        d1 = get_dashboard()
        d2 = get_dashboard()
        assert d1 is d2

    @patch("jarvis.core.agent_registry.get_agent_registry")
    def test_snapshot_collects_agents(self, mock_registry):
        mock_registry.return_value.list_available.return_value = ["research"]
        dashboard = AIOSDashboard()
        snap = dashboard.snapshot()
        assert "research" in snap.running_agents

    @patch("jarvis.core.task_engine.get_task_engine")
    def test_snapshot_collects_tasks(self, mock_engine):
        from jarvis.core.task_engine import TaskHandle, TaskState

        handle = TaskHandle(task_id="t1", name="job", state=TaskState.RUNNING)
        mock_engine.return_value.list_tasks.return_value = [handle]
        dashboard = AIOSDashboard()
        snap = dashboard.snapshot()
        assert len(snap.running_tasks) == 1
        assert snap.running_tasks[0]["name"] == "job"

    @patch("jarvis.memory.memory_manager.get_memory_manager")
    def test_snapshot_collects_goals(self, mock_memory):
        mock_memory.return_value.get_current_goal.return_value = {"key": "g1", "value": "Ship"}
        dashboard = AIOSDashboard()
        snap = dashboard.snapshot()
        assert snap.current_goal is not None
        assert snap.current_goal["key"] == "g1"

    @patch("jarvis.memory.memory_manager.get_memory_manager")
    def test_snapshot_collects_memory_stats(self, mock_memory):
        mock_memory.return_value.get_full_memory.return_value = {"identity": {"name": {}}, "preferences": {}}
        dashboard = AIOSDashboard()
        snap = dashboard.snapshot()
        assert "entries" in snap.memory_stats
