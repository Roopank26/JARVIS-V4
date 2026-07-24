"""
JARVIS Intelligent Provider Manager
Prioritizes local AI (Ollama) over cloud providers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("jarvis.providers")


class ProviderPriority(Enum):
    """Provider priority levels."""

    LOCAL = 1  # Ollama (fastest, private)
    CLOUD = 2  # Groq, OpenAI
    FALLBACK = 3  # Other providers


@dataclass
class ModelInfo:
    """Information about an AI model."""

    name: str
    provider: str
    size: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    supports_streaming: bool = True
    is_reasoning: bool = False
    recommended_for: list[str] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    name: str
    priority: ProviderPriority = ProviderPriority.CLOUD
    base_url: str | None = None
    api_key: str | None = None
    models: list[str] = field(default_factory=list)
    default_model: str | None = None
    timeout: float = 60.0
    max_retries: int = 3


@dataclass
class GenerationResult:
    """Result from text generation."""

    text: str
    model: str
    provider: str
    tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str | None = None
    error: str | None = None


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._available_models: list[str] = []
        self._is_available = False

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate text."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        pass

    @property
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self._is_available

    @property
    def priority(self) -> ProviderPriority:
        """Get provider priority."""
        return self.config.priority


class OllamaProvider(BaseProvider):
    """
    Ollama provider for local AI models.

    Supports: qwen3, deepseek-r1, llama3, mistral, gemma, etc.
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="ollama",
                priority=ProviderPriority.LOCAL,
                base_url="http://localhost:11434",
            )
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        """Initialize Ollama connection."""
        try:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )

            # Test connection
            self._is_available = await self.health_check()

            if self._is_available:
                self._available_models = await self.list_models()
                logger.info(f"Ollama initialized with {len(self._available_models)} models")
            else:
                logger.warning("Ollama not available")

            return self._is_available

        except ImportError:
            logger.warning("httpx not installed")
            return False
        except Exception as e:
            logger.error(f"Ollama initialization failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate text using Ollama."""
        if not self._is_available:
            return GenerationResult(
                text="",
                model=model or self.config.default_model,
                provider="ollama",
                error="Provider not available",
            )

        model = model or self.config.default_model
        start_time = asyncio.get_event_loop().time()

        try:
            response = await self._client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs,
                },
            )

            if response.status_code == 200:
                data = response.json()
                latency = (asyncio.get_event_loop().time() - start_time) * 1000

                return GenerationResult(
                    text=data.get("response", ""),
                    model=model,
                    provider="ollama",
                    tokens=data.get("eval_count", 0),
                    latency_ms=latency,
                )
            else:
                return GenerationResult(
                    text="",
                    model=model,
                    provider="ollama",
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return GenerationResult(
                text="",
                model=model,
                provider="ollama",
                error=str(e),
            )

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        if not self._client:
            return []

        try:
            response = await self._client.get("/api/tags")

            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "unknown") for m in data.get("models", [])]

        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")

        return []

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        if not self._client:
            return False

        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama."""
        if not self._client:
            return False

        try:
            response = await self._client.post(
                "/api/pull",
                json={"name": model},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    async def delete_model(self, model: str) -> bool:
        """Delete an Ollama model."""
        if not self._client:
            return False

        try:
            response = await self._client.delete("/api/delete", json={"name": model})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model {model}: {e}")
            return False


class GroqProvider(BaseProvider):
    """
    Groq provider for cloud AI models.

    Fast inference, good for production use.
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="groq",
                priority=ProviderPriority.CLOUD,
            )
        super().__init__(config)
        self._client = None

    async def initialize(self) -> bool:
        """Initialize Groq connection."""
        try:
            import httpx

            if not self.config.api_key:
                from jarvis.core.config import get_config

                cfg = get_config()
                self.config.api_key = cfg.get("GROQ_API_KEY")

            if not self.config.api_key:
                logger.warning("Groq API key not configured")
                return False

            self._client = httpx.AsyncClient(
                base_url="https://api.groq.com/openai/v1",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=self.config.timeout,
            )

            self._is_available = await self.health_check()

            if self._is_available:
                self._available_models = await self.list_models()
                logger.info(f"Groq initialized with {len(self._available_models)} models")

            return self._is_available

        except ImportError:
            logger.warning("httpx not installed")
            return False
        except Exception as e:
            logger.error(f"Groq initialization failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """Generate text using Groq."""
        if not self._is_available:
            return GenerationResult(
                text="",
                model=model or self.config.default_model,
                provider="groq",
                error="Provider not available",
            )

        model = model or self.config.default_model
        start_time = asyncio.get_event_loop().time()

        try:
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    **kwargs,
                },
            )

            if response.status_code == 200:
                data = response.json()
                choice = data.get("choices", [{}])[0]
                latency = (asyncio.get_event_loop().time() - start_time) * 1000

                return GenerationResult(
                    text=choice.get("message", {}).get("content", ""),
                    model=model,
                    provider="groq",
                    tokens=data.get("usage", {}).get("total_tokens", 0),
                    latency_ms=latency,
                    finish_reason=choice.get("finish_reason"),
                )
            else:
                return GenerationResult(
                    text="",
                    model=model,
                    provider="groq",
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            logger.error(f"Groq generate error: {e}")
            return GenerationResult(
                text="",
                model=model,
                provider="groq",
                error=str(e),
            )

    async def list_models(self) -> list[str]:
        """List available Groq models."""
        if not self._client:
            return []

        try:
            response = await self._client.get("/models")

            if response.status_code == 200:
                data = response.json()
                return [m.get("id", "unknown") for m in data.get("data", [])]

        except Exception as e:
            logger.error(f"Failed to list Groq models: {e}")

        return []

    async def health_check(self) -> bool:
        """Check if Groq API is available."""
        if not self._client:
            return False

        try:
            response = await self._client.get("/models")
            return response.status_code == 200
        except Exception:
            return False


class IntelligentProviderManager:
    """
    Manages multiple AI providers with intelligent routing.

    Priority: Ollama > Groq > Fallback
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        self._provider_order: list[str] = []
        self._active_provider: str | None = None
        self._model_routing: dict[str, str] = {}  # Task pattern -> preferred model

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a provider."""
        name = provider.config.name
        self._providers[name] = provider

        # Maintain priority order
        inserted = False
        for i, pname in enumerate(self._provider_order):
            if provider.priority.value < self._providers[pname].priority.value:
                self._provider_order.insert(i, name)
                inserted = True
                break

        if not inserted:
            self._provider_order.append(name)

        logger.info(f"Registered provider: {name} (priority: {provider.priority.name})")

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all providers."""
        results = {}

        for name, provider in self._providers.items():
            results[name] = await provider.initialize()

        # Set active provider (first available in priority order)
        for name in self._provider_order:
            if self._providers[name].is_available:
                self._active_provider = name
                break

        return results

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        force_provider: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """
        Generate text using the best available provider.

        Args:
            prompt: Input prompt
            model: Preferred model (optional)
            force_provider: Force specific provider
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult
        """
        # Try active provider first
        if force_provider and force_provider in self._providers:
            result = await self._providers[force_provider].generate(prompt, model, **kwargs)
            if not result.error:
                return result

        # Try providers in priority order
        for name in self._provider_order:
            provider = self._providers[name]

            if not provider.is_available:
                continue

            result = await provider.generate(prompt, model, **kwargs)

            if not result.error:
                self._active_provider = name
                return result

        # Return error if no provider worked
        return GenerationResult(
            text="",
            model=model or "unknown",
            provider="none",
            error="No providers available",
        )

    def get_best_model_for_task(self, task_type: str) -> str | None:
        task_lower = task_type.lower()

        reason_keywords = ("reason", "code", "analyze", "plan", "complex", "implement", "review")
        simple_keywords = ("chat", "hello", "simple", "quick", "fast", "greet")

        for provider_name in self._provider_order:
            provider = self._providers[provider_name]
            if not provider.is_available or not provider._available_models:
                continue

            models = provider._available_models

            if any(k in task_lower for k in reason_keywords):
                for m in models:
                    if any(k in m.lower() for k in ("70b", "32b", "deepseek", "qwen", "llama3", "r1")):
                        return m

            if any(k in task_lower for k in simple_keywords):
                for m in models:
                    if any(k in m.lower() for k in ("7b", "mini", "small", "fast")):
                        return m

            return models[0]

        return None

    async def list_all_models(self) -> dict[str, list[str]]:
        """List all models from all providers."""
        models = {}

        for name, provider in self._providers.items():
            if provider.is_available:
                models[name] = await provider.list_models()

        return models

    def get_provider_status(self) -> list[dict[str, Any]]:
        """Get status of all providers."""
        return [
            {
                "name": name,
                "available": provider.is_available,
                "priority": provider.priority.name,
                "models": len(provider._available_models),
                "active": name == self._active_provider,
            }
            for name, provider in self._providers.items()
        ]

    @property
    def active_provider(self) -> str | None:
        """Get active provider name."""
        return self._active_provider

    @property
    def providers(self) -> dict[str, BaseProvider]:
        """Get all providers."""
        return self._providers


# Factory function
def create_provider_manager() -> IntelligentProviderManager:
    """
    Create and configure the provider manager.

    Returns:
        Configured IntelligentProviderManager
    """
    manager = IntelligentProviderManager()

    # Register providers in priority order
    manager.register_provider(OllamaProvider())
    manager.register_provider(GroqProvider())

    return manager
