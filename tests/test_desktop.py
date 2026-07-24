"""
Tests for JARVIS Desktop Assistant features.
"""

import tempfile
from pathlib import Path

import pytest


class TestPluginSystem:
    """Test plugin architecture."""

    def test_plugin_metadata(self):
        """Test PluginMetadata creation."""
        from jarvis.plugins.base import PluginMetadata

        metadata = PluginMetadata(
            name="test-plugin", version="1.0.0", author="Test", description="A test plugin"
        )

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test"

    def test_plugin_metadata_from_dict(self):
        """Test PluginMetadata from dict."""
        from jarvis.plugins.base import PluginMetadata

        data = {
            "name": "my-plugin",
            "version": "2.0.0",
            "author": "User",
            "description": "My plugin",
            "commands": ["cmd1", "cmd2"],
            "events": ["on_start"],
        }

        metadata = PluginMetadata.from_dict(data)

        assert metadata.name == "my-plugin"
        assert metadata.commands == ["cmd1", "cmd2"]
        assert metadata.events == ["on_start"]

    def test_plugin_manager_init(self):
        """Test PluginManager initialization."""
        from jarvis.plugins.base import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager(Path(tmpdir))
            assert manager.plugin_count == 0
            assert manager.enabled_plugins == []

    @pytest.mark.asyncio
    async def test_plugin_discover_empty(self):
        """Test plugin discovery with no plugins."""
        from jarvis.plugins.base import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager(Path(tmpdir))
            plugins = await manager.discover_plugins()
            assert plugins == []

    @pytest.mark.asyncio
    async def test_plugin_discover_with_plugin(self):
        """Test plugin discovery with plugins present."""
        from jarvis.plugins.base import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test plugin directory
            plugin_dir = Path(tmpdir) / "test-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "plugin.json").write_text('{"name": "test-plugin", "version": "1.0.0"}')

            manager = PluginManager(Path(tmpdir))
            plugins = await manager.discover_plugins()

            assert len(plugins) == 1
            assert plugins[0].name == "test-plugin"

    def test_plugin_manager_list(self):
        """Test plugin list functionality."""
        from jarvis.plugins.base import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager(Path(tmpdir))
            assert manager.list_plugins() == []


class TestWakeWord:
    """Test wake word detection."""

    def test_wake_word_config(self):
        """Test WakeWordConfig."""
        from jarvis.voice.wake_word import WakeWordConfig

        config = WakeWordConfig(word="jarvis", sensitivity=0.8, timeout=60.0)

        assert config.word == "jarvis"
        assert config.sensitivity == 0.8
        assert config.timeout == 60.0

    def test_wake_word_engine_init(self):
        """Test WakeWordEngine initialization."""
        from jarvis.voice.wake_word import WakeWordEngine

        engine = WakeWordEngine()
        assert engine.config.word == "jarvis"
        assert not engine.is_listening

    def test_wake_word_set_sensitivity(self):
        """Test setting sensitivity."""
        from jarvis.voice.wake_word import WakeWordEngine

        engine = WakeWordEngine()
        engine.set_sensitivity(0.5)
        assert engine.config.sensitivity == 0.5

        # Test bounds
        engine.set_sensitivity(1.5)
        assert engine.config.sensitivity == 1.0

        engine.set_sensitivity(-0.5)
        assert engine.config.sensitivity == 0.0

    @pytest.mark.asyncio
    async def test_voice_state_machine_init(self):
        """Test VoiceStateMachine initialization."""
        from jarvis.voice.wake_word import VoiceStateMachine

        state = VoiceStateMachine()
        assert state.state == VoiceStateMachine.IDLE
        assert state.is_idle

    @pytest.mark.asyncio
    async def test_voice_state_transition(self):
        """Test voice state transitions."""
        from jarvis.voice.wake_word import VoiceStateMachine

        state = VoiceStateMachine()
        await state.transition(state.LISTENING)
        assert state.state == state.LISTENING
        assert not state.is_idle

    @pytest.mark.asyncio
    async def test_voice_wake(self):
        """Test wake from idle."""
        from jarvis.voice.wake_word import VoiceStateMachine

        state = VoiceStateMachine()
        await state.wake()
        assert state.state == state.LISTENING


class TestScheduler:
    """Test task scheduler."""

    def test_scheduled_task_init(self):
        """Test ScheduledTask initialization."""
        from jarvis.services.scheduler import ScheduledTask, TaskType

        task = ScheduledTask(
            name="test-task",
            schedule="0 9 * * *",
            task_type=TaskType.REMINDER,
            command="echo hello",
        )

        assert task.name == "test-task"
        assert task.schedule == "0 9 * * *"
        assert task.enabled

    def test_scheduled_task_is_due(self):
        """Test task due checking with past next_run."""
        from datetime import datetime, timedelta

        from jarvis.services.scheduler import ScheduledTask, TaskType

        task = ScheduledTask(
            name="test-task",
            schedule="* * * * *",  # Every minute
            task_type=TaskType.COMMAND,
            command="echo hello",
        )

        # Set next_run to past to make task due
        task.next_run = datetime.now() - timedelta(minutes=5)
        task.last_run = datetime.now() - timedelta(minutes=6)

        assert task.is_due()
        assert task.next_run is not None

        # Test not due when disabled
        task.enabled = False
        assert not task.is_due()

    def test_task_scheduler_init(self):
        """Test TaskScheduler initialization."""
        from jarvis.services.scheduler import TaskScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = TaskScheduler(Path(tmpdir) / "scheduler.json")
            assert scheduler.tasks == {}
            assert len(scheduler.list_tasks()) == 0

    def test_add_task(self):
        """Test adding a task."""
        from jarvis.services.scheduler import TaskScheduler, TaskType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = TaskScheduler(Path(tmpdir) / "scheduler.json")

            task = scheduler.add_task(
                name="morning-reminder",
                schedule="0 9 * * *",
                command="Good morning!",
                task_type=TaskType.REMINDER,
            )

            assert task.name == "morning-reminder"
            assert "morning-reminder" in scheduler.tasks

    def test_remove_task(self):
        """Test removing a task."""
        from jarvis.services.scheduler import TaskScheduler, TaskType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = TaskScheduler(Path(tmpdir) / "scheduler.json")

            scheduler.add_task(
                name="test-task",
                schedule="0 9 * * *",
                command="echo test",
                task_type=TaskType.COMMAND,
            )

            assert scheduler.remove_task("test-task")
            assert "test-task" not in scheduler.tasks

    def test_enable_disable_task(self):
        """Test enabling/disabling tasks."""
        from jarvis.services.scheduler import TaskScheduler, TaskType

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = TaskScheduler(Path(tmpdir) / "scheduler.json")

            scheduler.add_task(
                name="test-task",
                schedule="0 9 * * *",
                command="echo test",
                task_type=TaskType.COMMAND,
            )

            assert scheduler.disable_task("test-task")
            assert not scheduler.tasks["test-task"].enabled

            assert scheduler.enable_task("test-task")
            assert scheduler.tasks["test-task"].enabled

    def test_daily_summary(self):
        """Test DailySummary."""
        from datetime import date

        from jarvis.services.scheduler import DailySummary

        summary = DailySummary(date=date.today())
        summary.commands_executed = 10
        summary.errors_encountered = 2

        data = summary.to_dict()
        assert data["commands_executed"] == 10
        assert data["errors_encountered"] == 2

    def test_summary_increment_commands(self):
        """Test incrementing command counter."""
        from jarvis.services.scheduler import TaskScheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = TaskScheduler(Path(tmpdir) / "scheduler.json")
            scheduler.increment_commands()
            scheduler.increment_commands()

            assert scheduler._daily_summary.commands_executed == 2


class TestProjectMemory:
    """Test project memory system."""

    def test_project_context_init(self):
        """Test ProjectContext initialization."""
        from jarvis.memory.project import ProjectContext

        project = ProjectContext(path=Path("/test/project"), name="test-project", language="Python")

        assert project.name == "test-project"
        assert project.language == "Python"
        assert project.frameworks == []

    def test_project_context_serialization(self):
        """Test ProjectContext serialization."""
        from jarvis.memory.project import ProjectContext

        project = ProjectContext(path=Path("/test/project"), name="test-project")

        data = project.to_dict()
        assert data["name"] == "test-project"
        assert data["path"] == "/test/project"

        restored = ProjectContext.from_dict(data)
        assert restored.name == project.name

    def test_project_memory_init(self):
        """Test ProjectMemory initialization."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            assert memory.projects == {}
            assert memory.active_project is None

    def test_add_project(self):
        """Test adding a project."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            project = memory.add_project(project_path, "TestProject")

            assert "TestProject" in memory.projects
            assert project.name == "TestProject"

    def test_remove_project(self):
        """Test removing a project."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            memory.add_project(project_path, "TestProject")
            assert memory.remove_project("TestProject")
            assert "TestProject" not in memory.projects

    def test_set_active_project(self):
        """Test setting active project."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            memory.add_project(project_path, "TestProject")
            memory.set_active("TestProject")

            assert memory.active_project == "TestProject"
            assert memory.get_active_project().name == "TestProject"

    def test_list_projects(self):
        """Test listing projects."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")

            for name in ["project1", "project2", "project3"]:
                path = Path(tmpdir) / name
                path.mkdir()
                memory.add_project(path, name)

            projects = memory.list_projects()
            assert len(projects) == 3
            names = [p["name"] for p in projects]
            assert "project1" in names

    def test_update_todos(self):
        """Test updating TODOs."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            memory.add_project(project_path, "TestProject")
            memory.update_todos("TestProject", ["Task 1", "Task 2"])

            project = memory.get_project("TestProject")
            assert project.todos == ["Task 1", "Task 2"]

    def test_add_note(self):
        """Test adding notes."""
        from jarvis.memory.project import ProjectMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ProjectMemory(Path(tmpdir) / "projects.json")
            project_path = Path(tmpdir) / "test_project"
            project_path.mkdir()

            memory.add_project(project_path, "TestProject")
            memory.add_note("TestProject", "This is a test note")

            project = memory.get_project("TestProject")
            assert "This is a test note" in project.notes


class TestKnowledgeBase:
    """Test knowledge base."""

    @pytest.mark.asyncio
    async def test_knowledge_base_init(self):
        """Test KnowledgeBase initialization."""
        from jarvis.memory.knowledge import LocalKnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = LocalKnowledgeBase(Path(tmpdir) / "knowledge")
            assert kb is not None

    @pytest.mark.asyncio
    async def test_knowledge_base_add(self):
        """Test adding entries."""
        from jarvis.memory.knowledge import LocalKnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = LocalKnowledgeBase(Path(tmpdir) / "knowledge")
            await kb.initialize()

            entry_id = await kb.add(content="This is a test entry", source="test", tags=["test"])

            assert entry_id is not None
            count = await kb.count()
            assert count >= 1
            kb.close()
            import gc
            gc.collect()

    @pytest.mark.asyncio
    async def test_knowledge_base_search(self):
        """Test search."""
        from jarvis.memory.knowledge import LocalKnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = LocalKnowledgeBase(Path(tmpdir) / "knowledge")
            await kb.initialize()

            await kb.add(content="Python is a programming language", source="test")
            await kb.add(content="JavaScript is for web development", source="test")

            results = await kb.search("Python")
            assert len(results) >= 1
            kb.close()
            import gc
            gc.collect()

    @pytest.mark.asyncio
    async def test_knowledge_base_get(self):
        """Test getting entry by ID."""
        from jarvis.memory.knowledge import LocalKnowledgeBase

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = LocalKnowledgeBase(Path(tmpdir) / "knowledge")
            await kb.initialize()

            entry_id = await kb.add(content="Test content")
            entry = await kb.get(entry_id)

            assert entry is not None
            assert entry["content"] == "Test content"
            kb.close()
            import gc
            gc.collect()


class TestSelfImprovement:
    """Test self-improvement logs."""

    def test_interaction_log(self):
        """Test InteractionLog creation."""
        from datetime import datetime

        from jarvis.memory.self_improve import InteractionLog, Outcome

        log = InteractionLog(
            timestamp=datetime.now(),
            input_text="test command",
            intent="test",
            outcome=Outcome.SUCCESS,
        )

        assert log.input_text == "test command"
        assert log.outcome == Outcome.SUCCESS

    def test_self_improvement_log_interaction(self):
        """Test logging interactions."""
        from jarvis.memory.self_improve import Outcome, SelfImprovementLogs

        with tempfile.TemporaryDirectory() as tmpdir:
            logs = SelfImprovementLogs(Path(tmpdir) / "logs.json")

            logs.log_interaction(input_text="hello", intent="greeting", outcome=Outcome.SUCCESS)

            assert len(logs.interactions) == 1

    def test_self_improvement_get_stats(self):
        """Test getting stats."""
        from jarvis.memory.self_improve import Outcome, SelfImprovementLogs

        with tempfile.TemporaryDirectory() as tmpdir:
            logs = SelfImprovementLogs(Path(tmpdir) / "logs.json")

            logs.log_interaction(input_text="cmd1", intent="task", outcome=Outcome.SUCCESS)
            logs.log_interaction(input_text="cmd2", intent="task", outcome=Outcome.FAILED)

            summary = logs.get_stats_summary()
            assert summary["total_interactions"] == 2
            assert summary["successes"] == 1
            assert summary["failures"] == 1


class TestDaemon:
    """Test daemon service."""

    def test_daemon_config(self):
        """Test DaemonConfig."""
        from jarvis.services.daemon import DaemonConfig

        config = DaemonConfig(name="test-jarvis")
        assert config.name == "test-jarvis"
        assert config.auto_restart is True

    def test_daemon_init(self):
        """Test JarvisDaemon initialization."""
        from jarvis.services.daemon import JarvisDaemon

        with tempfile.TemporaryDirectory() as _tmpdir:
            daemon = JarvisDaemon()
            assert daemon is not None
            assert not daemon.is_running

    @pytest.mark.asyncio
    async def test_daemon_start_stop(self):
        """Test daemon start/stop."""
        from jarvis.services.daemon import JarvisDaemon

        with tempfile.TemporaryDirectory() as tmpdir:
            daemon = JarvisDaemon()
            daemon.config.data_dir = Path(tmpdir)
            daemon.config.pid_file = Path(tmpdir) / "test.pid"

            started = await daemon.start()
            assert started
            assert daemon.is_running
            assert daemon.uptime is not None

            stopped = await daemon.stop()
            assert stopped
            assert not daemon.is_running


class TestListener:
    """Test continuous listener."""

    def test_listener_config(self):
        """Test ListenerConfig."""
        from jarvis.voice.listener import ListenerConfig

        config = ListenerConfig(wake_word="jarvis", silence_threshold=5.0)
        assert config.wake_word == "jarvis"
        assert config.silence_threshold == 5.0

    def test_voice_command(self):
        """Test VoiceCommand."""
        from jarvis.voice.listener import VoiceCommand

        cmd = VoiceCommand(raw_text="hello", intent="greeting", entities={})
        assert cmd.raw_text == "hello"
        assert cmd.intent == "greeting"

    @pytest.mark.asyncio
    async def test_parse_voice_command(self):
        """Test parsing voice commands."""
        from jarvis.voice.listener import parse_voice_command

        cmd = await parse_voice_command("jarvis search for python tutorials")
        assert cmd.raw_text == "jarvis search for python tutorials"
        assert cmd.intent == "search"

        cmd2 = await parse_voice_command("search for python tutorials")
        assert cmd2.intent == "search"


class TestVSCodeBridge:
    """Test VS Code integration."""

    def test_vscode_bridge_init(self):
        """Test VSCodeBridge initialization."""
        from jarvis.integrations.vscode import VSCodeBridge

        bridge = VSCodeBridge(port=8766)
        assert bridge.port == 8766
        assert not bridge.is_connected

    def test_editor_context(self):
        """Test EditorContext."""
        from jarvis.integrations.vscode import EditorContext

        ctx = EditorContext(current_file="/test/file.py", language="python")
        assert ctx.current_file == "/test/file.py"
        assert ctx.language == "python"

    def test_vscode_message(self):
        """Test VSCodeMessage."""
        from jarvis.integrations.vscode import MessageType, VSCodeMessage

        msg = VSCodeMessage(id="123", type=MessageType.REQUEST, method="test")
        assert msg.id == "123"
        assert msg.type == MessageType.REQUEST
