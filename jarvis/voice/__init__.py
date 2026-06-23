"""
Voice module for JARVIS - Speech-to-Text and Text-to-Speech.
"""

from jarvis.voice.audio import (
    AudioManager,
    AudioConfig,
    AudioLoopback,
    SpeechToText,
    TextToSpeech,
    VoiceAssistant,
)

__all__ = [
    "AudioManager",
    "AudioConfig",
    "AudioLoopback",
    "SpeechToText",
    "TextToSpeech",
    "VoiceAssistant",
]
