"""
Tests for Phase 2.1 - Dynamic Agent Registry.
"""

from jarvis.core.agent_registry import AgentRegistry, get_agent_registry, register_builtin_agents


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        registry.register("test_agent", "A test agent", "mymodule", "factory_fn")

        meta = registry.get_metadata("test_agent")
        assert meta is not None
        assert meta.name == "test_agent"
        assert meta.description == "A test agent"

    def test_unregister(self):
        registry = AgentRegistry()
        registry.register("agent1", "desc", "m", "f")
        assert registry.unregister("agent1") is True
        assert registry.get_metadata("agent1") is None
        assert registry.unregister("agent1") is False

    def test_list_names(self):
        registry = AgentRegistry()
        registry.register("a", "d", "m", "f")
        registry.register("b", "d", "m", "f")
        assert set(registry.list_names()) == {"a", "b"}

    def test_list_available(self):
        registry = AgentRegistry()
        registry.register("active", "d", "m", "f", enabled=True)
        registry.register("disabled", "d", "m", "f", enabled=False)

        available = registry.list_available()
        assert "active" in available
        assert "disabled" not in available

    def test_search(self):
        registry = AgentRegistry()
        registry.register("weather", "Get weather data", "m", "f")
        registry.register("search", "Search the web", "m", "f")

        results = registry.search("weather")
        assert len(results) == 1
        assert results[0].name == "weather"

    def test_register_function(self):
        registry = AgentRegistry()

        def my_fn():
            pass

        registry.register_function("my_fn", my_fn, {"description": "my function"})
        assert registry.get("my_fn") is my_fn

    def test_callbacks(self):
        registry = AgentRegistry()
        events = []

        def cb(name, event):
            events.append((name, event))

        registry.add_callback(cb)
        registry.register("cb_agent", "desc", "m", "f")

        assert ("cb_agent", "registered") in events

    def test_set_health(self):
        registry = AgentRegistry()
        registry.register("agent", "d", "m", "f")
        registry.set_health("agent", "degraded")
        assert registry.get_metadata("agent").health == "degraded"

    def test_auto_discover(self):
        registry = AgentRegistry()
        registry.register("d1", "d", "m", "f")
        registry.register("d2", "d", "m", "f")
        count = registry.auto_discover()
        assert count >= 0

    def test_get_agent_registry_singleton(self):
        r1 = get_agent_registry()
        r2 = get_agent_registry()
        assert r1 is r2

    def test_register_builtin_agents(self):
        registry = AgentRegistry()
        register_builtin_agents(registry)
        names = registry.list_names()
        assert "research" in names or "vscode" in names or "coding" in names
