"""
Phase 3 Dashboard Expansion Tests
"""


from jarvis.core.dashboard import AIOSDashboard, DashboardSnapshot


def test_dashboard_snapshot_shape():
    dash = AIOSDashboard()
    snap = dash.snapshot()
    assert isinstance(snap, DashboardSnapshot)
    assert isinstance(snap.running_agents, list)
    assert isinstance(snap.running_tasks, list)
    assert isinstance(snap.system, dict)
    assert isinstance(snap.vision, dict)
    assert isinstance(snap.desktop, dict)
    assert isinstance(snap.knowledge_graph, dict)
    assert isinstance(snap.background_jobs, list)
    assert isinstance(snap.workflows, list)
