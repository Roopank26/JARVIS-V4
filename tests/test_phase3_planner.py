"""
Phase 3 Planner Tests
"""


from jarvis.core.planner import Plan, Planner, PlanStep


def test_planner_fallback_plan():
    planner = Planner(llm_client=None)
    plan = planner._fallback_plan("echo hello")
    assert isinstance(plan, Plan)
    assert len(plan.steps) >= 1


def test_planner_validate_tool():
    planner = Planner()
    assert planner.validate_tool("bash", ["bash", "speak"]) is True
    assert planner.validate_tool("nonexistent", ["bash", "speak"]) is False


def test_planner_validate_plan():
    planner = Planner()
    plan = Plan(
        goal="test",
        steps=[PlanStep(step=1, tool="bash", description="run", parameters={"command": "echo"}, critical=True)],
    )
    ok, invalid = planner.validate_plan(plan, ["bash", "speak"])
    assert ok is True
    assert invalid == []
