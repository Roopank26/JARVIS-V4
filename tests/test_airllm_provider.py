
"""Tests for the AirLLM provider integration."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from jarvis.api.providers import (
    LLMConfig,
    LLMResponse,
    ProviderManager,
    ProviderType,
)

logger = logging.getLogger(__name__)


def _make_airllm(models=None, available=True):
    cfg = LLMConfig(provider=ProviderType.AIRLLM, model=models[0] if models else None)
    try:
        from jarvis.providers.airllm.provider import AirLLMProvider

        p = AirLLMProvider(cfg)
    except Exception as exc:
        pytest.skip(f"AirLLM provider unavailable: {exc}")
    p._available = available
    p._available_models = models or []
    if models:
        p._model = models[0]
    return p


class TestAirLLMProvider:
    def test_provider_type_exists(self):
        assert ProviderType.AIRLLM.value == "airllm"

    def test_airllm_priority_last(self):
        assert ProviderManager.PROVIDER_PRIORITY[-1] == ProviderType.AIRLLM

    def test_airllm_fallback_to_none(self):
        assert ProviderManager.PROVIDER_FALLBACK_ORDER[ProviderType.AIRLLM] is None

    def test_add_airllm_provider(self):
        manager = ProviderManager()
        airllm = _make_airllm(["Qwen/Qwen3-8B"])
        manager.add_provider(airllm)
        assert ProviderType.AIRLLM in manager.providers

    def test_airllm_model_alias_resolution(self):
        manager = ProviderManager()
        airllm = _make_airllm(["Qwen/Qwen3-8B"])
        manager.add_provider(airllm)
        manager.primary_provider = ProviderType.AIRLLM
        success, model = manager.set_model("qwen3")
        assert success is True
        assert model == "Qwen/Qwen3-8B"

    def test_airllm_status_includes_vram(self):
        manager = ProviderManager()
        airllm = _make_airllm(["Qwen/Qwen3-8B"])
        manager.add_provider(airllm)
        status = airllm.get_status()
        assert "vram_used_gb" in status
        assert status["provider"] == "airllm"


class TestAirLLMFallback:
    @pytest.mark.asyncio
    async def test_fallback_to_ollama_when_airllm_unavailable(self):
        manager = ProviderManager()
        airllm = _make_airllm(["Qwen/Qwen3-8B"], available=False)
        ollama_cfg = LLMConfig(provider=ProviderType.OLLAMA, model="qwen3:8b")
        from jarvis.api.providers import OllamaProvider

        ollama = OllamaProvider(ollama_cfg)
        ollama._available_models = ["qwen3:8b"]
        ollama._available = True
        manager.add_provider(airllm)
        manager.add_provider(ollama)
        manager.primary_provider = ProviderType.AIRLLM

        async def fake_ollama_generate(*args, **kwargs):
            return LLMResponse(content="hi", provider=ProviderType.OLLAMA, model="qwen3:8b")

        with patch.object(
            airllm, "generate", new_callable=AsyncMock, side_effect=Exception("AirLLM down")
        ):
            with patch.object(
                ollama, "generate", new_callable=AsyncMock, side_effect=fake_ollama_generate
            ):
                response = await manager.generate("Hello")
        assert response.provider == ProviderType.OLLAMA
        assert manager.primary_provider == ProviderType.OLLAMA


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
