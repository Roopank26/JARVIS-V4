"""
Voice Router - Orchestrates the voice pipeline.
Wake Word → STT → Intent Classification → Agent → TTS
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
from pathlib import Path

from jarvis.voice.wake_word import WakeWordEngine, WakeWordConfig, VoiceStateMachine
from jarvis.voice.audio import AudioConfig
from jarvis.core.agent import JarvisAgent, classify_intent, Intent

logger = logging.getLogger(__name__)


class VoiceRouter:
    """
    Orchestrates the complete voice pipeline.
    
    Flow:
    1. Wake word detection (WakeWordEngine)
    2. Speech-to-Text (SpeechToText)
    3. Intent Classification (existing classify_intent)
    4. Agent Processing (JarvisAgent)
    5. Text-to-Speech (TextToSpeech)
    """

    def __init__(
        self,
        agent: Optional[JarvisAgent] = None,
        wake_word_enabled: bool = True,
        tts_enabled: bool = True,
        stt_enabled: bool = True
    ):
        self.agent = agent
        self.wake_word = WakeWordEngine()
        self.state_machine = VoiceStateMachine()
        self.stt = None
        self.tts = None
        
        # Pipeline settings
        self.wake_word_enabled = wake_word_enabled
        self.tts_enabled = tts_enabled
        self.stt_enabled = stt_enabled
        
        # Callbacks
        self._on_wake_word: Optional[Callable] = None
        self._on_transcription: Optional[Callable] = None
        self._on_response: Optional[Callable] = None
        
        # Task management
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize voice components."""
        # Initialize STT
        if self.stt_enabled:
            try:
                from jarvis.voice.audio import SpeechToText
                self.stt = SpeechToText()
                logger.info("STT initialized")
            except Exception as e:
                logger.warning(f"STT initialization failed: {e}")
                self.stt_enabled = False
        
        # Initialize TTS
        if self.tts_enabled:
            try:
                from jarvis.voice.audio import TextToSpeech
                self.tts = TextToSpeech()
                logger.info("TTS initialized")
            except Exception as e:
                logger.warning(f"TTS initialization failed: {e}")
                self.tts_enabled = False

    async def start(self) -> None:
        """Start the voice router."""
        if self._running:
            logger.warning("Voice router already running")
            return
        
        await self.initialize()
        self._running = True
        
        if self.wake_word_enabled:
            await self.wake_word.start(self._on_wake_detected)
            logger.info("Voice router started with wake word")
        else:
            # Start direct listening without wake word
            self._listen_task = asyncio.create_task(self._continuous_listen())
            logger.info("Voice router started in direct mode")
    
    async def stop(self) -> None:
        """Stop the voice router."""
        self._running = False
        
        if self.wake_word_enabled:
            await self.wake_word.stop()
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Voice router stopped")

    async def _on_wake_detected(self, phrase: str) -> None:
        """Handle wake word detection."""
        logger.info(f"Wake word detected: {phrase}")
        
        if self._on_wake_word:
            self._on_wake_word(phrase)
        
        # Start listening for command
        await self.state_machine.transition("listening")
        await self._listen_for_command()

    async def _continuous_listen(self) -> None:
        """Continuously listen for commands without wake word."""
        while self._running:
            await self._listen_for_command()
            await asyncio.sleep(0.5)

    async def _listen_for_command(self) -> None:
        """Listen for a voice command and process it."""
        if not self.stt:
            logger.warning("STT not available")
            return
        
        try:
            # Listen for speech
            await self.state_machine.transition("listening")
            
            if self.stt_enabled:
                text = await self.stt.listen(timeout=10.0)
            else:
                # Simulation mode
                text = None
            
            if text:
                logger.info(f"Transcribed: {text}")
                
                if self._on_transcription:
                    self._on_transcription(text)
                
                # Process through agent
                await self.state_machine.transition("processing")
                response = await self.agent.process(text)
                
                # Speak response
                await self.state_machine.transition("responding")
                await self._speak(response)
                
                if self._on_response:
                    self._on_response(response)
            else:
                logger.debug("No speech detected")
            
            await self.state_machine.transition("idle")
            
        except Exception as e:
            logger.error(f"Error in voice command processing: {e}")
            await self.state_machine.transition("idle")

    async def _speak(self, text: str) -> None:
        """Speak text using TTS."""
        if not self.tts or not self.tts_enabled:
            logger.debug(f"TTS disabled, would speak: {text[:50]}...")
            return
        
        try:
            await self.tts.speak(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")

    async def speak(self, text: str) -> None:
        """Public method to speak text."""
        await self._speak(text)

    def set_wake_word_callback(self, callback: Callable) -> None:
        """Set callback for wake word detection."""
        self._on_wake_word = callback

    def set_transcription_callback(self, callback: Callable) -> None:
        """Set callback for transcription."""
        self._on_transcription = callback

    def set_response_callback(self, callback: Callable) -> None:
        """Set callback for response."""
        self._on_response = callback


class VoiceCommandProcessor:
    """
    Process voice commands with intent routing.
    Extends the existing intent classification for voice commands.
    """

    # Voice-specific command patterns
    VOICE_COMMANDS = {
        # Quick actions
        r"(?:hey\s+)?jarvis\s+(open|launch|start)\s+(.+)": "open_app",
        r"(?:hey\s+)?jarvis\s+(close|quit|exit)\s+(.+)": "close_app",
        r"(?:hey\s+)?jarvis\s+(search|google)\s+(.+)": "web_search",
        r"(?:hey\s+)?jarvis\s+(play|pause|stop)\s*(.*)": "media_control",
        
        # System commands
        r"(?:hey\s+)?jarvis\s+(take a note|remind me|remember)": "note_taking",
        r"(?:hey\s+)?jarvis\s+(what time|what's the time)": "time_query",
        r"(?:hey\s+)?jarvis\s+(weather|temperature)": "weather_query",
        
        # AI queries
        r"(?:hey\s+)?jarvis\s+(what is|who is|how to|tell me about)": "ai_query",
        r"(?:hey\s+)?jarvis\s+(explain|define)": "ai_query",
    }

    @classmethod
    def parse_voice_command(cls, text: str) -> tuple[str, Optional[str]]:
        """
        Parse a voice command and return (intent, extracted_arg).
        
        Returns:
            Tuple of (intent_type, extracted_argument)
        """
        text_lower = text.lower().strip()
        
        for pattern, intent in cls.VOICE_COMMANDS.items():
            import re
            match = re.search(pattern, text_lower)
            if match:
                arg = match.group(2) if len(match.groups()) > 1 else None
                return intent, arg
        
        return "unknown", None

    @classmethod
    def preprocess_voice_text(cls, text: str) -> str:
        """
        Preprocess voice transcription for better recognition.
        
        - Remove filler words
        - Fix common misrecognitions
        - Normalize formatting
        """
        # Remove "hey jarvis" prefix
        text = text.lower()
        text = text.replace("hey jarvis", "").replace("hey computer", "")
        text = text.strip()
        
        # Common corrections
        corrections = {
            "open ": "open ",
            "close ": "close ",
            "search ": "search ",
            "what is": "what is",
            "who is": "who is",
        }
        
        return text


# Global voice router instance
_voice_router: Optional[VoiceRouter] = None


def get_voice_router() -> VoiceRouter:
    """Get the global voice router instance."""
    global _voice_router
    if _voice_router is None:
        _voice_router = VoiceRouter()
    return _voice_router


def init_voice_router(agent: JarvisAgent, **kwargs) -> VoiceRouter:
    """Initialize the global voice router with an agent."""
    global _voice_router
    _voice_router = VoiceRouter(agent=agent, **kwargs)
    return _voice_router
