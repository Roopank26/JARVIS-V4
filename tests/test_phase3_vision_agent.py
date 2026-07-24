"""
Phase 3 Vision Agent Tests
"""

import pytest

from jarvis.agents.vision_agent import VisionAgent


@pytest.mark.asyncio
async def test_vision_agent_initialization():
    agent = VisionAgent()
    await agent.initialize()
    assert agent._provider_name is None or isinstance(agent._provider_name, str)


@pytest.mark.asyncio
async def test_ocr_not_implemented():
    agent = VisionAgent()
    text = await agent.ocr("nonexistent.png")
    assert isinstance(text, str)
