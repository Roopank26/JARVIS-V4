
"""Refactored AirLLM utilities for JARVIS."""

from __future__ import annotations

import gc
import importlib.util
import os
from pathlib import Path

import torch

logger = __name__


def clean_memory() -> None:
    """Free CPU RAM and GPU VRAM."""
    gc.collect()
    try:
        import ctypes

        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def get_model_size_gb(path: str | Path) -> float:
    """Return total size of model files in GB."""
    total = 0
    root = Path(path)
    if root.is_file():
        return root.stat().st_size / (1024 ** 3)
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            fp = Path(dirpath) / f
            if fp.exists():
                total += fp.stat().st_size
    return total / (1024 ** 3)


def get_vram_used_gb() -> float:
    """Return current GPU VRAM usage in GB."""
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.memory_allocated() / (1024 ** 3)


def get_vram_total_gb() -> float:
    """Return total GPU VRAM in GB."""
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)


def is_airllm_available() -> bool:
    """Check whether AirLLM runtime dependencies are installed."""
    required = ["torch", "transformers", "accelerate", "safetensors", "huggingface_hub", "tqdm"]
    return all(importlib.util.find_spec(pkg) is not None for pkg in required)


def get_airllm_requirements() -> list[str]:
    """Return list of missing AirLLM dependencies."""
    required = ["torch", "transformers", "accelerate", "safetensors", "huggingface_hub", "tqdm"]
    missing = []
    for pkg in required:
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)
    return missing


def estimate_model_vram_gb(model_id: str, hf_token: str | None = None) -> float:
    """Roughly estimate VRAM needed for a model (billions * 0.7 GB for fp16)."""
    try:
        from transformers import AutoConfig

        cfg = AutoConfig.from_pretrained(model_id, token=hf_token)
        params_b = getattr(cfg, "num_parameters", None)
        if params_b is None:
            if hasattr(cfg, "hidden_size") and hasattr(cfg, "num_hidden_layers"):
                vocab = getattr(cfg, "vocab_size", 32000)
                intermediate = getattr(cfg, "intermediate_size", cfg.hidden_size * 4)
                layers = cfg.num_hidden_layers
                embed = cfg.hidden_size * vocab
                per_layer = cfg.hidden_size * cfg.hidden_size * 4 + intermediate * cfg.hidden_size * 2
                params_b = (embed + per_layer * layers) / 1e9
            else:
                return 0.0
        return params_b * 0.7
    except Exception:
        return 0.0
