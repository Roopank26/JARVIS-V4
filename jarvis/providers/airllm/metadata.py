
"""AirLLM model metadata extraction."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
contextlib_suppress = contextlib.suppress


@dataclass
class ModelMetadata:
    """Metadata for an AirLLM-compatible model."""

    model_id: str
    name: str
    size_gb: float = 0.0
    context_length: int = 512
    architecture: str = "Unknown"
    parameters_b: float = 0.0
    quantization: str = "none"
    pipeline_tag: str | None = None
    likes: int = 0
    tags: list[str] = field(default_factory=list)
    source: str = "unknown"
    supports_streaming: bool = True
    is_reasoning: bool = False

    def display_name(self) -> str:
        return self.name or self.model_id.split("/")[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.display_name(),
            "size_gb": round(self.size_gb, 1),
            "context_length": self.context_length,
            "architecture": self.architecture,
            "parameters_b": self.parameters_b,
            "quantization": self.quantization,
            "pipeline_tag": self.pipeline_tag,
            "likes": self.likes,
            "tags": self.tags,
            "source": self.source,
            "supports_streaming": self.supports_streaming,
            "is_reasoning": self.is_reasoning,
        }


def extract_local_metadata(model_path: str) -> ModelMetadata | None:
    """Extract metadata from a locally cached HuggingFace model."""
    try:
        from transformers import AutoConfig

        from jarvis.providers.airllm.utils import get_model_size_gb

        cfg = AutoConfig.from_pretrained(model_path)
        model_id = _guess_repo_id_from_path(model_path)
        num_params = getattr(cfg, "num_parameters", None)
        if num_params is None and hasattr(cfg, "hidden_size") and hasattr(cfg, "num_hidden_layers"):
            vocab = getattr(cfg, "vocab_size", 32000)
            intermediate = getattr(cfg, "intermediate_size", cfg.hidden_size * 4)
            layers = cfg.num_hidden_layers
            embed = cfg.hidden_size * vocab
            per_layer = cfg.hidden_size * cfg.hidden_size * 4 + intermediate * cfg.hidden_size * 2
            num_params = embed + per_layer * layers

        return ModelMetadata(
            model_id=model_id,
            name=model_id.split("/")[-1],
            size_gb=get_model_size_gb(model_path),
            context_length=getattr(cfg, "max_position_embeddings", None) or getattr(cfg, "seq_length", 512),
            architecture=getattr(cfg, "architectures", ["Unknown"])[0],
            parameters_b=num_params / 1e9 if num_params else 0.0,
            source="local",
        )
    except Exception as exc:
        logger.debug("Could not extract local metadata for %s: %s", model_path, exc)
        return None


def extract_hub_metadata(model_info: dict[str, Any]) -> ModelMetadata | None:
    """Extract metadata from a HuggingFace Hub model-info dict."""
    try:
        model_id = model_info.get("id", "")
        if not model_id:
            return None

        card_data = model_info.get("cardData", {}) or {}
        if not isinstance(card_data, dict):
            card_data = vars(card_data) if hasattr(card_data, "__dict__") else {}
        config_data = model_info.get("config", {}) or {}
        if not isinstance(config_data, dict):
            config_data = vars(config_data) if hasattr(config_data, "__dict__") else {}
        transformers_config = config_data.get("transformers", {}) or {}
        if not isinstance(transformers_config, dict):
            transformers_config = vars(transformers_config) if hasattr(transformers_config, "__dict__") else {}
        model_config = transformers_config.get("architecture", "Unknown")

        tags = model_info.get("tags", []) or []
        pipeline_tag = model_info.get("pipeline_tag")

        size_gb = 0.0
        siblings = model_info.get("siblings") or []
        for s in siblings:
            s_dict = vars(s) if hasattr(s, "__dict__") else s
            if s_dict.get("rfilename", "").endswith((".safetensors", ".bin")):
                size_gb += s_dict.get("size", 0) or 0
        size_gb /= 1024 ** 3

        context_length = 512
        if card_data:
            context_length = int(
                card_data.get("max_position_embeddings")
                or card_data.get("seq_length", 512)
                or transformers_config.get("max_length", 512)
                or 512
            )

        parameters_b = 0.0
        if card_data:
            params_str = card_data.get("parameters", "0")
            with contextlib_suppress(ValueError, AttributeError):
                parameters_b = float(str(params_str).replace("B", "").strip())

        is_reasoning = any(k in model_id.lower() for k in ["deepseek", "r1", "reasoning", "think"])

        return ModelMetadata(
            model_id=model_id,
            name=model_id.split("/")[-1],
            size_gb=size_gb,
            context_length=context_length,
            architecture=model_config,
            parameters_b=parameters_b,
            pipeline_tag=pipeline_tag,
            likes=model_info.get("likes", 0),
            tags=tags,
            source="hub",
            is_reasoning=is_reasoning,
        )
    except Exception as exc:
        logger.debug("Could not extract hub metadata for %s: %s", model_info.get("id"), exc)
        return None


def _guess_repo_id_from_path(path: str) -> str:
    """Best-effort guess of a HF repo ID from a local cache path."""
    p = Path(path)
    if "hub" in p.parts:
        for part in p.parts:
            if part.startswith("models--"):
                return part.replace("models--", "").replace("--", "/")
    return p.name
