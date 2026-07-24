"""
Tests for Phase 2.2 - Long Running Task Engine.
"""

import asyncio

import pytest

from jarvis.core.task_engine import LongRunningTaskEngine, TaskHandle, TaskState


class TestLongRunningTaskEngine:
    @pytest.mark.asyncio
    async def test_create_and_list_tasks(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            handle.progress = 50
            await asyncio.sleep(0.01)
            handle.progress = 100

        handle = engine.create_task("background_job", coro)
        await asyncio.sleep(0)
        assert handle.state == TaskState.RUNNING
        tasks = engine.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_id == handle.task_id

    @pytest.mark.asyncio
    async def test_task_completes(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            handle.progress = 100
            await asyncio.sleep(0.01)

        handle = engine.create_task("job", coro)
        await engine.wait(handle.task_id)
        assert handle.state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_task_cancel(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                pass

        handle = engine.create_task("cancel_me", coro)
        await asyncio.sleep(0.01)
        assert engine.cancel(handle.task_id) is True
        await engine.wait(handle.task_id)
        assert handle.state == TaskState.CANCELLED

    @pytest.mark.asyncio
    async def test_task_pause_resume(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")
        events = []

        async def coro(handle: TaskHandle):
            for _ in range(3):
                events.append("tick")
                await asyncio.sleep(0.05)

        handle = engine.create_task("pausable", coro)
        await asyncio.sleep(0.02)
        assert engine.pause(handle.task_id) is True
        assert handle.state == TaskState.PAUSED
        assert engine.resume(handle.task_id) is True
        assert handle.state == TaskState.RUNNING
        await engine.wait(handle.task_id)

    @pytest.mark.asyncio
    async def test_task_failure(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            raise RuntimeError("boom")

        handle = engine.create_task("fail", coro)
        await engine.wait(handle.task_id)
        assert handle.state == TaskState.FAILED
        assert handle.error == "boom"

    @pytest.mark.asyncio
    async def test_task_persistence(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            await asyncio.sleep(0.01)

        handle = engine.create_task("persist", coro)
        await engine.wait(handle.task_id)
        saved = tmp_path / "tasks" / f"{handle.task_id}.json"
        assert saved.exists()
        content = saved.read_text(encoding="utf-8")
        assert handle.task_id in content

    @pytest.mark.asyncio
    async def test_get_task_and_running(self, tmp_path):
        engine = LongRunningTaskEngine(state_dir=tmp_path / "tasks")

        async def coro(handle: TaskHandle):
            await asyncio.sleep(0.1)

        h1 = engine.create_task("r1", coro)
        engine.create_task("r2", coro)
        await asyncio.sleep(0)
        assert engine.get_task(h1.task_id) is h1
        running = engine.get_running()
        assert len(running) == 2

    def test_get_task_engine_singleton(self):
        from jarvis.core.task_engine import get_task_engine

        g1 = get_task_engine()
        g2 = get_task_engine()
        assert g1 is g2
