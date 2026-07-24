"""
Tests for Voice Router and Provider Management.
"""

import pytest

from jarvis.api.providers import (
    GroqProvider,
    LLMConfig,
    OllamaProvider,
    ProviderManager,
    ProviderType,
)
from jarvis.voice.voice_router import VoiceCommandProcessor, VoiceRouter


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
        intent, arg = VoiceCommandProcessor.parse_voice_command(
            "hey jarvis what is machine learning"
        )
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
        assert manager._initialized is False

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

    def test_format_status(self):
        """Test formatting provider status."""
        manager = ProviderManager()
        config = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        provider._available = True
        manager.primary_provider = ProviderType.OLLAMA

        manager.add_provider(provider)

        status = manager.format_status()
        assert "Ollama" in status or "OLLAMA" in status
        assert "qwen3:8b" in status

    def test_format_models(self):
        """Test formatting models list."""
        manager = ProviderManager()
        config = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        manager.add_provider(provider)

        models = manager.format_models()
        assert "qwen3:8b" in models
        assert "deepseek-r1:8b" in models

    def test_provider_priority(self):
        """Test provider priority order."""
        assert ProviderType.OLLAMA in ProviderManager.PROVIDER_PRIORITY
        assert ProviderType.AIRLLM in ProviderManager.PROVIDER_PRIORITY
        assert ProviderType.GROQ in ProviderManager.PROVIDER_PRIORITY
        # Ollama should be first, AirLLM last (GPU-only)
        assert ProviderManager.PROVIDER_PRIORITY[0] == ProviderType.OLLAMA
        assert ProviderManager.PROVIDER_PRIORITY[-1] == ProviderType.AIRLLM

    def test_default_model(self):
        """Test default model configuration."""
        assert ProviderManager.DEFAULT_MODEL == "qwen3:8b"

    def test_reasoning_model(self):
        """Test reasoning model configuration."""
        assert ProviderManager.REASONING_MODEL == "deepseek-r1:8b"


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

    def test_available_models_initially_empty(self):
        """Test that available_models is empty on init."""
        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        assert provider.available_models == []

    def test_default_model_qwen(self):
        """Test default model is qwen3:8b."""
        config = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        provider = OllamaProvider(config)
        assert provider.model == "qwen3:8b"


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
        assert config.model is None
        assert config.max_tokens == 4096
        assert config.temperature == 0.7

    def test_custom_values(self):
        """Test custom config values."""
        config = LLMConfig(
            provider=ProviderType.OLLAMA, model="custom-model", max_tokens=1000, temperature=0.5
        )
        assert config.provider == ProviderType.OLLAMA
        assert config.model == "custom-model"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5


class TestProviderSelection:
    """Tests for provider selection logic."""

    def test_ollama_priority_over_groq(self):
        """Test that Ollama is prioritized over Groq."""
        assert ProviderManager.PROVIDER_PRIORITY[0] == ProviderType.OLLAMA
        assert ProviderManager.PROVIDER_PRIORITY[-1] == ProviderType.AIRLLM
        assert ProviderType.GROQ in ProviderManager.PROVIDER_PRIORITY

    def test_startup_diagnostics_initialization(self):
        """Test startup diagnostics are initialized."""
        manager = ProviderManager()
        assert manager._startup_diagnostics == {}


class TestIntelligentModelRouting:
    """Tests for intelligent model routing."""

    def test_reasoning_pattern_detection(self):
        """Test reasoning patterns are defined."""
        assert len(ProviderManager.REASONING_PATTERNS) > 0
        assert any("step by step" in p for p in ProviderManager.REASONING_PATTERNS)

    def test_get_best_model_for_task_reasoning(self):
        """Test reasoning task routing."""
        manager = ProviderManager()

        # Add mock Ollama provider
        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        manager.add_provider(provider)

        # Test reasoning task
        model = manager.get_best_model_for_task("Solve this step by step")
        assert "deepseek" in model.lower()

    def test_get_best_model_for_task_general(self):
        """Test general task routing."""
        manager = ProviderManager()

        # Add mock Ollama provider
        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        manager.add_provider(provider)

        # Test general task
        model = manager.get_best_model_for_task("What is Python?")
        assert "qwen" in model.lower() or "llama" in model.lower()


class TestModelSwitching:
    """Tests for model switching functionality."""

    def test_set_model_ollama(self):
        """Test switching to Ollama model."""
        manager = ProviderManager()

        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        manager.add_provider(provider)

        success, model = manager.set_model("qwen3")
        assert success is True
        assert model == "qwen3:8b"
        assert manager.primary_provider == ProviderType.OLLAMA

    def test_set_model_normalizes_name(self):
        """Test model name normalization."""
        manager = ProviderManager()

        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b"]
        manager.add_provider(provider)

        success, model = manager.set_model("qwen3")
        assert success is True
        assert model == "qwen3:8b"
        assert provider.model == "qwen3:8b"

    def test_get_current_model(self):
        """Test getting current model."""
        manager = ProviderManager()
        manager.primary_provider = ProviderType.OLLAMA

        config = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        provider = OllamaProvider(config)
        manager.add_provider(provider)

        assert manager.get_current_model() == "qwen3:8b"


class TestBenchmarkAndCompare:
    """Tests for benchmark and comparison features."""

    def test_compare_models(self):
        """Test model comparison."""
        manager = ProviderManager()

        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = OllamaProvider(config)
        provider._available_models = ["qwen3:8b", "deepseek-r1:8b"]
        manager.add_provider(provider)

        result = manager.compare_models("qwen3:8b", "deepseek-r1:8b")
        assert "qwen3" in result
        assert "deepseek" in result


class TestProviderFallback:
    """Tests for provider fallback logic."""

    def test_fallback_order(self):
        """Test fallback order is correct."""
        priority = ProviderManager.PROVIDER_PRIORITY
        assert priority[0] == ProviderType.OLLAMA  # Ollama first (general-purpose local)
        assert priority[-1] == ProviderType.AIRLLM  # AirLLM last (GPU-only memory-efficient)
        assert ProviderType.GROQ in priority  # Cloud fallback

    def test_provider_manager_has_generate(self):
        """Test ProviderManager has generate method."""
        manager = ProviderManager()
        assert hasattr(manager, "generate")
        assert hasattr(manager, "stream_generate")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
