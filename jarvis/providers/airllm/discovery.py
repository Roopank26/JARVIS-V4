
"""AirLLM model discovery: local cache + HuggingFace Hub."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from jarvis.providers.airllm.metadata import (
    ModelMetadata,
    extract_hub_metadata,
    extract_local_metadata,
)

logger = logging.getLogger(__name__)

_HF_CACHE_ENV = "HF_HOME"
_DEFAULT_HF_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
_POPULAR_MODELS = [
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-4B",
    "Qwen/Qwen3-1.7B",
    "meta-llama/Llama-3.2-3B",
    "meta-llama/Llama-3.2-1B",
    "google/gemma-2-2b",
    "microsoft/phi-2",
    "microsoft/phi-4-mini",
    "HuggingFaceH4/zephyr-7b-beta",
    "mistralai/Mistral-7B-Instruct-v0.3",
]


_EMBEDDING_PREFIXES = (
    "sentence-transformers/",
    "BAAI/",
    "intfloat/",
    "thenlper/",
    "WhereIsAI/UAE-",
    "mixedbread-ai/",
)


def _is_text_generation_model(model_id: str) -> bool:
    return not model_id.startswith(_EMBEDDING_PREFIXES)


def discover_local_models(max_models: int = 50) -> list[ModelMetadata]:
    """Scan the local HuggingFace cache for model directories."""
    discovered: list[ModelMetadata] = []
    hf_home = Path(os.environ.get(_HF_CACHE_ENV, _DEFAULT_HF_CACHE))
    if not hf_home.exists():
        return discovered

    seen: set[str] = set()
    try:
        for entry in hf_home.iterdir():
            if entry.is_dir() and entry.name.startswith("models--"):
                repo_id = entry.name.replace("models--", "").replace("--", "/")
                if repo_id in seen or not _is_text_generation_model(repo_id):
                    continue
                seen.add(repo_id)
                snapshots = entry / "snapshots"
                if snapshots.exists():
                    for snap in snapshots.iterdir():
                        if snap.is_dir():
                            meta = extract_local_metadata(str(snap))
                            if meta:
                                discovered.append(meta)
                                if len(discovered) >= max_models:
                                    return discovered
    except Exception as exc:
        logger.debug("Local model scan failed: %s", exc)

    return discovered


def discover_hub_models(query: str = "", max_models: int = 50) -> list[ModelMetadata]:
    """Query HuggingFace Hub for compatible models."""
    discovered: list[ModelMetadata] = []
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        models_iter = api.list_models(
            search=query or "text-generation",
            limit=max_models,
            sort="lastModified",
        )
        for model_info in models_iter:
            info_dict = vars(model_info)
            model_id = info_dict.get("id", "")
            if not _is_text_generation_model(model_id):
                continue
            meta = extract_hub_metadata(info_dict)
            if meta:
                discovered.append(meta)
                if len(discovered) >= max_models:
                    break
    except Exception as exc:
        logger.debug("Hub model discovery failed: %s", exc)
    return discovered


def discover_popular_models(max_models: int = 20) -> list[ModelMetadata]:
    """Return metadata for a curated list of popular local-AI models."""
    discovered: list[ModelMetadata] = []
    for model_id in _POPULAR_MODELS[:max_models]:
        try:
            from huggingface_hub import model_info

            info = model_info(model_id)
            meta = extract_hub_metadata(vars(info))
            if meta:
                discovered.append(meta)
        except Exception as exc:
            logger.debug("Could not fetch metadata for %s: %s", model_id, exc)
    return discovered


def discover_all_models(
    discover_hub: bool = True,
    discover_local: bool = True,
    max_models: int = 50,
) -> list[ModelMetadata]:
    """Run full discovery: local cache + popular hub models."""
    all_models: list[ModelMetadata] = []
    seen_ids: set[str] = set()

    def _add_unique(meta: ModelMetadata) -> None:
        if meta.model_id not in seen_ids:
            seen_ids.add(meta.model_id)
            all_models.append(meta)

    if discover_local:
        for meta in discover_local_models(max_models):
            _add_unique(meta)

    if discover_hub:
        for meta in discover_popular_models(max_models):
            _add_unique(meta)

    logger.info("AirLLM discovery found %d unique models.", len(all_models))
    return all_models
