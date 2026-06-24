"""
Tests for Voice Router and Provider Management.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from jarvis.voice.voice_router import VoiceRouter, VoiceCommandProcessor
from jarvis.api.providers import (
    ProviderManager, OllamaProvider, GroqProvider,
    ProviderType, LLMConfig
)


class TestVoiceCommandProcessor:
    """Tests for VoiceCommandProcessor."""

    def test_parse_open_command(self):
        """Test parsing open app command."""
        intent, arg = VoiceCommandProcessor.parse_voice_command("hey jarvis open notepad")
        assert intent == "open_app"
        assert arg == "notepad"

    def test_parse_search_command(self):
        """Test parsing search command."""
        intent, arg = VoiceCommandProcessor.parse_voice_command("hey jarvis search python")
        assert intent == "web_search"
        assert arg == "python"

    def test_parse_ai_query(self):
        """Test parsing AI query."""
        intent, arg = VoiceCommandProcessor.parse_voice_command("hey jarvis what is machine learning")
        assert intent == "ai_query"

    def test_preprocess_voice_text(self):
        """Test voice text preprocessing."""
        text = VoiceCommandProcessor.preprocess_voice_text("Hey Jarvis open Chrome")
        assert "jarvis" not in text.lower()
        assert "open chrome" in text


class TestVoiceRouter:
    """Tests for VoiceRouter."""

    def test_init(self):
        """Test VoiceRouter initialization."""
        router = VoiceRouter()
        assert router.wake_word is not None
        assert router.state_machine is not None
        assert router.wake_word_enabled is True

    def test_init_without_wake_word(self):
        """Test VoiceRouter without wake word."""
        router = VoiceRouter(wake_word_enabled=False)
        assert router.wake_word_enabled is False


class TestProviderManager:
    """Tests for ProviderManager."""

    def test_init(self):
        """Test ProviderManager initialization."""
        manager = ProviderManager()
        assert manager.providers == {}
        assert manager.primary_provider is None

    def test_add_provider(self):
        """Test adding a provider."""
        manager = ProviderManager()
        config = LLMConfig(provider=ProviderType.GROQ, api_key="test")
        provider = GroqProvider(config)
        manager.add_provider(provider)
        assert ProviderType.GROQ in manager.providers

    def test_set_primary(self):
        """Test setting primary provider."""
        manager = ProviderManager()
        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        manager.add_provider(provider)
        manager.set_primary(ProviderType.OLLAMA)
        assert manager.primary_provider == ProviderType.OLLAMA

    def test_get_status(self):
        """Test getting provider status."""
        manager = ProviderManager()
        status = manager.get_status()
        assert "primary" in status
        assert "providers" in status

    def test_get_available_providers(self):
        """Test getting available providers."""
        manager = ProviderManager()
        available = manager.get_available_providers()
        assert isinstance(available, list)


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_init(self):
        """Test OllamaProvider initialization."""
        config = LLMConfig(provider=ProviderType.OLLAMA, model="llama3")
        provider = OllamaProvider(config)
        assert provider.model == "llama3"
        assert provider.base_url == "http://localhost:11434"

    def test_custom_base_url(self):
        """Test custom base URL."""
        config = LLMConfig(provider=ProviderType.OLLAMA, base_url="http://custom:11434")
        provider = OllamaProvider(config)
        assert provider.base_url == "http://custom:11434"


class TestGroqProvider:
    """Tests for GroqProvider."""

    def test_init(self):
        """Test GroqProvider initialization."""
        config = LLMConfig(provider=ProviderType.GROQ, api_key="test-key", model="llama-3.3-70b")
        provider = GroqProvider(config)
        assert provider.api_key == "test-key"
        assert provider.model == "llama-3.3-70b"


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_defaults(self):
        """Test default config values."""
        config = LLMConfig()
        assert config.provider == ProviderType.GROQ
        assert config.model == "llama-3.3-70b-versatile"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7

    def test_custom_values(self):
        """Test custom config values."""
        config = LLMConfig(
            provider=ProviderType.OLLAMA,
            model="custom-model",
            max_tokens=1000,
            temperature=0.5
        )
        assert config.provider == ProviderType.OLLAMA
        assert config.model == "custom-model"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
