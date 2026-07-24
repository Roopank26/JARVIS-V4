"""
Tests for JARVIS Phase 4 — System Diagnostics.
"""

import pytest


def test_diagnostics_singleton():
    from jarvis.monitoring.health import SystemSelfDiagnostics
    diag = SystemSelfDiagnostics()
    assert diag is not None


@pytest.mark.asyncio
async def test_diagnostics_run():
    from jarvis.monitoring.health import SystemSelfDiagnostics
    from jarvis.runtime.manager import RuntimeManager
    diag = SystemSelfDiagnostics()
    runtime = RuntimeManager()
    await runtime.start()
    report = await diag.run_diagnostics()
    assert isinstance(report.subsystems, dict)
    assert len(report.subsystems) > 0
    await runtime.stop()
