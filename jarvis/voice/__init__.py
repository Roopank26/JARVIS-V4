"""
Voice module for JARVIS - Speech-to-Text and Text-to-Speech.
"""

from jarvis.voice.audio import (
    AudioConfig,
    AudioLoopback,
    AudioManager,
    SpeechToText,
    TextToSpeech,
    VoiceAssistant,
)
from jarvis.voice.fish_audio_tts import FishAudioConfig, FishAudioTTS, TTSProvider

__all__ = [
    "AudioConfig",
    "AudioLoopback",
    "AudioManager",
    "FishAudioConfig",
    "FishAudioTTS",
    "SpeechToText",
    "TextToSpeech",
    "TTSProvider",
    "VoiceAssistant",
]
