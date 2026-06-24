"""
AI Provider Abstraction Layer for JARVIS.
Provides fallback hierarchy: Ollama (Local) → Groq (Cloud)
"""

import asyncio
import logging
import re
import time
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """AI provider types."""
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: ProviderType = ProviderType.GROQ
    model: str = "llama-3.3-70b-versatile"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0
    stream: bool = True


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    provider: ProviderType
    model: str
    usage: Optional[Dict[str, int]] = None
    latency: float = 0.0
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._available = True
        self._last_error: Optional[str] = None
        self._available_models: List[str] = []

    @property
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._available

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    @property
    def available_models(self) -> List[str]:
        """Get available models for this provider."""
        return self._available_models

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a response from the model."""
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream a response from the model."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the provider is healthy."""
        pass

    async def initialize(self) -> bool:
        """Initialize the provider."""
        try:
            return await self.check_health()
        except Exception as e:
            self._available = False
            self._last_error = str(e)
            return False


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model or "qwen3:8b"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Ollama."""
        start = time.time()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                        "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                    }
                }

                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return LLMResponse(
                            content=data.get("response", ""),
                            provider=ProviderType.OLLAMA,
                            model=self.model,
                            latency=time.time() - start
                        )
                    else:
                        error = await resp.text()
                        self._last_error = f"HTTP {resp.status}: {error}"
                        self._available = False
                        raise Exception(self._last_error)

        except aiohttp.ClientError as e:
            self._last_error = f"Connection error: {e}"
            self._available = False
            raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response from Ollama."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                }

                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    async for line in resp.content:
                        if line:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]

        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    async def check_health(self) -> bool:
        """Check if Ollama is running and store available models."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = data.get("models", [])
                        self._available_models = [m["name"] for m in models]
                        logger.info(f"Ollama available, {len(models)} models")
                        return True
                    return False
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """List available Ollama models."""
        if self._available_models:
            return self._available_models
        await self.check_health()
        return self._available_models


class GroqProvider(BaseLLMProvider):
    """Groq cloud LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.model = config.model or "llama-3.3-70b-versatile"
        self.api_key = config.api_key

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Groq."""
        import aiohttp
        start = time.time()

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "stream": False
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return LLMResponse(
                            content=data["choices"][0]["message"]["content"],
                            provider=ProviderType.GROQ,
                            model=self.model,
                            usage=data.get("usage"),
                            latency=time.time() - start
                        )
                    else:
                        error = await resp.json()
                        self._last_error = error.get("error", {}).get("message", "Unknown error")
                        raise Exception(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response from Groq."""
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            if line.strip() == "data: [DONE]":
                                break
                            try:
                                data = json.loads(line[6:])
                                if "choices" in data:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                pass

    async def check_health(self) -> bool:
        """Check if Groq is available."""
        try:
            import aiohttp
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=headers,
                    timeout=5.0
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False


class ProviderManager:
    """
    Manages multiple LLM providers with automatic fallback.
    
    Priority: Ollama (Local) → Groq (Cloud)
    JARVIS uses local models first and only falls back to cloud when local is unavailable.
    """

    # Provider priority order (local first)
    PROVIDER_PRIORITY = [
        ProviderType.OLLAMA,  # Local - highest priority
        ProviderType.GROQ,    # Cloud fallback
    ]

    # Default models
    DEFAULT_MODEL = "qwen3:8b"
    REASONING_MODEL = "deepseek-r1:8b"

    # Reasoning task patterns
    REASONING_PATTERNS = [
        r"\b(step by step|explain how|reasoning|thinking|analyze)",
        r"\b(algorithm|problem|solve|calculate|prove)",
        r"\b(why|how come|what if|compare)",
    ]

    def __init__(self):
        self.providers: Dict[ProviderType, BaseLLMProvider] = {}
        self.primary_provider: Optional[ProviderType] = None
        self._initialized = False
        self._startup_diagnostics: Dict[str, Any] = {}

    def add_provider(self, provider: BaseLLMProvider) -> None:
        """Add a provider to the manager."""
        self.providers[provider.config.provider] = provider

    def set_primary(self, provider_type: ProviderType) -> None:
        """Set the primary provider."""
        if provider_type in self.providers:
            self.primary_provider = provider_type

    def set_model(self, model: str) -> bool:
        """Switch to a specific model across providers."""
        # Normalize model name
        model_lower = model.lower().strip()
        if not model_lower.endswith(":8b") and ":" not in model_lower:
            model_lower = model_lower + ":8b"

        # Check if model is in Ollama
        if ProviderType.OLLAMA in self.providers:
            ollama = self.providers[ProviderType.OLLAMA]
            for avail_model in ollama.available_models:
                if model_lower in avail_model.lower():
                    ollama.model = avail_model
                    self.primary_provider = ProviderType.OLLAMA
                    logger.info(f"Switched to Ollama model: {avail_model}")
                    return True

        # Check other providers
        for provider_type, provider in self.providers.items():
            if hasattr(provider, 'model'):
                provider.model = model
                self.primary_provider = provider_type
                logger.info(f"Switched to {provider_type.value} model: {model}")
                return True

        return False

    def get_best_model_for_task(self, prompt: str) -> str:
        """Intelligently select the best model for a given task."""
        prompt_lower = prompt.lower()
        
        # Check for reasoning patterns
        for pattern in self.REASONING_PATTERNS:
            if re.search(pattern, prompt_lower):
                if ProviderType.OLLAMA in self.providers:
                    ollama = self.providers[ProviderType.OLLAMA]
                    for model in ollama.available_models:
                        if "deepseek" in model.lower():
                            return model
                return self.REASONING_MODEL
        
        # Default to general purpose model
        if ProviderType.OLLAMA in self.providers:
            ollama = self.providers[ProviderType.OLLAMA]
            for model in ollama.available_models:
                if "qwen" in model.lower():
                    return model
        return self.DEFAULT_MODEL

    async def initialize(self) -> bool:
        """Initialize providers in priority order (local first)."""
        self._startup_diagnostics = {"providers": {}, "primary": None}

        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                try:
                    is_healthy = await provider.check_health()
                    self._startup_diagnostics["providers"][provider_type.value] = {
                        "available": is_healthy,
                        "model": provider.model,
                        "models": provider.available_models,
                    }
                    print(f"[Provider] {provider_type.value.capitalize()}: {'detected' if is_healthy else 'unavailable'}")
                    if is_healthy and self.primary_provider is None:
                        self.primary_provider = provider_type
                        print(f"[Provider] Selected: {provider_type.value}")
                except Exception as e:
                    self._startup_diagnostics["providers"][provider_type.value] = {
                        "available": False,
                        "error": str(e),
                    }
                    print(f"[Provider] {provider_type.value}: error - {e}")

        # Log available models
        if self.primary_provider:
            provider = self.providers[self.primary_provider]
            if provider.available_models:
                print(f"[Provider] Available models:")
                for model in provider.available_models:
                    print(f"  - {model}")
            self._startup_diagnostics["primary"] = self.primary_provider.value
            self._initialized = True
            return True

        self._initialized = False
        return False

    def get_startup_diagnostics(self) -> Dict[str, Any]:
        """Get startup diagnostics for logging."""
        return self._startup_diagnostics

    def format_status(self) -> str:
        """Format provider status for display."""
        lines = ["[Provider Status]", "=" * 40]

        for provider_type, provider in self.providers.items():
            is_primary = provider_type == self.primary_provider
            status = "✓ PRIMARY" if is_primary else "○ available" if provider.is_available else "✗ unavailable"

            lines.append(f"\n{provider_type.value.upper()}:")
            lines.append(f"  Status: {status}")
            lines.append(f"  Model: {provider.model}")

            if provider.available_models:
                lines.append("  Available models:")
                for model in provider.available_models:
                    marker = " ← DEFAULT" if model == self.DEFAULT_MODEL else ""
                    marker = " ← REASONING" if "deepseek" in model.lower() else marker
                    lines.append(f"    • {model}{marker}")

        return "\n".join(lines)

    def format_models(self) -> str:
        """Format available models list."""
        if ProviderType.OLLAMA in self.providers:
            ollama = self.providers[ProviderType.OLLAMA]
            if ollama.available_models:
                return "\n".join([f"  • {m}" for m in ollama.available_models])
        return "  No models available"

    def get_current_model(self) -> str:
        """Get the current model name."""
        if self.primary_provider and self.primary_provider in self.providers:
            return self.providers[self.primary_provider].model
        return "No provider selected"

    async def benchmark_models(self, test_prompt: str = "Count from 1 to 5") -> Dict[str, Any]:
        """Benchmark all available models."""
        results = {}

        if ProviderType.OLLAMA in self.providers:
            ollama = self.providers[ProviderType.OLLAMA]
            for model in ollama.available_models[:3]:
                try:
                    old_model = ollama.model
                    ollama.model = model
                    
                    start = time.time()
                    response = await ollama.generate(test_prompt)
                    latency = time.time() - start
                    
                    results[f"ollama/{model}"] = {
                        "latency": round(latency, 2),
                        "tokens": len(response.content.split()),
                        "provider": "Ollama"
                    }
                    
                    ollama.model = old_model
                except Exception as e:
                    results[f"ollama/{model}"] = {"error": str(e)}

        return results

    def compare_models(self, model1: str, model2: str) -> str:
        """Compare two models side by side."""
        lines = ["[Model Comparison]", "=" * 40, ""]
        
        for model in [model1, model2]:
            lines.append(f"### {model}")
            if ProviderType.OLLAMA in self.providers:
                ollama = self.providers[ProviderType.OLLAMA]
                if model in ollama.available_models:
                    lines.append("  Provider: Ollama")
                    lines.append("  Status: Available ✓")
                    continue
            lines.append("  Provider: Unknown")
            lines.append("  Status: Not available")
            lines.append("")
        
        return "\n".join(lines)

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using available providers with fallback."""
        if self.primary_provider and self.primary_provider in self.providers:
            provider = self.providers[self.primary_provider]
            try:
                if provider.is_available:
                    return await provider.generate(prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Primary provider error: {e}")

        for provider_type, provider in self.providers.items():
            if provider_type == self.primary_provider:
                continue
            try:
                if await provider.check_health():
                    self.primary_provider = provider_type
                    logger.info(f"Falling back to {provider_type.value}")
                    return await provider.generate(prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {provider_type.value} error: {e}")

        raise Exception("All providers failed")

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response with fallback."""
        if self.primary_provider and self.primary_provider in self.providers:
            provider = self.providers[self.primary_provider]
            try:
                if provider.is_available:
                    async for chunk in provider.stream_generate(prompt, **kwargs):
                        yield chunk
                    return
            except Exception as e:
                logger.warning(f"Stream error: {e}")

        response = await self.generate(prompt, **kwargs)
        yield response.content

    def get_available_providers(self) -> List[ProviderType]:
        """Get list of available providers."""
        return [p for p, provider in self.providers.items() if provider.is_available]

    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "primary": self.primary_provider.value if self.primary_provider else None,
            "providers": {
                p.value: {
                    "available": provider.is_available,
                    "model": provider.model,
                    "last_error": provider.last_error
                }
                for p, provider in self.providers.items()
            }
        }


# Global provider manager
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def init_providers(configs: Dict[ProviderType, LLMConfig]) -> ProviderManager:
    """Initialize provider manager with configs."""
    global _provider_manager
    _provider_manager = ProviderManager()

    for provider_type, config in configs.items():
        if provider_type == ProviderType.OLLAMA:
            _provider_manager.add_provider(OllamaProvider(config))
        elif provider_type == ProviderType.GROQ:
            _provider_manager.add_provider(GroqProvider(config))

    return _provider_manager
