"""
Phase 3 Multi-Agent Collaboration Tests
"""


import pytest

from jarvis.agents.collaboration import AgentCollaboration


@pytest.mark.asyncio
async def test_collaboration_initialization():
    collab = AgentCollaboration()
    assert collab._default_timeout == 30.0


@pytest.mark.asyncio
async def test_resolve_conflict():
    collab = AgentCollaboration()
    conflict = {
        "candidates": [
            {"confidence": 0.8, "source_count": 3, "timestamp": 1000},
            {"confidence": 0.6, "source_count": 5, "timestamp": 2000},
        ]
    }
    resolved = collab.resolve_conflict(conflict)
    assert resolved["resolved"] is True
    assert resolved["winner"]["confidence"] == 0.8


@pytest.mark.asyncio
async def test_merge_outputs():
    collab = AgentCollaboration()
    outputs = [
        {"success": True, "sources": [{"url": "http://a.com", "title": "A"}], "key_findings": ["finding1"]},
        {"success": True, "sources": [{"url": "http://b.com", "title": "B"}], "key_findings": ["finding1", "finding2"]},
        {"success": False, "error": "fail"},
    ]
    merged = collab.merge_outputs(outputs)
    assert merged["combined"] is True
    assert len(merged["sources"]) == 2
    assert len(merged["key_findings"]) == 2
    assert len(merged["errors"]) == 1


def test_get_history_empty():
    collab = AgentCollaboration()
    assert collab.get_history() == []
