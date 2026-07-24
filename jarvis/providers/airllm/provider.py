
"""AirLLM native provider for JARVIS."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

from jarvis.api.providers import BaseLLMProvider, LLMConfig, LLMResponse, ProviderType
from jarvis.providers.airllm.config import AirLLMConfig
from jarvis.providers.airllm.discovery import discover_all_models
from jarvis.providers.airllm.loader import AirLLMLoader, AirLLMLoaderError
from jarvis.providers.airllm.metadata import ModelMetadata
from jarvis.providers.airllm.utils import (
    get_airllm_requirements,
    get_vram_total_gb,
    get_vram_used_gb,
    is_airllm_available,
)

logger = logging.getLogger(__name__)


MODEL_ALIASES = {
    "qwen3": "Qwen/Qwen3-8B",
    "qwen": "Qwen/Qwen3-8B",
    "llama3": "meta-llama/Llama-3.2-3B",
    "llama": "meta-llama/Llama-3.2-3B",
    "phi": "microsoft/phi-2",
    "phi3": "microsoft/phi-4-mini",
    "gemma": "google/gemma-2-2b",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "deepseek": "deepseek-ai/DeepSeek-V2-Lite",
    "zephyr": "HuggingFaceH4/zephyr-7b-beta",
}


class AirLLMProvider(BaseLLMProvider):
    """JARVIS provider backed by AirLLM memory-efficient local inference."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self.airllm_config = AirLLMConfig(
            device=os.environ.get("AIRLLM_DEVICE", "cuda:0"),
            hf_token=getattr(config, "api_key", None) or os.environ.get("HF_TOKEN"),
            max_seq_len=getattr(config, "max_tokens", 512),
        )
        self._loader: AirLLMLoader | None = None
        self._loaded_model_id: str | None = None
        self._model_meta: dict[str, Any] = {}
        self._connection_status = "Not loaded"
        self._latency_ms = 0.0
        self._discovered: list[ModelMetadata] = []
        self._available = self._check_runtime()

    def _check_runtime(self) -> bool:
        if not is_airllm_available():
            self._last_error = "AirLLM runtime dependencies missing: " + ", ".join(
                get_airllm_requirements()
            )
            return False
        try:
            import torch

            if not torch.cuda.is_available():
                self._last_error = (
                    "AirLLM requires a CUDA-capable GPU. "
                    "Use Ollama for CPU local inference."
                )
                return False
        except ImportError:
            self._last_error = "torch not available"
            return False
        return True

    def _resolve_model_hint(self, hint: str) -> str:
        hint_lower = hint.lower().strip()
        if hint_lower in MODEL_ALIASES:
            return MODEL_ALIASES[hint_lower]
        for meta in self._discovered:
            if hint_lower in meta.model_id.lower():
                return meta.model_id
        return hint

    def _pick_generative_model(self) -> str:
        generative_ids = (
            "Qwen/",
            "meta-llama/",
            "google/gemma-",
            "microsoft/phi",
            "mistralai/",
            "HuggingFaceH4/zephyr",
            "deepseek-ai/",
            "tiiuae/",
            "HuggingFaceTB/",
            "01-ai/",
        )
        for model_id in self._available_models:
            if model_id.startswith(generative_ids):
                return model_id
        return self._available_models[0] if self._available_models else ""

    async def initialize(self) -> bool:
        if not self._available:
            return False
        try:
            self._discovered = discover_all_models(
                discover_hub=self.airllm_config.discover_hub,
                discover_local=self.airllm_config.discover_local,
                max_models=self.airllm_config.max_discovered_models,
            )
            self._available_models = [m.model_id for m in self._discovered]
            if self._model:
                resolved = self._resolve_model_hint(self._model)
                if resolved in self._available_models:
                    self._model = resolved
                else:
                    self._model = self._pick_generative_model()
            else:
                self._model = self._pick_generative_model()
            self._connection_status = "Ready"
            logger.info("AirLLM initialized, %d models discovered.", len(self._available_models))
            return True
        except Exception as exc:
            self._last_error = str(exc)
            self._available = False
            logger.error("AirLLM initialization failed: %s", exc)
            return False

    async def check_health(self) -> bool:
        return await self.initialize()

    async def load_model(self, model_id: str) -> dict[str, Any]:
        """Load a model into memory (blocks until ready)."""
        if not self._available:
            raise AirLLMLoaderError("AirLLM runtime unavailable.")
        resolved = self._resolve_model_hint(model_id)
        if self._loaded_model_id == resolved and self._loader and self._loader.is_loaded:
            return self._model_meta

        if self._loader:
            self._loader.unload()

        loader = AirLLMLoader(
            {
                "device": self.airllm_config.device,
                "dtype": self.airllm_config.dtype,
                "max_seq_len": self.airllm_config.max_seq_len,
                "layer_shards_saving_path": self.airllm_config.layer_shards_saving_path,
                "profiling_mode": self.airllm_config.profiling_mode,
                "compression": self.airllm_config.compression,
                "hf_token": self.airllm_config.hf_token,
                "prefetching": self.airllm_config.prefetching,
                "delete_original": self.airllm_config.delete_original,
            }
        )
        meta = loader.load(resolved)
        self._loader = loader
        self._loaded_model_id = resolved
        self._model = resolved
        self._model_meta = meta
        self._connection_status = "Loaded"
        return meta

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._loader or not self._loader.is_loaded:
            raise AirLLMLoaderError("No model loaded. Call load_model first.")
        start = time.time()
        try:
            content = await self._loader.generate(prompt, **kwargs)
            self._latency_ms = (time.time() - start) * 1000
            return LLMResponse(
                content=content,
                provider=ProviderType.AIRLLM,
                model=self._loaded_model_id or "",
                usage={},
                latency=time.time() - start,
            )
        except Exception as exc:
            self._last_error = str(exc)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._loader or not self._loader.is_loaded:
            raise AirLLMLoaderError("No model loaded. Call load_model first.")
        try:
            async for chunk in self._loader.stream_generate(prompt, **kwargs):
                yield chunk
        except Exception as exc:
            logger.error("AirLLM stream error: %s", exc)
            raise

    async def list_models(self) -> list[str]:
        if not self._available_models:
            await self.initialize()
        return self._available_models

    def unload(self) -> None:
        """Unload the currently loaded model."""
        if self._loader:
            self._loader.unload()
            self._loader = None
            self._loaded_model_id = None
            self._connection_status = "Unloaded"
            logger.info("AirLLM model unloaded.")

    def get_status(self) -> dict[str, Any]:
        vram_total = get_vram_total_gb()
        vram_used = get_vram_used_gb()
        return {
            "name": "AirLLM",
            "provider": ProviderType.AIRLLM.value,
            "available": self._available,
            "current_model": self._loaded_model_id or self._model or "",
            "available_models": self._available_models,
            "connection": self._connection_status,
            "latency_ms": self._latency_ms,
            "error": self._last_error,
            "last_check": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vram_used_gb": round(vram_used, 2),
            "vram_total_gb": round(vram_total, 2),
            "memory_profile": self._model_meta,
        }
