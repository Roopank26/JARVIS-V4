"""
Tests for JARVIS Phase 4 — Autonomous Goal Engine.
"""


import pytest


def test_create_goal():
    from jarvis.goals import GoalType, get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    goal = engine.create_goal("Test Goal", "A test goal", goal_type=GoalType.PROJECT)
    assert goal.title == "Test Goal"
    assert goal.goal_type == GoalType.PROJECT
    reset_goal_engine()


def test_list_goals():
    from jarvis.goals import get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    engine.create_goal("Goal 1", "Desc 1")
    engine.create_goal("Goal 2", "Desc 2")
    goals = engine.list_goals()
    assert len(goals) >= 2
    reset_goal_engine()


def test_delete_goal():
    from jarvis.goals import get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    goal = engine.create_goal("Delete Me", "Desc")
    assert engine.delete_goal(goal.goal_id) is True
    assert engine.get_goal(goal.goal_id) is None
    reset_goal_engine()


def test_create_task():
    from jarvis.goals import get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    goal = engine.create_goal("Goal", "Desc")
    task = engine.create_task(goal.goal_id, "Task 1", "Do something")
    assert task is not None
    assert task.name == "Task 1"
    reset_goal_engine()


def test_get_progress():
    from jarvis.goals import get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    goal = engine.create_goal("Goal", "Desc")
    engine.create_task(goal.goal_id, "T1", "Do T1")
    progress = engine.get_progress(goal.goal_id)
    assert progress is not None
    assert progress.total_tasks == 1
    reset_goal_engine()


@pytest.mark.asyncio
async def test_goal_engine_start_stop():
    from jarvis.goals import get_goal_engine, reset_goal_engine
    engine = get_goal_engine()
    await engine.start()
    assert engine._running is True
    engine.stop()
    assert engine._running is False
    reset_goal_engine()
