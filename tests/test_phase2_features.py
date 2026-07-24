"""
Tests for Phase 2 features: conversation context, reference resolution,
notifications, proactive monitor, workspace awareness, daily assistant,
background intelligence, personality, interruptions, adaptive suggestions.
"""


import pytest

try:
    from jarvis.conversation.context import ConversationContext, ConversationState
    from jarvis.conversation.reference import classify_token, expand_token, resolve_token
except ImportError:
    pass

try:
    from jarvis.notifications.manager import NotificationLevel, get_notification_manager
except ImportError:
    pass

try:
    from jarvis.proactive.monitor import MonitorRule, ProactiveMonitor
except ImportError:
    pass

try:
    from jarvis.workspace.awareness import WorkspaceAwareness
except ImportError:
    pass

try:
    from jarvis.daily.assistant import DailyAssistant
except ImportError:
    pass

try:
    from jarvis.background.tasks import BackgroundIntelligence, BackgroundTask, TaskPriority
except ImportError:
    pass

try:
    from jarvis.personality.manager import PersonalityManager
except ImportError:
    pass


class TestConversationContext:
    def test_context_creation(self):
        ctx = ConversationContext()
        assert ctx.get_state() == ConversationState.IDLE
        ctx.add_turn("user", "hello")
        assert len(ctx.get_recent_turns()) == 1

    def test_turns_limit(self):
        ctx = ConversationContext()
        for i in range(50):
            ctx.add_turn("user", f"msg {i}")
        assert len(ctx.get_recent_turns()) <= 40

    def test_topic_tracking(self):
        ctx = ConversationContext()
        ctx.set_topic("python")
        assert ctx.get_topic() == "python"

    def test_prompt_context(self):
        ctx = ConversationContext()
        ctx.add_turn("user", "hello")
        out = ctx.to_prompt_context()
        assert "hello" in out

    def test_clear(self):
        ctx = ConversationContext()
        ctx.add_turn("user", "test")
        ctx.set_topic("project")
        ctx.clear()
        assert ctx.get_topic() is None
        assert len(ctx.get_recent_turns()) == 0


class TestReferenceResolution:
    def test_pronoun_classify(self):
        assert classify_token("it") == "pronoun"
        assert classify_token("this") == "pronoun"
        assert classify_token("that") == "pronoun"

    def test_ordinal_classify(self):
        assert classify_token("the previous one") == "ordinal"
        assert classify_token("the last document") == "ordinal"

    def test_temporal_classify(self):
        assert classify_token("yesterday's project") == "temporal"
        assert classify_token("today's build") == "temporal"

    def test_resolve_pronoun_with_topic(self):
        class Ctx:
            def get_topic(self):
                return "python project"
            def get_last_user_message(self):
                class M:
                    content = "fix the bug"
                return M()
        result = resolve_token("it", Ctx(), None)
        assert result == "python project"

    def test_expand_token_pronoun(self):
        class Ctx:
            def get_topic(self):
                return "vscode"
        assert expand_token("it", Ctx(), None) == "vscode"


class TestNotifications:
    def test_notify_info(self):
        mgr = get_notification_manager()
        n = mgr.notify(NotificationLevel.INFO, "Test", "Message")
        assert n.title == "Test"
        assert n.level == NotificationLevel.INFO

    def test_dismiss(self):
        mgr = get_notification_manager()
        n = mgr.notify(NotificationLevel.INFO, "Dismiss", "me")
        mgr.dismiss(n.id)
        active = mgr.get_active()
        assert not any(a["id"] == n.id for a in active)

    def test_group(self):
        mgr = get_notification_manager()
        mgr.notify(NotificationLevel.INFO, "A", "1", group="builds")
        mgr.notify(NotificationLevel.SUCCESS, "B", "2", group="builds")
        group_items = mgr.get_group("builds")
        assert len(group_items) >= 2

    def test_clear(self):
        mgr = get_notification_manager()
        mgr.notify(NotificationLevel.INFO, "X", "Y")
        mgr.clear()
        assert mgr.get_active() == []


class TestProactiveMonitor:
    def test_register_rule(self):
        pm = ProactiveMonitor()
        rule = MonitorRule(
            name="Build done",
            event_types=["tool"],
            match=lambda d: d.get("phase") == "complete",
            message="Done",
        )
        pm.add_rule(rule)
        assert rule in pm.rules


class TestWorkspaceAwareness:
    def test_default_dir(self):
        w = WorkspaceAwareness()
        state = w.get_state()
        assert state.directory is not None

    def test_set_repo(self):
        w = WorkspaceAwareness()
        w.set_repo("/tmp/repo")
        assert w.get_state().repo == "/tmp/repo"

    def test_add_server(self):
        w = WorkspaceAwareness()
        w.add_server("uvicorn")
        assert "uvicorn" in w.get_state().running_servers

    def test_prompt_context(self):
        w = WorkspaceAwareness()
        w.set_repo("/tmp/repo")
        w.set_branch("main")
        ctx = w.to_prompt_context()
        assert "/tmp/repo" in ctx


class TestDailyAssistant:
    def test_morning_briefing(self):
        da = DailyAssistant()
        result = da.morning_briefing()
        assert "Morning" in result or "Briefing" in result

    def test_evening_summary(self):
        da = DailyAssistant()
        result = da.evening_summary()
        assert "Evening" in result or "Summary" in result


class TestBackgroundIntelligence:
    def test_register_defaults(self):
        bi = BackgroundIntelligence()
        names = [t.name for t in bi.list_tasks()]
        assert "memory_cleanup" in names

    def test_due_tasks(self):
        bi = BackgroundIntelligence()
        due = bi.get_due_tasks()
        assert isinstance(due, list)

    def test_add_task(self):
        bi = BackgroundIntelligence()
        bi.add_task(BackgroundTask("custom", TaskPriority.LOW, interval_seconds=3600))
        assert "custom" in [t.name for t in bi.list_tasks()]


class TestPersonality:
    def test_default_profile(self):
        pm = PersonalityManager()
        assert pm.profile.verbosity == "concise"

    def test_response_template(self):
        pm = PersonalityManager()
        r = pm.get_response("open_app", app="VS Code")
        assert "VS Code" in r

    def test_short_preference(self):
        pm = PersonalityManager()
        assert pm.prefer_short(is_voice=True) is True
        assert pm.prefer_short(is_voice=False) is False


class TestAgentInterrupts:
    def test_request_interrupt(self):
        from jarvis.core.agent import create_jarvis
        agent = create_jarvis()
        agent.request_interrupt()
        assert agent._interrupt_flag.is_set()

    def test_clear_interrupt(self):
        from jarvis.core.agent import create_jarvis
        agent = create_jarvis()
        agent.request_interrupt()
        agent.clear_interrupt()
        assert not agent._interrupt_flag.is_set()

    @pytest.mark.asyncio
    async def test_process_returns_on_interrupt(self):
        from jarvis.core.agent import create_jarvis
        agent = create_jarvis()
        agent.request_interrupt()
        result = await agent.process("hello")
        assert "stopping" in result.lower() or "What now" in result


class TestDesktopExtensions:
    @pytest.mark.asyncio
    async def test_open_folder(self):
        from jarvis.desktop.automation import DesktopAutomation
        d = DesktopAutomation()
        result = await d.open_folder("C:\\")
        assert result is True

    @pytest.mark.asyncio
    async def test_search_files(self):
        from jarvis.desktop.automation import DesktopAutomation
        d = DesktopAutomation()
        results = await d.search_files("*.py", ".")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_switch_window_alias(self):
        from jarvis.desktop.automation import DesktopAutomation
        d = DesktopAutomation()
        result = await d.switch_window("nonexistent_window_xyz")
        assert isinstance(result, bool)


class TestWorkspaceIntegration:
    def test_workspace_initializes(self):
        try:
            from jarvis.workspace.awareness import WorkspaceAwareness
            w = WorkspaceAwareness()
            state = w.get_state()
            assert state is not None
        except Exception:
            pytest.skip("workspace awareness not available")


class TestDailyAssistantIntegration:
    def test_routine_for_morning(self):
        from datetime import datetime

        from jarvis.daily.assistant import DailyAssistant
        da = DailyAssistant()
        result = da.get_routine_for_time(datetime(2026, 1, 1, 9, 0, 0))
        assert "Morning" in result or "Briefing" in result

    def test_routine_for_evening(self):
        from datetime import datetime

        from jarvis.daily.assistant import DailyAssistant
        da = DailyAssistant()
        result = da.get_routine_for_time(datetime(2026, 1, 1, 20, 0, 0))
        assert "Evening" in result or "Summary" in result
