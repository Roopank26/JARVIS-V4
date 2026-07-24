"""
Tests for JARVIS-V8 AGW (Artificial General Work) System.

Covers:
- Directors (all 9)
- Work Session Mode
- Project Intelligence
- AI Reasoning Engine
- AGW Orchestrator
- Self-Improvement Enhancements
"""

from __future__ import annotations

import os
import tempfile

import pytest

from jarvis.agw.directors import (
    ArchitectureDirector,
    AutomationDirector,
    ExecutiveDirector,
    KnowledgeDirector,
    LearningDirector,
    QualityDirector,
    ResearchDirector,
    SecurityDirector,
    SoftwareEngineeringDirector,
    get_all_directors,
    initialize_all_directors,
)
from jarvis.agw.orchestrator import AGWOrchestrator
from jarvis.agw.project_intelligence import get_project_intelligence
from jarvis.agw.reasoning import get_reasoning_engine
from jarvis.agw.self_improvement import get_agw_self_improvement
from jarvis.agw.work_session import WorkSessionManager


def test_version():
    import jarvis
    assert jarvis.__version__ == "3.0.0"


class TestSoftwareEngineeringDirector:

    def test_import(self):
        d = SoftwareEngineeringDirector()
        assert d.DOMAIN == "software_engineering"

    def test_capabilities(self):
        d = SoftwareEngineeringDirector()
        caps = d.get_capabilities()
        assert "repo_analysis" in caps

    def test_workflows(self):
        d = SoftwareEngineeringDirector()
        wfs = d.get_workflows()
        assert len(wfs) >= 1
        assert wfs[0].name == "repository_audit"


class TestResearchDirector:

    def test_import(self):
        d = ResearchDirector()
        assert d.DOMAIN == "research"

    def test_capabilities(self):
        d = ResearchDirector()
        caps = d.get_capabilities()
        assert "web_search" in caps


class TestExecutiveDirector:

    def test_import(self):
        d = ExecutiveDirector()
        assert d.DOMAIN == "executive"

    def test_capabilities(self):
        d = ExecutiveDirector()
        caps = d.get_capabilities()
        assert "goal_management" in caps


class TestKnowledgeDirector:

    def test_import(self):
        d = KnowledgeDirector()
        assert d.DOMAIN == "knowledge"


class TestAutomationDirector:

    def test_import(self):
        d = AutomationDirector()
        assert d.DOMAIN == "automation"

    def test_workflows(self):
        d = AutomationDirector()
        wfs = d.get_workflows()
        assert any(w.name == "dependency_check" for w in wfs)


class TestLearningDirector:

    def test_import(self):
        d = LearningDirector()
        assert d.DOMAIN == "learning"


class TestQualityDirector:

    def test_import(self):
        d = QualityDirector()
        assert d.DOMAIN == "quality"


class TestSecurityDirector:

    def test_import(self):
        d = SecurityDirector()
        assert d.DOMAIN == "security"


class TestArchitectureDirector:

    def test_import(self):
        d = ArchitectureDirector()
        assert d.DOMAIN == "architecture"


@pytest.mark.asyncio
async def test_initialize_all_directors():
    directors = await initialize_all_directors()
    assert len(directors) == 9
    assert "software_engineering" in directors
    assert "research" in directors


@pytest.mark.asyncio
async def test_get_all_directors():
    await initialize_all_directors()
    all_dirs = get_all_directors()
    assert len(all_dirs) == 9


@pytest.mark.asyncio
async def test_executive_director_daily_brief():
    d = ExecutiveDirector()
    await d.initialize()
    result = await d.execute("daily brief", {"period": "daily_brief"})
    assert result["status"] == "completed"
    assert "brief" in result


@pytest.mark.asyncio
async def test_security_director_execute():
    d = SecurityDirector()
    await d.initialize()
    result = await d.execute("security audit", {})
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_automation_director_execute():
    d = AutomationDirector()
    await d.initialize()
    result = await d.execute("check deps", {"workflow": "dependency_check"})
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_work_session_start():
    mgr = WorkSessionManager()
    with tempfile.TemporaryDirectory() as tmp:
        ctx = await mgr.start_session(tmp)
        assert ctx is not None
        assert ctx.project_name == os.path.basename(os.path.abspath(tmp))
        mgr.end_session()


def test_get_workspace_info():
    mgr = WorkSessionManager()
    workspace = mgr._detect_repo(".")
    assert isinstance(workspace, (str, type(None)))


@pytest.mark.asyncio
async def test_project_intelligence_stats():
    pi = get_project_intelligence()
    stats = pi.get_stats()
    assert "tracked_projects" in stats


@pytest.mark.asyncio
async def test_reasoning_default():
    engine = get_reasoning_engine()
    result = await engine.reason("hello there")
    assert result.input == "hello there"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_reasoning_research():
    engine = get_reasoning_engine()
    result = await engine.reason("research quantum computing")
    assert "researcher" in result.selected_agents
    assert "web_search" in result.selected_tools


@pytest.mark.asyncio
async def test_reasoning_code():
    engine = get_reasoning_engine()
    result = await engine.reason("refactor this code")
    assert "software_engineering_director" in result.selected_agents


def test_decompose_build():
    engine = get_reasoning_engine()
    task = engine.decompose_task("build a REST API")
    assert len(task.subtasks) >= 3
    assert task.risk_assessment in ("low", "moderate")


def test_decompose_fix():
    engine = get_reasoning_engine()
    task = engine.decompose_task("fix login bug")
    assert len(task.subtasks) >= 2
    names = [s["name"] for s in task.subtasks]
    assert "diagnose" in names
    assert "patch" in names


def test_reasoning_history():
    engine = get_reasoning_engine()
    history = engine.get_history()
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_agw_initialize():
    orch = AGWOrchestrator()
    await orch.initialize()
    assert orch._initialized is True
    assert len(orch.get_directors()) == 9


@pytest.mark.asyncio
async def test_agw_process():
    orch = AGWOrchestrator()
    await orch.initialize()
    result = await orch.process("hello jarvis")
    assert "status" in result
    assert "input" in result


@pytest.mark.asyncio
async def test_agw_get_status():
    orch = AGWOrchestrator()
    status = orch.get_status()
    assert "initialized" in status
    assert "running" in status


def test_agw_self_improvement_record():
    imp = get_agw_self_improvement()
    reflection = imp.record_reflection(
        director="software_engineering",
        task="review code",
        confidence=0.8,
        plan=["analyze", "suggest"],
        outcome={"status": "completed"},
    )
    assert reflection.score == 1.0
    assert len(reflection.suggestions) >= 1


def test_agw_scores():
    imp = get_agw_self_improvement()
    imp.record_reflection("swe", "t1", 0.5, [], {"status": "completed"})
    imp.record_reflection("swe", "t2", 0.8, [], {"status": "completed"})
    scores = imp.get_director_scores()
    assert "swe" in scores
