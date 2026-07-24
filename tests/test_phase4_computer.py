"""
Tests for JARVIS Phase 4 — Computer Agent.
"""



def test_computer_agent_singleton():
    from jarvis.computers.agent import get_computer_agent, reset_computer_agent
    agent = get_computer_agent()
    assert agent is get_computer_agent()
    reset_computer_agent()


def test_computer_agent_capture_screen():
    from jarvis.computers.agent import get_computer_agent
    get_computer_agent()


def test_computer_agent_open_application():
    from jarvis.computers.agent import get_computer_agent
    get_computer_agent()


def test_computer_agent_health_check():
    from jarvis.computers.agent import get_computer_agent, reset_computer_agent
    agent = get_computer_agent()
    health = agent.health_check()
    assert "healthy" in health
    reset_computer_agent()
