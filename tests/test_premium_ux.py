"""
Tests for the premium UX enhancement modules.

These cover the new orchestration/UX layers added around the existing backend:
event bus, friendly errors, tool library, command palette, background task
manager, suggestions, and the orchestrator's lifecycle. They do NOT depend on
live providers, voice, or network.
"""

import asyncio
import pytest

from jarvis.events import (
    EventBus,
    EventType,
    Stage,
    get_event_bus,
    reset_event_bus,
)
from jarvis.errors import handle_error, FriendlyError
from jarvis.tools_library import ToolLibrary, reset_tool_library
from jarvis.palette import CommandPalette, reset_command_palette
from jarvis.tasks import (
    BackgroundTaskManager,
    TaskState,
    get_task_manager,
    reset_task_manager,
)
from jarvis.suggestions import SuggestionEngine, reset_suggestion_engine


@pytest.fixture
def bus():
    reset_event_bus()
    return get_event_bus()


def test_event_bus_pubsub():
    b = EventBus()
    received = []
    b.subscribe(EventType.TOAST, lambda e: received.append(e))
    b.emit(EventType.TOAST, {"msg": "hello"})
    assert len(received) == 1
    assert received[0].data["msg"] == "hello"


def test_event_bus_any_handler():
    b = EventBus()
    count = {"n": 0}
    b.subscribe(None, lambda e: count.__setitem__("n", count["n"] + 1))
    b.emit(EventType.TOKEN, {})
    b.emit(EventType.TASK, {})
    assert count["n"] == 2


def test_event_bus_history_filter():
    b = EventBus()
    b.emit(EventType.TOKEN, {"x": 1})
    b.emit(EventType.TASK, {"x": 2})
    assert len(b.history(EventType.TOKEN)) == 1
    assert len(b.history()) == 2


def test_friendly_error_auth():
    err = handle_error(Exception("401 invalid_api_key"))
    assert isinstance(err, FriendlyError)
    assert "API key" in err.title
    assert err.fix


def test_friendly_error_network():
    err = handle_error(Exception("ConnectionError: failed to resolve"))
    assert "Connection" in err.title


def test_friendly_error_module():
    err = handle_error(Exception("ModuleNotFoundError: No module named 'faster_whisper'"))
    assert "not installed" in err.title
    assert "faster_whisper" in err.fix


@pytest.mark.asyncio
async def test_tool_library_refresh_empty(bus):
    reset_tool_library()
    lib = ToolLibrary(bus=bus)
    tools = lib.refresh()
    assert isinstance(tools, list)


@pytest.mark.asyncio
async def test_tool_library_favorite_and_recent(bus):
    reset_tool_library()
    lib = ToolLibrary(bus=bus)
    lib.refresh()
    # Favorite toggle should not raise even with no tools
    assert lib.toggle_favorite("nonexistent") is False
    lib._cache["demo"] = type("T", (), {
        "name": "demo", "description": "d", "category": "x",
        "permission": "ask_once", "source": "registry", "plugin_id": None,
        "read_only": True, "dangerous": False, "used_at": 0.0, "favorite": False,
    })()
    assert lib.toggle_favorite("demo") is True
    assert "demo" in [t.name for t in lib.favorites()]
    lib.mark_used("demo")
    assert "demo" in [t.name for t in lib.recent()]
    assert lib.search("demo")[0].name == "demo"


def test_palette_static_search():
    reset_command_palette()
    p = CommandPalette()
    items = p.search("voice")
    titles = [i["title"] for i in items]
    assert any("voice" in t.lower() or "Voice" in t for t in titles)
    # Exact command present
    assert any(i["id"] == "cmd.help" for i in p.search("help"))


def test_palette_history():
    reset_command_palette()
    p = CommandPalette()
    p.add_history("research obesity prediction")
    res = p.search("obesity prediction")
    assert any(i["category"] == "history" for i in res)


@pytest.mark.asyncio
async def test_task_manager_lifecycle(bus):
    reset_task_manager()
    mgr = BackgroundTaskManager(bus=bus, max_concurrent=2)
    await mgr.start()
    try:
        done = asyncio.Event()

        def factory():
            async def _run():
                await asyncio.sleep(0.05)
                return "ok"
            return _run()

        tid = mgr.submit("test task", factory, category="test")
        # Wait for completion
        for _ in range(50):
            t = mgr.get(tid)
            if t and t.state == TaskState.COMPLETED:
                break
            await asyncio.sleep(0.02)
        assert mgr.get(tid).state == TaskState.COMPLETED
        assert mgr.get(tid).result == "ok"
    finally:
        await mgr.stop()


@pytest.mark.asyncio
async def test_task_manager_cancel(bus):
    reset_task_manager()
    mgr = BackgroundTaskManager(bus=bus, max_concurrent=1)
    await mgr.start()
    try:
        def factory():
            async def _run():
                await asyncio.sleep(5)
                return "late"
            return _run()

        tid = mgr.submit("long task", factory, category="test")
        await asyncio.sleep(0.05)
        assert await mgr.cancel(tid) is True
        t = mgr.get(tid)
        assert t.state in (TaskState.CANCELLED,)
    finally:
        await mgr.stop()


@pytest.mark.asyncio
async def test_task_manager_retry_then_fail(bus):
    reset_task_manager()
    mgr = BackgroundTaskManager(bus=bus, max_concurrent=1)
    await mgr.start()
    try:
        counter = {"n": 0}

        def factory():
            async def _run():
                counter["n"] += 1
                raise RuntimeError("boom")
            return _run()

        tid = mgr.submit("failing", factory, category="test", )
        mgr.get(tid).max_retries = 1
        for _ in range(60):
            t = mgr.get(tid)
            if t and t.state in (TaskState.FAILED, TaskState.COMPLETED):
                break
            await asyncio.sleep(0.02)
        assert mgr.get(tid).state == TaskState.FAILED
    finally:
        await mgr.stop()


def test_suggestion_engine_scan_runs():
    reset_suggestion_engine()
    eng = SuggestionEngine(bus=EventBus())
    # Should not raise even if git/subprocess unavailable
    out = eng.scan()
    assert isinstance(out, list)


@pytest.mark.asyncio
async def test_orchestrator_emits_stages(bus):
    """Orchestrator must emit reasoning-stage events without touching backend."""
    from jarvis.orchestrator import JarvisOrchestrator

    class FakeAgent:
        def __init__(self):
            self.tools = type("R", (), {"add_callback": lambda *a, **k: None})()
            self.memory = type("M", (), {"format_for_prompt": lambda: ""})()

        async def answer_query(self, prompt, **kw):
            return "echo: " + prompt[:20]

    events = []
    bus.subscribe(EventType.STAGE, lambda e: events.append(e.data["stage"]))
    orch = JarvisOrchestrator(FakeAgent(), bus=bus)
    result = await orch.process("hello there")
    assert "thinking" in events
    assert "complete" in events
    assert result
