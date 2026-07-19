"""
JARVIS UI application factory.

Wires the backend (agent, registry, plugin manager, provider manager, voice
runtime) together with the premium orchestration + UX layers. Keeps the
backend untouched — this module only *composes* existing pieces.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.activity import get_activity_center
from jarvis.events import EventType, get_event_bus
from jarvis.orchestrator import JarvisOrchestrator
from jarvis.palette import get_command_palette
from jarvis.suggestions import get_suggestion_engine
from jarvis.tasks import get_task_manager
from jarvis.tools_library import get_tool_library
from jarvis.ui.desktop_ui import DesktopUI

logger = logging.getLogger(__name__)


class JarvisApp:
    """
    Composition root for the premium UI.

    Holds the agent, orchestrator, and all UX services, and exposes helpers
    the web server uses. Construct with :func:`create_app`.
    """

    def __init__(self, agent: Any, api_key: str | None = None) -> None:
        self.agent = agent
        self.api_key = api_key
        self.bus = get_event_bus()
        self.orchestrator = JarvisOrchestrator(agent, bus=self.bus)
        self.tool_library = get_tool_library()
        self.palette = get_command_palette()
        self.suggestions = get_suggestion_engine()
        self.activity = get_activity_center()
        self.tasks = get_task_manager()
        self.desktop_ui = DesktopUI()

    async def initialize(self) -> None:
        """Lazy init: wire voice, register tools, start task scheduler."""
        try:
            from jarvis.ui.cli import JarvisCLI

            cli = JarvisCLI(agent=self.agent)
            cli.register_tools()
        except Exception as e:
            logger.debug(f"Tool registration skipped: {e}")

        self.tool_library.refresh()

        # Health-check the provider manager (registered in create_jarvis) so the
        # local Ollama runtime is selected as primary and reported by metrics.
        try:
            pm = getattr(self.agent, "provider_manager", None)
            if pm is not None:
                await pm.initialize()
        except Exception as e:
            logger.debug(f"Provider manager health check skipped: {e}")

        # Initialize voice runtime for TTS/status (non-fatal if unavailable)
        try:
            from jarvis.voice.voice_runtime import get_voice_runtime

            rt = get_voice_runtime()
            await rt.initialize()
            self.agent.set_speak_callback(lambda text: _speak(rt, text))

            # Wire voice interrupt to orchestrator for barge-in
            if hasattr(rt, "_interrupt_manager"):
                interrupt_event = asyncio.Event()
                self.orchestrator.set_interrupt_event(interrupt_event)
                rt._interrupt_manager._async_event = interrupt_event

            # Subscribe to voice state changes for UI updates
            self._bus.subscribe(EventType.VOICE_STATE, self._on_voice_state)
            self._bus.subscribe(EventType.VOICE_INTERRUPT, self._on_voice_interrupt)
            self._bus.subscribe(EventType.VOICE_TRANSCRIPT, self._on_voice_transcript)

            # Start push-to-talk if configured
            if rt.config.push_to_talk:
                asyncio.create_task(rt.start_push_to_talk())

        except Exception as e:
            logger.debug(f"Voice init skipped: {e}")

        await self.tasks.start()

    def _on_voice_state(self, event: Any) -> None:
        """Handle voice state changes."""
        data = event.data if hasattr(event, "data") else {}
        state = data.get("state", "")
        if state == "listening":
            self.desktop_ui.set_listening(True)
            self.desktop_ui.set_speaking(False)
        elif state in ("speaking", "tts_started", "playback_started"):
            self.desktop_ui.set_speaking(True)
            self.desktop_ui.set_listening(False)
        elif state in ("idle", "stopped", "playback_finished", "tts_finished"):
            self.desktop_ui.set_speaking(False)
            self.desktop_ui.set_listening(False)
        elif state == "user_speaking":
            self.desktop_ui.set_listening(True)

    def _on_voice_interrupt(self, event: Any) -> None:
        """Handle voice interrupt."""
        self.desktop_ui.set_speaking(False)
        self.desktop_ui.set_listening(True)

    def _on_voice_transcript(self, event: Any) -> None:
        """Handle voice transcript."""
        data = event.data if hasattr(event, "data") else {}
        text = data.get("text", "")
        if text and not data.get("partial", False):
            self.desktop_ui.add_message("user", text)

    async def process(self, text: str) -> str:
        """Process a user request through the orchestrator."""
        self.palette.add_history(text)
        return await self.orchestrator.process(text)

    async def shutdown(self) -> None:
        await self.tasks.stop()


def _speak(runtime: Any, text: str) -> None:
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(runtime.speak(text))
    except RuntimeError:
        pass


import asyncio  # noqa: E402  (placed after helper to keep utils first)


def create_app(api_key: str | None = None) -> JarvisApp:
    """
    Build a fully-wired premium JARVIS app.

    Args:
        api_key: Optional provider API key.

    Returns:
        JarvisApp ready for ``await app.initialize()``.
    """
    from jarvis.core.agent import create_jarvis

    agent = create_jarvis(api_key=api_key)
    return JarvisApp(agent, api_key=api_key)
