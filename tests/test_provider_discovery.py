"""
Tests for dynamic provider discovery, model auto-detection, and failover.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from jarvis.api.providers import (
    ProviderManager,
    OllamaProvider,
    GroqProvider,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    ProviderType,
    LLMConfig,
    LLMResponse,
)


def _make_ollama(models=None, available=True):
    cfg = LLMConfig(provider=ProviderType.OLLAMA, model=models[0] if models else None)
    p = OllamaProvider(cfg)
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


def _make_groq(models=None, available=True, api_key="test"):
    cfg = LLMConfig(provider=ProviderType.GROQ, api_key=api_key, model=models[0] if models else None)
    p = GroqProvider(cfg)
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


def _make_openai(models=None, available=True, api_key="test"):
    cfg = LLMConfig(provider=ProviderType.OPENAI, api_key=api_key, model=models[0] if models else None)
    p = OpenAIProvider(cfg)
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


def _make_google(models=None, available=True, api_key="test"):
    cfg = LLMConfig(provider=ProviderType.GOOGLE, api_key=api_key, model=models[0] if models else None)
    p = GoogleProvider(cfg)
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


def _make_anthropic(models=None, available=True, api_key="test"):
    cfg = LLMConfig(provider=ProviderType.ANTHROPIC, api_key=api_key, model=models[0] if models else None)
    p = AnthropicProvider(cfg)
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


class TestProviderDiscovery:
    def test_priority_order(self):
        assert ProviderManager.PROVIDER_PRIORITY == [
            ProviderType.OLLAMA,
            ProviderType.GROQ,
            ProviderType.OPENAI,
            ProviderType.GOOGLE,
            ProviderType.ANTHROPIC,
        ]

    def test_fallback_order(self):
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.OLLAMA] == ProviderType.GROQ
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.GROQ] == ProviderType.OPENAI
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.OPENAI] == ProviderType.GOOGLE
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.GOOGLE] == ProviderType.ANTHROPIC
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.ANTHROPIC] is None

    def test_add_all_provider_types(self):
        manager = ProviderManager()
        manager.add_provider(_make_ollama(["qwen3:8b"]))
        manager.add_provider(_make_groq(["llama-3.3-70b-versatile"]))
        manager.add_provider(_make_openai(["gpt-4o"]))
        manager.add_provider(_make_google(["gemini-2.0-flash"]))
        manager.add_provider(_make_anthropic(["claude-3-5-sonnet-20240620"]))
        assert len(manager.providers) == 5
        assert set(manager.providers.keys()) == {
            ProviderType.OLLAMA,
            ProviderType.GROQ,
            ProviderType.OPENAI,
            ProviderType.GOOGLE,
            ProviderType.ANTHROPIC,
        }


class TestDynamicModelDiscovery:
    def test_ollama_auto_select_first_model(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b", "deepseek-r1:8b"])
        manager.add_provider(ollama)
        manager.primary_provider = ProviderType.OLLAMA
        assert manager.get_current_model() == "qwen3:8b"

    def test_groq_auto_select_first_model(self):
        manager = ProviderManager()
        groq = _make_groq(["llama-3.3-70b-versatile", "mixtral-8x7b-32768"])
        manager.add_provider(groq)
        manager.primary_provider = ProviderType.GROQ
        assert manager.get_current_model() == "llama-3.3-70b-versatile"

    def test_openai_auto_select_first_model(self):
        manager = ProviderManager()
        openai = _make_openai(["gpt-4o", "gpt-4o-mini"])
        manager.add_provider(openai)
        manager.primary_provider = ProviderType.OPENAI
        assert manager.get_current_model() == "gpt-4o"

    def test_google_auto_select_first_model(self):
        manager = ProviderManager()
        google = _make_google(["gemini-2.0-flash", "gemini-1.5-pro"])
        manager.add_provider(google)
        manager.primary_provider = ProviderType.GOOGLE
        assert manager.get_current_model() == "gemini-2.0-flash"

    def test_anthropic_auto_select_first_model(self):
        manager = ProviderManager()
        anthropic = _make_anthropic(["claude-3-5-sonnet-20240620", "claude-3-haiku-20240307"])
        manager.add_provider(anthropic)
        manager.primary_provider = ProviderType.ANTHROPIC
        assert manager.get_current_model() == "claude-3-5-sonnet-20240620"


class TestAutomaticFailover:
    @pytest.mark.asyncio
    async def test_fallback_to_groq_when_ollama_unavailable(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"], available=False)
        groq = _make_groq(["llama-3.3-70b-versatile"], available=True)
        manager.add_provider(ollama)
        manager.add_provider(groq)
        manager.primary_provider = ProviderType.OLLAMA

        async def fake_groq_generate(*args, **kwargs):
            return LLMResponse(content="hi", provider=ProviderType.GROQ, model="llama-3.3-70b-versatile")

        with patch.object(ollama, "generate", new_callable=AsyncMock, side_effect=Exception("Ollama down")):
            with patch.object(groq, "generate", new_callable=AsyncMock, side_effect=fake_groq_generate):
                response = await manager.generate("Hello")
        assert response.provider == ProviderType.GROQ
        assert manager.primary_provider == ProviderType.GROQ

    @pytest.mark.asyncio
    async def test_fallback_chain_through_all_providers(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"], available=False)
        groq = _make_groq(["llama-3.3-70b-versatile"], available=False)
        openai = _make_openai(["gpt-4o"], available=True)
        manager.add_provider(ollama)
        manager.add_provider(groq)
        manager.add_provider(openai)

        async def fake_openai_generate(*args, **kwargs):
            return LLMResponse(content="hi", provider=ProviderType.OPENAI, model="gpt-4o")

        with patch.object(ollama, "generate", new_callable=AsyncMock, side_effect=Exception("down")):
            with patch.object(groq, "generate", new_callable=AsyncMock, side_effect=Exception("down")):
                with patch.object(openai, "generate", new_callable=AsyncMock, side_effect=fake_openai_generate):
                    response = await manager.generate("Hello")
        assert response.provider == ProviderType.OPENAI
        assert manager.primary_provider == ProviderType.OPENAI

    @pytest.mark.asyncio
    async def test_stream_fallback(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"], available=False)
        groq = _make_groq(["llama-3.3-70b-versatile"], available=True)
        manager.add_provider(ollama)
        manager.add_provider(groq)

        class FakeStream:
            def __init__(self, items):
                self._items = list(items)
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._index]
                self._index += 1
                return item

        def mock_stream(*args, **kwargs):
            return FakeStream(["hello"])

        with patch.object(ollama, "stream_generate", side_effect=Exception("down")):
            with patch.object(groq, "stream_generate", side_effect=mock_stream):
                chunks = []
                async for chunk in manager.stream_generate("Hello"):
                    chunks.append(chunk)
        assert "hello" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"], available=False)
        groq = _make_groq(["llama-3.3-70b-versatile"], available=False)
        manager.add_provider(ollama)
        manager.add_provider(groq)

        with patch.object(ollama, "generate", new_callable=AsyncMock, side_effect=Exception("down")):
            with patch.object(groq, "generate", new_callable=AsyncMock, side_effect=Exception("down")):
                with pytest.raises(Exception, match="All providers failed"):
                    await manager.generate("Hello")


class TestModelAutoSwitch:
    def test_switch_model_ollama(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b", "deepseek-r1:8b"])
        manager.add_provider(ollama)
        manager.primary_provider = ProviderType.OLLAMA
        success, model = manager.set_model("deepseek")
        assert success is True
        assert model == "deepseek-r1:8b"
        assert manager.primary_provider == ProviderType.OLLAMA

    def test_switch_model_logs_event(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"])
        manager.add_provider(ollama)
        manager.primary_provider = ProviderType.OLLAMA
        manager.set_model("qwen3")
        assert len(manager._switch_log) == 1
        assert manager._switch_log[0]["event"] == "model_switched"
        assert manager._switch_log[0]["provider"] == "ollama"

    def test_switch_provider_logs_event(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b"])
        groq = _make_groq(["llama-3.3-70b-versatile"])
        manager.add_provider(ollama)
        manager.add_provider(groq)
        manager.primary_provider = ProviderType.OLLAMA
        manager.set_primary(ProviderType.GROQ)
        events = [e for e in manager._switch_log if e["event"] == "provider_switched"]
        assert len(events) == 1
        assert events[0]["to"] == "groq"

    def test_set_model_auto_selects_first_ollama_model(self):
        manager = ProviderManager()
        ollama = _make_ollama(["qwen3:8b", "phi3:14b"])
        manager.add_provider(ollama)
        manager.primary_provider = ProviderType.OLLAMA
        success, model = manager.set_model("nonexistent-model-xyz")
        assert success is False
        assert model == "nonexistent-model-xyz"


class TestProviderStatus:
    def test_get_status_returns_all_providers(self):
        manager = ProviderManager()
        manager.add_provider(_make_ollama(["qwen3:8b"]))
        manager.add_provider(_make_groq(["llama-3.3-70b-versatile"]))
        manager.add_provider(_make_openai(["gpt-4o"]))
        status = manager.get_status()
        assert "ollama" in status["providers"]
        assert "groq" in status["providers"]
        assert "openai" in status["providers"]

    def test_format_status_shows_fallback_chain(self):
        manager = ProviderManager()
        manager.add_provider(_make_ollama(["qwen3:8b"]))
        manager.add_provider(_make_groq(["llama-3.3-70b-versatile"]))
        manager.primary_provider = ProviderType.OLLAMA
        text = manager.format_status()
        assert "Ollama" in text
        assert "groq" in text

    def test_format_models_shows_all_providers(self):
        manager = ProviderManager()
        manager.add_provider(_make_ollama(["qwen3:8b"]))
        manager.add_provider(_make_groq(["llama-3.3-70b-versatile"]))
        text = manager.format_models()
        assert "[ollama]" in text
        assert "[groq]" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
