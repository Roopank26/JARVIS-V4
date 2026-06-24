"""
API module for JARVIS.
Supports Groq (primary) and Gemini (legacy fallback).
"""

from jarvis.api.gemini import (
    GroqClient,
    GeminiClient,  # Alias for backward compatibility
    SimpleLLMClient
)

__all__ = ["GroqClient", "GeminiClient", "SimpleLLMClient"]
