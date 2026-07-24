"""
Tests for Phase 2.1 - Shared Context Bus.
"""

from jarvis.core.context_bus import ContextBus, get_context_bus, reset_context_bus


class TestContextBus:
    def test_publish_context(self):
        bus = ContextBus()
        envelope = bus.publish(event_type="task", task_id="t1", data={"foo": "bar"})
        assert envelope.task_id == "t1"
        assert envelope.event_type == "task"
        assert envelope.data == {"foo": "bar"}

    def test_publish_task_goal_result_error(self):
        bus = ContextBus()
        t = bus.publish_task("t1", {"status": "started"})
        assert t.task_id == "t1"

        g = bus.publish_goal("g1", {"name": "alpha"})
        assert g.goal_id == "g1"

        r = bus.publish_result("t1", {"output": "ok"})
        assert r.event_type == "result"

        e = bus.publish_error("t1", {"message": "boom"})
        assert e.event_type == "error"

    def test_subscribe_and_unsubscribe(self):
        bus = ContextBus()
        received = []

        def handler(env):
            received.append(env)

        unsub = bus.subscribe("custom", handler)
        bus.publish(event_type="custom", data={"x": 1})
        assert len(received) == 1
        assert received[0].data == {"x": 1}

        unsub()
        bus.publish(event_type="custom", data={"x": 2})
        assert len(received) == 1

    def test_subscribe_task(self):
        bus = ContextBus()
        received = []

        def handler(env):
            received.append(env)

        unsub = bus.subscribe_task("t1", handler)
        bus.publish_task("t1", {"step": 1})
        assert len(received) == 1
        unsub()

    def test_subscribe_goal(self):
        bus = ContextBus()
        received = []

        def handler(env):
            received.append(env)

        bus.subscribe_goal("g1", handler)
        bus.publish_goal("g1", {"priority": "high"})
        assert len(received) == 1
        assert received[0].data == {"priority": "high"}

    def test_history(self):
        bus = ContextBus()
        bus.publish(event_type="task", task_id="t1")
        bus.publish(event_type="task", task_id="t2")
        all_history = bus.history()
        assert len(all_history) >= 2

        filtered = bus.history(event_type="task")
        assert len(filtered) >= 2

    def test_get_context_bus_singleton(self):
        b1 = get_context_bus()
        b2 = get_context_bus()
        assert b1 is b2

    def test_reset_context_bus(self):
        get_context_bus()
        reset_context_bus()
        b2 = get_context_bus()
        assert isinstance(b2, ContextBus)
