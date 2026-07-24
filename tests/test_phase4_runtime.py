"""
Tests for JARVIS Phase 4 — Runtime Manager.
"""


import pytest


def test_runtime_manager_singleton():
    from jarvis.runtime.manager import get_runtime_manager, reset_runtime_manager
    mgr = get_runtime_manager()
    assert mgr is get_runtime_manager()
    reset_runtime_manager()


def test_runtime_manager_registers_defaults():
    from jarvis.runtime.manager import RuntimeManager
    mgr = RuntimeManager()
    names = list(mgr._subsystems.keys())
    assert "master_agent" in names
    assert "browser" in names
    assert "desktop" in names


def test_runtime_manager_topological_sort():
    from jarvis.runtime.manager import RuntimeManager
    mgr = RuntimeManager()
    result = mgr._topological_sort()
    assert result.index("master_agent") < result.index("orchestration")
    assert result.index("memory") < result.index("knowledge_graph")


def test_runtime_manager_snapshot():
    from jarvis.runtime.manager import RuntimeManager
    mgr = RuntimeManager()
    snap = mgr.snapshot()
    assert not snap.running
    assert snap.uptime_seconds == 0


@pytest.mark.asyncio
async def test_runtime_manager_start_stop():
    from jarvis.runtime.manager import RuntimeManager
    mgr = RuntimeManager()
    await mgr.start()
    assert mgr._running is True
    await mgr.stop()
    assert mgr._running is False


@pytest.mark.asyncio
async def test_runtime_manager_health_check():
    from jarvis.runtime.manager import RuntimeManager
    mgr = RuntimeManager()
    await mgr.start()
    health = await mgr.health_check()
    assert "master_agent" in health
    await mgr.stop()
