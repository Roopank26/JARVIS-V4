"""
API module for JARVIS.
Supports Groq (primary) and Gemini (legacy fallback).
"""

from jarvis.api.gemini import (
    GeminiClient,  # Alias for backward compatibility
    GroqClient,
    SimpleLLMClient,
)

__all__ = ["GeminiClient", "GroqClient", "SimpleLLMClient"]
