
"""AirLLM-specific configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class AirLLMConfig:
    """Configuration for the AirLLM local provider."""

    device: str = "cuda:0"
    dtype: str | None = None
    max_seq_len: int = 512
    layer_shards_saving_path: str | None = None
    profiling_mode: bool = False
    compression: Literal["4bit", "8bit"] | None = None
    hf_token: str | None = None
    prefetching: bool = True
    delete_original: bool = False
    models_dir: str | None = None
    discover_hub: bool = True
    discover_local: bool = True
    max_discovered_models: int = 50
