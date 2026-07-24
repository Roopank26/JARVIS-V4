"""
Phase 3 Orchestration Engine Tests
"""


import pytest

from jarvis.orchestration.engine import OrchestrationEngine


@pytest.mark.asyncio
async def test_orchestration_engine_initialization():
    engine = OrchestrationEngine()
    assert engine._master is not None
    assert engine.get_recent_history() == []


@pytest.mark.asyncio
async def test_subsystem_registration():
    engine = OrchestrationEngine()
    dummy = object()
    engine.register_subsystem("learning", dummy)
    assert engine.get_subsystem("learning") is dummy


@pytest.mark.asyncio
async def test_process_records_history():
    engine = OrchestrationEngine()
    async def fake_process(x, goal=None):
        return "ok"
    engine._master.process = fake_process
    result = await engine.process("hello")
    assert "ok" in result
    assert len(engine.get_recent_history()) == 1
    assert engine.get_recent_history()[0].success is True


@pytest.mark.asyncio
async def test_shutdown():
    engine = OrchestrationEngine()
    await engine.shutdown()
    assert engine._running is False
