"""
Continuous listening for JARVIS.
Provides always-on voice command processing.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jarvis.voice.audio import AudioConfig, SpeechToText, TextToSpeech
from jarvis.voice.wake_word import VoiceStateMachine, WakeWordConfig, WakeWordEngine

logger = logging.getLogger(__name__)


@dataclass
class ListenerConfig:
    """Configuration for continuous listener."""

    wake_word: str = "jarvis"
    wake_sensitivity: float = 0.7
    silence_threshold: float = 3.0  # seconds of silence before processing
    command_timeout: float = 30.0  # max time to wait for command
    response_timeout: float = 10.0  # max time for TTS
    idle_timeout: float = 300.0  # seconds before entering sleep mode
    listen_on_start: bool = True
    greeting: str = "Yes?"
    activation_sound: bool = True


class ContinuousListener:
    """
    Continuous voice listener with wake word detection.
    Handles the full voice interaction pipeline.
    """

    def __init__(
        self,
        config: ListenerConfig | None = None,
        command_callback: Callable[[str], Any] | None = None,
    ):
        self.config = config or ListenerConfig()
        self.command_callback = command_callback

        # Initialize components
        wake_config = WakeWordConfig(
            word=self.config.wake_word, sensitivity=self.config.wake_sensitivity
        )
        audio_config = AudioConfig()

        self.wake_engine = WakeWordEngine(wake_config)
        self.stt = SpeechToText(audio_config)
        self.tts = TextToSpeech(audio_config)
        self.state = VoiceStateMachine()

        self._running = False
        self._listen_task: asyncio.Task | None = None
        self._state_task: asyncio.Task | None = None

    def set_command_callback(self, callback: Callable[[str], Any]) -> None:
        """Set the command processing callback."""
        self.command_callback = callback

    async def start(self) -> None:
        """Start continuous listening."""
        if self._running:
            logger.warning("Listener already running")
            return

        logger.info("Starting continuous listener...")

        self._running = True

        # Set up wake word callback
        self.wake_engine.set_wake_phrases(
            [
                self.config.wake_word,
                f"hey {self.config.wake_word}",
                f"{self.config.wake_word} are you there",
            ]
        )

        # Start wake word detection
        await self.wake_engine.start(self._on_wake_detected)

        # Start state management
        self._state_task = asyncio.create_task(self._state_manager())

        # Start listening loop
        self._listen_task = asyncio.create_task(self._listen_loop())

        logger.info("Continuous listener started")

    async def stop(self) -> None:
        """Stop continuous listening."""
        logger.info("Stopping continuous listener...")

        self._running = False

        # Cancel tasks
        if self._listen_task:
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task

        if self._state_task:
            self._state_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._state_task

        # Stop components
        await self.wake_engine.stop()
        self.stt.stop()

        logger.info("Continuous listener stopped")

    async def _on_wake_detected(self, phrase: str) -> None:
        """Called when wake word is detected."""
        logger.info(f"Wake word detected: {phrase}")

        # Wake up
        await self.state.wake()

        # Optional activation sound
        if self.config.activation_sound:
            await self._play_activation_sound()

        # Greet
        if self.config.greeting:
            await self.tts.speak(self.config.greeting, blocking=False)

    async def _play_activation_sound(self) -> None:
        """Play activation sound."""
        # In a full implementation, this would play an audio file
        logger.debug("Playing activation sound")

    async def _listen_loop(self) -> None:
        """Main listening loop."""
        while self._running:
            try:
                if self.state.is_listening:
                    # Listen for command
                    text = await self.stt.listen(timeout=self.config.command_timeout)

                    if text:
                        logger.info(f"Command heard: {text}")
                        await self.state.process()

                        # Process command
                        if self.command_callback:
                            response = await self._process_command(text)

                            # Respond
                            await self.state.respond()
                            if response:
                                await self.tts.speak(response, blocking=False)

                        await self.state.done()
                    else:
                        # No speech detected, return to idle
                        await self.state.done()
                else:
                    # Not listening, just sleep
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                await asyncio.sleep(1)

    async def _process_command(self, text: str) -> str:
        """Process voice command."""
        if not self.command_callback:
            return "Command handler not set"

        try:
            result = await self.command_callback(text)
            return str(result) if result else "Done"
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return "Sorry, I encountered an error"

    async def _state_manager(self) -> None:
        """Manage state transitions."""
        while self._running:
            try:
                idle_time = self.state.get_idle_time()

                # Check for sleep timeout
                if idle_time > self.config.idle_timeout and self.state.is_idle:
                    logger.info("Entering sleep mode due to inactivity")
                    await self.state.transition(self.state.SLEEPING)

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"State manager error: {e}")
                await asyncio.sleep(1)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_state(self) -> str:
        return self.state.state


class VoiceCommand:
    """Represents a parsed voice command."""

    def __init__(
        self,
        raw_text: str,
        intent: str = "",
        entities: dict[str, Any] = None,
        confidence: float = 1.0,
    ):
        self.raw_text = raw_text
        self.intent = intent
        self.entities = entities or {}
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"VoiceCommand(text={self.raw_text!r}, intent={self.intent!r})"


async def parse_voice_command(text: str) -> VoiceCommand:
    """
    Parse voice command into structured format.

    Simple keyword-based parsing.
    """
    text_lower = text.lower().strip()

    # Remove wake word if present
    wake_words = ["jarvis", "hey jarvis"]
    for ww in wake_words:
        if text_lower.startswith(ww):
            text_lower = text_lower[len(ww) :].strip()
            # Remove common connectors
            for conn in [",", ":", " please", " could you", " would you"]:
                if text_lower.startswith(conn):
                    text_lower = text_lower[len(conn) :].strip()

    # Simple intent detection
    intent = "general"
    entities = {}

    # Time-related commands
    if any(w in text_lower for w in ["what time", "current time", "time is it"]):
        intent = "time"
    elif any(w in text_lower for w in ["date", "what day", "today's date"]):
        intent = "date"

    # File operations
    elif any(w in text_lower for w in ["open", "create", "delete", "read", "write"]):
        intent = "file_operation"
        # Extract filename if quoted
        import re

        quotes = re.findall(r'"([^"]*)"', text_lower)
        if quotes:
            entities["filename"] = quotes[0]

    # Search
    elif any(w in text_lower for w in ["search", "find", "look up", "google"]):
        intent = "search"
        # Extract query
        for trigger in ["search for", "find", "look up", "google"]:
            if trigger in text_lower:
                entities["query"] = text_lower.split(trigger, 1)[1].strip()
                break

    # System commands
    elif any(w in text_lower for w in ["shutdown", "restart", "sleep", "wake"]):
        intent = "system"

    # Questions
    question_words = ("what", "how", "why", "when", "where", "who", "can you", "do you")
    if any(text_lower.startswith(w) for w in question_words):
        intent = "question"

    return VoiceCommand(
        raw_text=text,
        intent=intent,
        entities=entities,
        confidence=0.8,  # Placeholder
    )


async def handle_voice_command(command: VoiceCommand, jarvis: Any = None) -> str:
    """
    Handle parsed voice command.

    Returns response text.
    """
    intent = command.intent

    if intent == "time":
        from datetime import datetime

        return f"The current time is {datetime.now().strftime('%I:%M %p')}"

    elif intent == "date":
        from datetime import datetime

        return f"Today's date is {datetime.now().strftime('%B %d, %Y')}"

    elif intent == "file_operation":
        if jarvis:
            result = await jarvis.process_command(command.raw_text)
            return result or "File operation completed"
        return "File operation not available"

    elif intent == "search":
        if jarvis:
            query = command.entities.get("query", command.raw_text)
            result = await jarvis.process_command(f"search for {query}")
            return result or "Search completed"
        return "Search not available"

    elif intent == "system":
        if "sleep" in command.raw_text.lower():
            return "Going to sleep mode. Say my name to wake me."
        elif "shutdown" in command.raw_text.lower():
            return "Shutting down. Goodbye!"
        return "System command acknowledged"

    elif intent == "question":
        if jarvis:
            result = await jarvis.process_command(command.raw_text)
            return result or "I don't have an answer for that"
        return "Question processing not available"

    else:
        if jarvis:
            result = await jarvis.process_command(command.raw_text)
            return result or "Done"
        return "Command received"
