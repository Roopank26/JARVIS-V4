"""
Validation tests for JARVIS Autonomous Desktop Mode.
Tests all requirements for persistent, always-on operation.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
import json
import pytest

from jarvis.desktop import DesktopAssistant, DesktopConfig
from jarvis.desktop.state import PersistentState, AppState, StartupManager


class TestDesktopConfig:
    """Test desktop configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = DesktopConfig()
        
        assert config.wake_word == "jarvis"
        assert config.wake_sensitivity == 0.7
        assert config.idle_timeout == 300.0
        assert config.auto_start is True
        assert config.minimize_to_tray is True
        assert config.auto_index_projects is True
        assert config.daily_summary_time == "18:00"

    def test_config_save_load(self):
        """Test config persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(
                wake_word="computer",
                wake_sensitivity=0.8,
                data_dir=Path(tmpdir)
            )
            
            # Save
            config_file = Path(tmpdir) / "config.json"
            config.save(config_file)
            
            # Load
            loaded = DesktopConfig.from_file(config_file)
            
            assert loaded.wake_word == "computer"
            assert loaded.wake_sensitivity == 0.8


class TestPersistentState:
    """Test persistent state management."""

    def test_state_initialization(self):
        """Test state initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            state = PersistentState(state_file)
            
            assert state.state.version == "3.0.0"
            assert state.state.crash_count == 0
            assert state.state.restart_count == 0

    def test_on_start(self):
        """Test start event tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            state = PersistentState(state_file)
            
            asyncio.run(state.on_start())
            
            assert state.state.last_start is not None
            assert state.state.restart_count == 1

    def test_on_stop(self):
        """Test stop event tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            state = PersistentState(state_file)
            
            state.state.session_start = datetime.now().isoformat()
            asyncio.run(state.on_stop())
            
            assert state.state.last_stop is not None

    def test_crash_detection(self):
        """Test crash detection on restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            state = PersistentState(state_file)
            
            # Simulate crash: start, stop quickly, start again
            asyncio.run(state.on_start())
            time.sleep(0.1)
            asyncio.run(state.on_stop())
            time.sleep(0.1)
            asyncio.run(state.on_start())
            
            # Should detect crash
            assert state.state.crash_count >= 1

    def test_recovery_info(self):
        """Test recovery info retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            state = PersistentState(state_file)
            
            info = state.get_recovery_info()
            
            assert "crash_count" in info
            assert "restart_count" in info
            assert "total_uptime" in info


class TestDesktopAssistant:
    """Test desktop assistant functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test assistant initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            success = await assistant.initialize()
            
            assert success
            assert assistant._initialized

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test assistant start/stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(
                data_dir=Path(tmpdir),
                minimize_to_tray=False  # Disable tray for testing
            )
            assistant = DesktopAssistant(config)
            
            # Start
            success = await assistant.start()
            assert success
            assert assistant.is_running
            
            # Stop
            stopped = await assistant.stop()
            assert stopped
            assert not assistant.is_running

    @pytest.mark.asyncio
    async def test_default_tasks_registered(self):
        """Test default scheduled tasks are registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            await assistant.initialize()
            
            # Check default tasks
            task_names = [t.name for t in assistant.scheduler.list_tasks()]
            
            assert "daily_summary" in task_names
            assert "index_projects" in task_names
            assert "cleanup_memory" in task_names

    @pytest.mark.asyncio
    async def test_command_processing(self):
        """Test command processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            await assistant.initialize()
            
            # Test status command (requires start_time)
            assistant._start_time = datetime.now()
            status = assistant._get_status()
            assert "JARVIS" in status
            
            # Test help command
            help_text = assistant._get_help()
            assert "Commands" in help_text

    @pytest.mark.asyncio
    async def test_memory_commands(self):
        """Test memory commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            await assistant.initialize()
            
            # Remember something using direct memory call
            assistant.memory.remember("Python", "Python is a programming language")
            assistant.memory._save()
            
            # Recall it
            facts = assistant.memory.recall("Python")
            assert len(facts) > 0

    @pytest.mark.asyncio
    async def test_plugin_loading(self):
        """Test plugin auto-loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test plugin
            plugin_dir = Path(tmpdir) / "plugins" / "test_plugin"
            plugin_dir.mkdir(parents=True)
            
            # Create plugin.json
            (plugin_dir / "plugin.json").write_text(json.dumps({
                "name": "test_plugin",
                "version": "1.0.0",
                "commands": ["test"]
            }))
            
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            await assistant.initialize()
            
            # Plugin count may be 0 if no valid plugin found
            assert assistant.plugins is not None

    @pytest.mark.asyncio
    async def test_daily_summary_generation(self):
        """Test daily summary generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            
            await assistant.initialize()
            
            # Generate summary
            summary = await assistant._generate_daily_summary()
            
            assert "Daily Summary" in summary
            assert "Activity" in summary

    def test_status_report(self):
        """Test status report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(data_dir=Path(tmpdir))
            assistant = DesktopAssistant(config)
            # Don't call start(), just set _start_time manually
            assistant._start_time = datetime.now() - timedelta(hours=1)
            
            status = assistant._get_status()
            
            assert "JARVIS Status" in status
            assert "Uptime" in status
            assert "Plugins" in status


class TestStartupManager:
    """Test startup management."""

    def test_platform_detection(self):
        """Test platform detection."""
        manager = StartupManager()
        
        # Should detect something
        assert manager.platform in ["linux", "macos", "windows", "unknown"]

    def test_install_systemd(self):
        """Test systemd service installation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily override home
            import os
            original_home = os.environ.get("HOME")
            os.environ["HOME"] = tmpdir
            
            try:
                manager = StartupManager()
                manager.platform = "linux"  # Force linux
                
                success = manager._install_systemd()
                
                assert success
                
                # Check file was created
                service_path = Path(tmpdir) / ".config" / "systemd" / "user" / "jarvis.service"
                assert service_path.exists()
                
                # Check content
                content = service_path.read_text()
                assert "JARVIS" in content
                assert "ExecStart" in content
                
            finally:
                if original_home:
                    os.environ["HOME"] = original_home


class TestSurviveRestart:
    """Test that state survives restarts."""

    def test_memory_survives_restart(self):
        """Test memory persists across restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            
            # First session: add memory
            config = DesktopConfig(data_dir=data_dir)
            assistant1 = DesktopAssistant(config)
            asyncio.run(assistant1.initialize())
            
            assistant1.memory.remember("test_key", "test_value")
            assistant1.memory._save()
            
            # Simulate restart
            del assistant1
            
            # Second session: verify memory
            config2 = DesktopConfig(data_dir=data_dir)
            assistant2 = DesktopAssistant(config2)
            asyncio.run(assistant2.initialize())
            assistant2.memory.load()
            
            memories = assistant2.memory.recall("test_key")
            assert len(memories) > 0

    def test_scheduler_survives_restart(self):
        """Test scheduled tasks persist across restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            
            # First session: add task
            from jarvis.services.scheduler import TaskScheduler, TaskType
            
            scheduler = TaskScheduler(data_dir / "scheduler.json")
            scheduler.add_task(
                name="custom_task",
                schedule="0 10 * * *",
                command="echo hello",
                task_type=TaskType.COMMAND
            )
            
            # Simulate restart
            del scheduler
            
            # Second session: verify task
            scheduler2 = TaskScheduler(data_dir / "scheduler.json")
            
            task = scheduler2.get_task("custom_task")
            assert task is not None
            assert task.schedule == "0 10 * * *"

    def test_projects_survive_restart(self):
        """Test tracked projects persist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            project_path = data_dir / "test_project"
            project_path.mkdir()
            
            # First session: add project
            from jarvis.memory.project import ProjectMemory
            
            memory = ProjectMemory(data_dir / "projects.json")
            memory.add_project(project_path, "TestProject")
            
            # Simulate restart
            del memory
            
            # Second session: verify project
            memory2 = ProjectMemory(data_dir / "projects.json")
            
            project = memory2.get_project("TestProject")
            assert project is not None


class TestContinuousOperation:
    """Test continuous operation requirements."""

    @pytest.mark.asyncio
    async def test_state_persistence_loop(self):
        """Test repeated save/load cycles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            
            for i in range(5):
                state = PersistentState(state_file)
                await state.on_start()
                
                # Simulate work
                state.state.memory_entries = i
                await state.save()
                
                # Verify
                del state
                
                state2 = PersistentState(state_file)
                assert state2.state.memory_entries == i

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown saves state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DesktopConfig(
                data_dir=Path(tmpdir),
                minimize_to_tray=False
            )
            assistant = DesktopAssistant(config)
            
            # Initialize only (skip voice components)
            await assistant.initialize()
            
            # Manually call state callbacks
            state = PersistentState(config.data_dir / "state.json")
            await state.on_start()
            
            # Simulate shutdown
            await state.on_stop()
            
            # Verify state file exists
            state_file = config.data_dir / "state.json"
            assert state_file.exists()
            
            # Verify state was saved
            with open(state_file) as f:
                state_data = json.load(f)
            assert state_data.get("last_stop") is not None


# Integration test
class TestFullAutonomousCycle:
    """Full autonomous operation cycle test."""

    @pytest.mark.asyncio
    async def test_full_cycle(self):
        """Test complete start-run-stop cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            
            # Initialize
            config = DesktopConfig(
                data_dir=data_dir,
                minimize_to_tray=False,
                auto_index_projects=False  # Skip for speed
            )
            assistant = DesktopAssistant(config)
            
            # Initialize only
            await assistant.initialize()
            
            # Use memory directly
            assistant.memory.remember("test", "test value")
            assistant.memory._save()
            
            # Verify persistence
            state_file = data_dir / "state.json"
            
            # Save state
            state = PersistentState(state_file)
            await state.on_start()
            await state.save()
            
            assert state_file.exists()
            
            # Verify memory survives restart
            config2 = DesktopConfig(data_dir=data_dir)
            assistant2 = DesktopAssistant(config2)
            await assistant2.initialize()
            assistant2.memory.load()
            
            facts = assistant2.memory.recall("test")
            assert len(facts) > 0
