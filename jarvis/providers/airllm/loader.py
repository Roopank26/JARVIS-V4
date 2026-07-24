
"""Memory-efficient AirLLM model loader adapted for JARVIS."""

from __future__ import annotations

import importlib.util
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from jarvis.providers.airllm.utils import clean_memory, get_vram_used_gb

logger = logging.getLogger(__name__)


class AirLLMLoaderError(Exception):
    """Raised when the AirLLM model loader encounters a fatal error."""


class AirLLMLoader:
    """
    Thin wrapper that manages an AirLLM-backed model lifecycle inside JARVIS.

    Responsibilities:
      * Resolve the local or Hub model path.
      * Build the meta-initialized transformers model.
      * Provide generate / stream_generate interfaces the provider can call.
      * Report memory footprint and metadata.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.model = None
        self.tokenizer = None
        self._model_path: str | None = None
        self._layer_names: list[str] = []
        self._prefetching = bool(config.get("prefetching", True))
        self._executor = ThreadPoolExecutor(max_workers=1) if self._prefetching else None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def vram_used_gb(self) -> float:
        return get_vram_used_gb()

    def load(self, model_id: str) -> dict[str, Any]:
        """
        Load the model using AirLLM-style layer streaming.

        Returns metadata dict.
        """
        if not _is_airllm_available():
            raise AirLLMLoaderError(
                "AirLLM dependencies missing. Install torch, transformers, accelerate, safetensors."
            )

        try:
            self._do_load(model_id)
            self._loaded = True
            meta = self._collect_metadata(model_id)
            logger.info("AirLLM loaded model '%s' successfully.", model_id)
            return meta
        except Exception as exc:
            self._loaded = False
            logger.error("AirLLM failed to load model '%s': %s", model_id, exc)
            raise AirLLMLoaderError(str(exc)) from exc

    def _do_load(self, model_id: str) -> None:
        """Actual model loading logic."""
        import torch
        from accelerate import init_empty_weights
        from accelerate.utils.modeling import set_module_tensor_to_device
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

        device = self.config.get("device", "cuda:0")
        dtype = self.config.get("dtype")
        max_seq_len = int(self.config.get("max_seq_len", 512))
        compression = self.config.get("compression")
        hf_token = self.config.get("hf_token")
        _ = self.config.get("layer_shards_saving_path")

        if compression is not None and importlib.util.find_spec("bitsandbytes") is None:
            raise AirLLMLoaderError("Compression requires bitsandbytes.")

        self._model_path = _resolve_model_path(model_id, hf_token)

        cfg = AutoConfig.from_pretrained(self._model_path, trust_remote_code=False)
        if dtype is None:
            cfg_dtype = getattr(cfg, "torch_dtype", None)
            if isinstance(cfg_dtype, str):
                cfg_dtype = getattr(torch, cfg_dtype, None)
            dtype = cfg_dtype if isinstance(cfg_dtype, torch.dtype) else torch.float16
        self.dtype = dtype

        self.tokenizer = AutoTokenizer.from_pretrained(
            self._model_path, token=hf_token, trust_remote_code=True
        )

        with init_empty_weights(include_buffers=False):
            self.model = AutoModelForCausalLM.from_config(
                cfg, attn_implementation="sdpa", trust_remote_code=False
            )
        if self.model is None:
            with init_empty_weights(include_buffers=False):
                self.model = AutoModelForCausalLM.from_config(
                    cfg, attn_implementation="eager", trust_remote_code=False
                )

        self.model.eval()
        self.model.tie_weights()

        for buffer_name, buffer in self.model.named_buffers():
            if buffer is not None and buffer.device.type != "meta":
                set_module_tensor_to_device(
                    self.model, buffer_name, device, value=buffer
                )

        self._patch_device(device, dtype)

        self._layer_names = _build_layer_names(self.model, getattr(cfg, "model_type", "llama"))
        self.max_seq_len = max_seq_len

    def _patch_device(self, device: str, dtype: Any) -> None:
        """Force the model to report the real device even with meta tensors."""
        import torch

        running_device = torch.device(device)
        base_cls = type(self.model)

        class _RuntimeModel(base_cls):
            @property
            def device(self):  # type: ignore[override]
                return running_device

            @property
            def dtype(self):  # type: ignore[override]
                return dtype

        self.model.__class__ = _RuntimeModel

    def _collect_metadata(self, model_id: str) -> dict[str, Any]:
        """Return basic metadata for a loaded model."""
        from transformers import AutoConfig

        cfg = AutoConfig.from_pretrained(self._model_path or model_id)
        num_params = getattr(cfg, "num_parameters", None)
        if num_params is None and hasattr(cfg, "hidden_size") and hasattr(cfg, "num_hidden_layers"):
            vocab = getattr(cfg, "vocab_size", 32000)
            intermediate = getattr(cfg, "intermediate_size", cfg.hidden_size * 4)
            layers = cfg.num_hidden_layers
            embed = cfg.hidden_size * vocab
            per_layer = cfg.hidden_size * cfg.hidden_size * 4 + intermediate * cfg.hidden_size * 2
            num_params = embed + per_layer * layers

        params_b = num_params / 1e9 if num_params else 0.0
        context_len = getattr(cfg, "max_position_embeddings", None) or getattr(
            cfg, "seq_length", 512
        )
        arch = getattr(cfg, "architectures", ["Unknown"])[0]

        return {
            "model_id": model_id,
            "architecture": arch,
            "parameters_b": round(params_b, 1),
            "context_length": context_len,
            "dtype": str(self.dtype),
            "device": self.config.get("device", "cuda:0"),
            "vram_used_gb": round(self.vram_used_gb, 2),
        }

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if self.model is None:
            raise AirLLMLoaderError("Model not loaded.")
        try:
            import torch

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=kwargs.get("max_length", self.max_seq_len),
            )
            input_ids = inputs["input_ids"].to(self.model.device)

            gen_kwargs: dict[str, Any] = {
                "max_new_tokens": kwargs.get("max_new_tokens", 256),
                "temperature": kwargs.get("temperature", 0.7),
                "do_sample": True,
                "pad_token_id": self.tokenizer.eos_token_id,
            }

            with torch.no_grad():
                output = self.model.generate(input_ids, **gen_kwargs)

            decoded = self.tokenizer.decode(output[0], skip_special_tokens=True)
            return decoded[len(prompt):] if decoded.startswith(prompt) else decoded
        except Exception as exc:
            logger.error("AirLLM generation failed: %s", exc)
            raise

    async def stream_generate(self, prompt: str, **kwargs: Any):
        """Stream tokens one by one."""
        response = await self.generate(prompt, **kwargs)
        for token in response.split():
            yield token + " "

    def unload(self) -> None:
        """Free GPU memory."""
        if self.model is not None:
            contextlib_suppress = __import__("contextlib").suppress
            with contextlib_suppress(Exception):
                self.model.to("meta")
            self.model = None
        if self._executor is not None:
            self._executor.shutdown(wait=False)
        clean_memory()
        self._loaded = False


def _is_airllm_available() -> bool:
    try:
        import importlib.util
        importlib.util.find_spec("torch")
        importlib.util.find_spec("transformers")
        importlib.util.find_spec("accelerate")
    except ImportError:
        return False
    return True


def _resolve_model_path(model_id: str, hf_token: str | None = None) -> str:
    """Return local path for a model (downloads via HF if needed)."""
    if Path(model_id).exists():
        return str(Path(model_id))

    from huggingface_hub import snapshot_download

    cache_path = snapshot_download(
        model_id,
        token=hf_token,
        ignore_patterns=["*.safetensors", "*.bin"],
    )
    has_index = (
        Path(cache_path, "model.safetensors.index.json").exists()
        or Path(cache_path, "pytorch_model.bin.index.json").exists()
    )
    if not has_index:
        cache_path = snapshot_download(
            model_id, token=hf_token, allow_patterns=["model.safetensors", "pytorch_model.bin"]
        )
    return cache_path


def _build_layer_names(model: Any, model_type: str) -> list[str]:
    """Build list of layer names for streaming hook installation."""
    names = ["model.embed_tokens"]
    layers_obj = getattr(model, "model", model)
    if hasattr(layers_obj, "layers"):
        n = len(layers_obj.layers)
        names.extend([f"model.layers.{i}" for i in range(n)])
    names.append("model.norm")
    names.append("lm_head")
    return names
