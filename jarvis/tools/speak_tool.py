"""
JARVIS Speak Tool
=================
Registers TTS capability in the ToolRegistry by wrapping the EXISTING
VoiceRuntime and its speak callback.

Design rules (DO NOT VIOLATE):
- NEVER create a new TTS engine
- NEVER duplicate pyttsx3, gTTS, Piper, espeak logic
- ONLY delegate to what VoiceRuntime already has
- If VoiceRuntime is unavailable, fall back through the callback chain
  that agent.py already maintains via set_speak_callback()

Resolution order (all from existing code):
  1. agent._speak_callback  (set by the UI / voice router)
  2. VoiceRuntime.speak()   (Piper → pyttsx3 → gTTS chain in voice_runtime.py)
  3. OS TTS command         (platform speak / espeak / say — last resort)
"""

from __future__ import annotations

import asyncio
import logging
import platform
from typing import Any

from jarvis.tools.base import PermissionLevel, ReadOnlyTool, ToolResult

logger = logging.getLogger(__name__)


class SpeakTool(ReadOnlyTool):
    """
    Converts text to speech using the JARVIS voice runtime.

    The tool stores an optional callback (injected by JarvisAgent) which is
    the same callback used everywhere else in the system. This ensures a
    single consistent TTS path.
    """

    name: str = "speak"
    description: str = (
        "Speak text aloud using the voice system. "
        "Use when the user asks JARVIS to talk, say something, read aloud, "
        "or any request involving audio/voice output."
    )
    permission_level = PermissionLevel.AUTOMATIC

    # Keywords used by CapabilityRouter for intent matching
    KEYWORDS = [
        "speak", "say", "talk", "voice", "aloud", "read", "tell",
        "audio", "listen", "hear", "sound", "tts", "speech",
    ]

    @property
    def category(self) -> str:
        return "voice"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to speak aloud",
                },
            },
            "required": ["text"],
        }

    def __init__(self, speak_callback=None) -> None:
        super().__init__()
        self._speak_callback = speak_callback
        # Lazily resolved VoiceRuntime
        self._runtime = None
        self._runtime_checked = False

    def set_speak_callback(self, callback) -> None:
        """Update the speak callback (called by JarvisAgent)."""
        self._speak_callback = callback

    def _get_runtime(self):
        """Try to get the global VoiceRuntime (lazy, cached)."""
        if self._runtime_checked:
            return self._runtime
        self._runtime_checked = True
        try:
            from jarvis.voice.voice_runtime import get_voice_runtime
            self._runtime = get_voice_runtime()
        except Exception:
            self._runtime = None
        return self._runtime

    async def execute(
        self, input_data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        text = input_data.get("text", "").strip()
        if not text:
            return ToolResult(success=False, output=None, error="No text provided to speak")

        logger.debug("[Executor] SpeakTool executing: %r", text[:60])

        # ── Path 1: agent speak callback (already wired in the whole system) ──
        if self._speak_callback is not None:
            try:
                result = self._speak_callback(text)
                if asyncio.iscoroutine(result):
                    await result
                logger.info("[Success] SpeakTool: spoken via callback")
                return ToolResult(success=True, output=f"Spoken: {text}")
            except Exception as e:
                logger.warning("[SpeakTool] callback failed: %s", e)

        # ── Path 2: VoiceRuntime.speak() — uses Piper/pyttsx3/gTTS chain ──
        runtime = self._get_runtime()
        if runtime is not None:
            try:
                spoken = await runtime.speak(text)
                if spoken:
                    logger.info("[Success] SpeakTool: spoken via VoiceRuntime")
                    return ToolResult(success=True, output=f"Spoken: {text}")
            except Exception as e:
                logger.warning("[SpeakTool] VoiceRuntime.speak() failed: %s", e)

        # ── Path 3: OS-level TTS fallback (existing platform commands) ──
        try:
            await self._os_speak(text)
            logger.info("[Success] SpeakTool: spoken via OS command")
            return ToolResult(success=True, output=f"Spoken (OS TTS): {text}")
        except Exception as e:
            logger.error("[Failure] SpeakTool: all TTS paths failed: %s", e)
            return ToolResult(
                success=False,
                output=None,
                error=(
                    "Voice output unavailable. "
                    "Install pyttsx3 (`pip install pyttsx3`) or "
                    "configure the Piper TTS server to enable speech."
                ),
            )

    async def _os_speak(self, text: str) -> None:
        """Attempt OS-native TTS as absolute last resort."""
        system = platform.system()
        clean_text = text.replace("'", "").replace('"', "").replace("\n", " ")
        if system == "Windows":
            # PowerShell's built-in SpeechSynthesizer
            script = (
                f"Add-Type -AssemblyName System.speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{clean_text}');"
            )
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-NonInteractive", "-Command", script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        elif system == "Darwin":
            proc = await asyncio.create_subprocess_exec(
                "say", clean_text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        else:
            # Linux: espeak
            proc = await asyncio.create_subprocess_exec(
                "espeak", "-v", "en", clean_text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()


    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        text = input_data.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return False, "Parameter 'text' must be a non-empty string"
        return True, None
