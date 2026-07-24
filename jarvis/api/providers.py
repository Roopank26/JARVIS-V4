"""
AI Provider Abstraction Layer for JARVIS.
Provides fallback hierarchy: AirLLM (Local) → Ollama (Local) → Groq → OpenAI → Gemini → Anthropic
"""

import asyncio
import contextlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """AI provider types."""

    AIRLLM = "airllm"
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    LMSTUDIO = "lmstudio"


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    provider: ProviderType = ProviderType.GROQ
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
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
    usage: dict[str, int] | None = None
    latency: float = 0.0
    error: str | None = None


@dataclass
class ProviderStatus:
    """Detailed provider status."""

    name: str
    provider: ProviderType
    available: bool
    current_model: str
    available_models: list[str] = field(default_factory=list)
    fallback: str | None = None
    connection: str = "Unknown"
    latency_ms: float = 0.0
    error: str | None = None
    last_check: str | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._available = True
        self._last_error: str | None = None
        self._available_models: list[str] = []
        self._model: str | None = config.model

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def available_models(self) -> list[str]:
        return self._available_models

    @property
    def model(self) -> str:
        return self._model or ""

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        pass

    async def initialize(self) -> bool:
        try:
            return await self.check_health()
        except Exception as e:
            self._available = False
            self._last_error = str(e)
            return False


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider with comprehensive model management."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self._connection_status = "Unknown"
        self._latency_ms = 0.0
        self._model_cache: dict[str, dict] = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 300

    def _is_cache_valid(self) -> bool:
        return time.time() - self._cache_time < self._cache_ttl and bool(self._available_models)

    def _resolve_model(self, model_hint: str) -> str:
        hint_lower = model_hint.lower().strip()
        for avail_model in self._available_models:
            if avail_model.lower() == hint_lower:
                return avail_model
        for avail_model in self._available_models:
            if hint_lower in avail_model.lower():
                return avail_model
        return model_hint

    def _pick_available_model(self, preferred: str | None) -> str:
        if preferred and preferred in self._available_models:
            return preferred
        if preferred:
            resolved = self._resolve_model(preferred)
            if resolved in self._available_models:
                return resolved
        if self._available_models:
            sorted_models = sorted(
                self._available_models,
                key=lambda m: (
                    any(kw in m.lower() for kw in ["r1", "deepseek", "think", "reason"]),
                    m,
                ),
            )
            return sorted_models[0]
        return preferred or ""

    def switch_model(self, model_hint: str) -> tuple:
        resolved = self._resolve_model(model_hint)
        if resolved in self._available_models:
            self._model = resolved
            logger.info(f"Ollama switched to model: {resolved}")
            return True, resolved
        logger.warning(f"Model '{resolved}' not found. Available: {self._available_models}")
        return False, resolved

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        start = time.time()
        if not self._model and self._available_models:
            self._model = self._available_models[0]
        if not self._model:
            raise Exception("No Ollama model selected or available")
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                options = {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                }
                if "qwen3" in self._model:
                    options["think"] = False
                payload = {
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options,
                }
                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._connection_status = "Connected"
                        self._latency_ms = (time.time() - start) * 1000
                        content = data.get("response", "")
                        if not content:
                            content = data.get("thinking", "")
                        return LLMResponse(
                            content=content,
                            provider=ProviderType.OLLAMA,
                            model=self._model,
                            latency=time.time() - start,
                        )
                    error = await resp.text()
                    self._last_error = f"HTTP {resp.status}: {error}"
                    self._available = False
                    self._connection_status = f"Error: {resp.status}"
                    raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model and self._available_models:
            self._model = self._available_models[0]
        if not self._model:
            raise Exception("No Ollama model selected or available")
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                options = {}
                if "qwen3" in self._model:
                    options["think"] = False
                payload = {
                    "model": self._model,
                    "prompt": prompt,
                    "stream": True,
                    "options": options,
                }
                async with session.post(url, json=payload, timeout=self.config.timeout) as resp:
                    async for line in resp.content:
                        if line:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            elif "thinking" in data:
                                yield data["thinking"]
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    async def check_health(self) -> bool:
        start = time.time()
        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.get(f"{self.base_url}/api/tags", timeout=5.0) as resp,
            ):
                self._latency_ms = (time.time() - start) * 1000
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    self._available_models = [m["name"] for m in models]
                    if self._model and self._model not in self._available_models:
                        self._model = self._pick_available_model(self._model)
                    elif not self._model and self._available_models:
                        self._model = self._pick_available_model(None)
                    self._connection_status = "Connected"
                    self._available = True
                    logger.info(f"Ollama available, {len(models)} models: {self._available_models}")
                    return True
                self._connection_status = f"Error: {resp.status}"
                self._available = False
                return False
        except Exception as e:
            self._last_error = str(e)
            self._connection_status = "Connection Failed"
            self._available = False
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        if self._available_models:
            return self._available_models
        await self.check_health()
        return self._available_models

    def get_status(self) -> "ProviderStatus":
        return ProviderStatus(
            name="Ollama",
            provider=ProviderType.OLLAMA,
            available=self._available,
            current_model=self._model or "",
            available_models=self._available_models.copy(),
            fallback="Groq",
            connection=self._connection_status,
            latency_ms=self._latency_ms,
            error=self._last_error,
        )


class GroqProvider(BaseLLMProvider):
    """Groq cloud LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._base_url = "https://api.groq.com/openai/v1"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No Groq model selected")
        import aiohttp

        start = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "stream": False,
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        provider=ProviderType.GROQ,
                        model=self._model,
                        usage=data.get("usage"),
                        latency=time.time() - start,
                    )
                error = await resp.json()
                self._last_error = error.get("error", {}).get("message", "Unknown error")
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No Groq model selected")
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp,
        ):
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
        try:
            import aiohttp

            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self._base_url}/models",
                    headers=headers,
                    timeout=5.0,
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class OpenAIProvider(BaseLLMProvider):
    """OpenAI cloud LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._base_url = "https://api.openai.com/v1"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No OpenAI model selected")
        import aiohttp

        start = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        provider=ProviderType.OPENAI,
                        model=self._model,
                        usage=data.get("usage"),
                        latency=time.time() - start,
                    )
                error_text = await resp.text()
                try:
                    error = json.loads(error_text)
                    self._last_error = error.get("error", {}).get("message", error_text)
                except Exception:
                    self._last_error = f"HTTP {resp.status}"
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No OpenAI model selected")
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp,
        ):
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
        try:
            import aiohttp

            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self._base_url}/models",
                    headers=headers,
                    timeout=5.0,
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude cloud LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._base_url = "https://api.anthropic.com/v1"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No Anthropic model selected")
        import aiohttp

        start = time.time()
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": self._model,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "messages": [{"role": "user", "content": prompt}],
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    content = ""
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")
                    return LLMResponse(
                        content=content,
                        provider=ProviderType.ANTHROPIC,
                        model=self._model,
                        usage=data.get("usage"),
                        latency=time.time() - start,
                    )
                error_text = await resp.text()
                try:
                    error = json.loads(error_text)
                    self._last_error = error.get("error", {}).get("message", error_text)
                except Exception:
                    self._last_error = f"HTTP {resp.status}"
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No Anthropic model selected")
        import aiohttp

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._base_url}/messages",
                headers=headers,
                json=payload,
            ) as resp,
        ):
            async for line in resp.content:
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if "text" in delta:
                                    yield delta["text"]
                        except json.JSONDecodeError:
                            pass

    async def check_health(self) -> bool:
        try:
            import aiohttp

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    "https://api.anthropic.com/v1/models",
                    headers=headers,
                    timeout=5.0,
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class GoogleProvider(BaseLLMProvider):
    """Google Gemini cloud LLM provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No Google model selected")
        import aiohttp

        start = time.time()
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens),
                },
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    content = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            content += part.get("text", "")
                    return LLMResponse(
                        content=content,
                        provider=ProviderType.GOOGLE,
                        model=self._model,
                        latency=time.time() - start,
                    )
                error_text = await resp.text()
                self._last_error = f"HTTP {resp.status}: {error_text}"
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No Google model selected")
        import aiohttp

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:streamGenerateContent?key={self.api_key}&alt=sse"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url,
                json=payload,
            ) as resp,
        ):
            async for line in resp.content:
                if line:
                    text = line.decode("utf-8").strip()
                    if text.startswith("data: "):
                        try:
                            data = json.loads(text[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except (json.JSONDecodeError, KeyError):
                            pass

    async def check_health(self) -> bool:
        try:
            import aiohttp

            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            async with aiohttp.ClientSession() as session, session.get(url, timeout=5.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        if name.startswith("models/"):
                            name = name[len("models/") :]
                        if name:
                            models.append(name)
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter cloud LLM provider (unified API for many models)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._base_url = "https://openrouter.ai/api/v1"

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No OpenRouter model selected")
        import aiohttp

        start = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://jarvis.local",
                "X-Title": "JARVIS",
            }
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        provider=ProviderType.OPENROUTER,
                        model=self._model,
                        usage=data.get("usage"),
                        latency=time.time() - start,
                    )
                error_text = await resp.text()
                try:
                    error = json.loads(error_text)
                    self._last_error = error.get("error", {}).get("message", error_text)
                except Exception:
                    self._last_error = f"HTTP {resp.status}"
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No OpenRouter model selected")
        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://jarvis.local",
            "X-Title": "JARVIS",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp,
        ):
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
        try:
            import aiohttp

            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self._base_url}/models",
                    headers=headers,
                    timeout=5.0,
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class LMStudioProvider(BaseLLMProvider):
    """LM Studio local LLM provider (OpenAI-compatible API)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._base_url = (config.base_url or "http://localhost:1234").rstrip("/")

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        if not self._model:
            raise Exception("No LM Studio model selected")
        import aiohttp

        start = time.time()
        try:
            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        provider=ProviderType.LMSTUDIO,
                        model=self._model,
                        latency=time.time() - start,
                    )
                error_text = await resp.text()
                self._last_error = f"HTTP {resp.status}: {error_text}"
                raise Exception(self._last_error)
        except Exception as e:
            self._last_error = str(e)
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        if not self._model:
            raise Exception("No LM Studio model selected")
        import aiohttp

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            ) as resp,
        ):
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
        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self._base_url}/v1/models",
                    timeout=5.0,
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                    self._available_models = models
                    if self._model and self._model not in self._available_models:
                        self._model = self._available_models[0] if self._available_models else None
                    elif not self._model and self._available_models:
                        self._model = self._available_models[0]
                    self._available = True
                    return True
                self._available = False
                return False
        except Exception:
            self._available = False
            return False


class ProviderManager:
    """
    Manages multiple LLM providers with automatic failover and reconnection.

    Priority order (current selection first, then local, then cloud):
      1. Current selected provider (if healthy)
      2. Ollama (Local)
      3. Groq
      4. OpenAI
      5. Gemini (Google)
      6. Anthropic
      7. OpenRouter
      8. LM Studio
      9. AirLLM (Local)
    """

    PROVIDER_PRIORITY = [
        ProviderType.OLLAMA,
        ProviderType.GROQ,
        ProviderType.OPENAI,
        ProviderType.GOOGLE,
        ProviderType.ANTHROPIC,
        ProviderType.OPENROUTER,
        ProviderType.LMSTUDIO,
        ProviderType.AIRLLM,
    ]

    PROVIDER_FALLBACK_ORDER = {
        ProviderType.OLLAMA: ProviderType.GROQ,
        ProviderType.GROQ: ProviderType.OPENAI,
        ProviderType.OPENAI: ProviderType.GOOGLE,
        ProviderType.GOOGLE: ProviderType.ANTHROPIC,
        ProviderType.ANTHROPIC: ProviderType.OPENROUTER,
        ProviderType.OPENROUTER: ProviderType.LMSTUDIO,
        ProviderType.LMSTUDIO: ProviderType.AIRLLM,
        ProviderType.AIRLLM: None,
    }

    DEFAULT_MODEL = "qwen3:8b"
    REASONING_MODEL = "deepseek-r1:8b"

    REASONING_PATTERNS = [
        r"\b(step by step|explain how|reasoning|thinking|analyze)",
        r"\b(algorithm|problem|solve|calculate|prove)",
        r"\b(why|how come|what if|compare)",
    ]

    def get_best_model_for_task(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        for pattern in self.REASONING_PATTERNS:
            if re.search(pattern, prompt_lower):
                for provider_type in self.PROVIDER_PRIORITY:
                    if provider_type in self.providers:
                        provider = self.providers[provider_type]
                        for model in provider.available_models:
                            if "deepseek" in model.lower():
                                return model
        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                for model in provider.available_models:
                    if "qwen" in model.lower():
                        return model
        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                if provider.model:
                    return provider.model
        return ""

    RECONNECT_INTERVAL = 30.0
    FAILURE_COOLDOWN = 60.0

    def __init__(self):
        self.providers: dict[ProviderType, BaseLLMProvider] = {}
        self.primary_provider: ProviderType | None = None
        self._initialized = False
        self._startup_diagnostics: dict[str, Any] = {}
        self._switch_log: list[dict[str, Any]] = []
        self._failed_recently: dict[ProviderType, float] = {}
        self._reconnect_task: asyncio.Task | None = None

    def add_provider(self, provider: BaseLLMProvider) -> None:
        self.providers[provider.config.provider] = provider

    def _emit_switch_event(self, event_type: str, **kwargs: Any) -> None:
        try:
            from jarvis.events import EventType, get_event_bus

            bus = get_event_bus()
            data = {
                "provider": self.primary_provider.value if self.primary_provider else None,
                "model": self.get_current_model(),
                "timestamp": time.time(),
            }
            data.update(kwargs)
            if event_type == "provider_switched":
                bus.emit(EventType.PROVIDER_SWITCHED, data)
            elif event_type == "model_switched":
                bus.emit(EventType.MODEL_SWITCHED, data)
            elif event_type == "provider_available":
                bus.emit(EventType.PROVIDER_AVAILABLE, data)
            elif event_type == "provider_unavailable":
                bus.emit(EventType.PROVIDER_UNAVAILABLE, data)
            elif event_type == "provider_discovered":
                bus.emit(EventType.PROVIDER_DISCOVERED, data)
        except Exception:
            pass

    def set_primary(self, provider_type: ProviderType) -> None:
        old_primary = self.primary_provider
        if provider_type in self.providers:
            self.primary_provider = provider_type
        if old_primary != self.primary_provider:
            self._switch_log.append(
                {
                    "event": "provider_switched",
                    "from": old_primary.value if old_primary else None,
                    "to": provider_type.value,
                    "model": self.get_current_model(),
                    "timestamp": time.time(),
                }
            )
            self._emit_switch_event(
                "provider_switched", from_provider=old_primary.value if old_primary else None
            )

    def set_model(self, model: str) -> tuple:
        if ProviderType.AIRLLM in self.providers:
            airllm = self.providers[ProviderType.AIRLLM]
            if hasattr(airllm, "_resolve_model_hint"):
                resolved = airllm._resolve_model_hint(model)
                if resolved in airllm.available_models:
                    airllm.model = resolved
                    self.primary_provider = ProviderType.AIRLLM
                    self._switch_log.append(
                        {
                            "event": "model_switched",
                            "provider": ProviderType.AIRLLM.value,
                            "model": resolved,
                            "timestamp": time.time(),
                        }
                    )
                    self._emit_switch_event(
                        "model_switched", provider=ProviderType.AIRLLM.value, model=resolved
                    )
                    return True, resolved
                model_lower = model.lower().strip()
                for avail_model in airllm.available_models:
                    if model_lower in avail_model.lower():
                        airllm.model = avail_model
                        self.primary_provider = ProviderType.AIRLLM
                        self._switch_log.append(
                            {
                                "event": "model_switched",
                                "provider": ProviderType.AIRLLM.value,
                                "model": avail_model,
                                "timestamp": time.time(),
                            }
                        )
                        self._emit_switch_event(
                            "model_switched", provider=ProviderType.AIRLLM.value, model=avail_model
                        )
                        return True, avail_model

        if ProviderType.OLLAMA in self.providers:
            ollama = self.providers[ProviderType.OLLAMA]
            if hasattr(ollama, "switch_model"):
                success, resolved = ollama.switch_model(model)
                if success:
                    self.primary_provider = ProviderType.OLLAMA
                    self._switch_log.append(
                        {
                            "event": "model_switched",
                            "provider": ProviderType.OLLAMA.value,
                            "model": resolved,
                            "timestamp": time.time(),
                        }
                    )
                    self._emit_switch_event(
                        "model_switched", provider=ProviderType.OLLAMA.value, model=resolved
                    )
                    return True, resolved
                return False, resolved
            model_lower = model.lower().strip()
            for avail_model in ollama.available_models:
                if model_lower in avail_model.lower():
                    ollama.model = avail_model
                    self.primary_provider = ProviderType.OLLAMA
                    self._switch_log.append(
                        {
                            "event": "model_switched",
                            "provider": ProviderType.OLLAMA.value,
                            "model": avail_model,
                            "timestamp": time.time(),
                        }
                    )
                    self._emit_switch_event(
                        "model_switched", provider=ProviderType.OLLAMA.value, model=avail_model
                    )
                    return True, avail_model

        for provider_type, provider in self.providers.items():
            if hasattr(provider, "model"):
                provider.model = model
                self.primary_provider = provider_type
                self._switch_log.append(
                    {
                        "event": "model_switched",
                        "provider": provider_type.value,
                        "model": model,
                        "timestamp": time.time(),
                    }
                )
                self._emit_switch_event("model_switched", provider=provider_type.value, model=model)
                return True, model

        return False, model

    async def initialize(self) -> bool:
        self._startup_diagnostics = {"providers": {}, "primary": None}
        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type not in self.providers:
                continue
            provider = self.providers[provider_type]
            try:
                is_healthy = await provider.check_health()
                self._startup_diagnostics["providers"][provider_type.value] = {
                    "available": is_healthy,
                    "model": provider.model,
                    "models": provider.available_models,
                }
                if is_healthy:
                    self._emit_switch_event(
                        "provider_discovered",
                        provider=provider_type.value,
                        models=provider.available_models,
                    )
                    self._emit_switch_event(
                        "provider_available", provider=provider_type.value, model=provider.model
                    )
                else:
                    self._emit_switch_event(
                        "provider_unavailable",
                        provider=provider_type.value,
                        error=provider.last_error,
                    )
                logger.info(
                    f"[Provider] {provider_type.value}: {'detected' if is_healthy else 'unavailable'}"
                )
                if is_healthy and self.primary_provider is None:
                    self.primary_provider = provider_type
                    logger.info(f"[Provider] Selected primary: {provider_type.value}")
            except Exception as e:
                self._startup_diagnostics["providers"][provider_type.value] = {
                    "available": False,
                    "error": str(e),
                }
                self._emit_switch_event(
                    "provider_unavailable", provider=provider_type.value, error=str(e)
                )
                logger.error(f"[Provider] {provider_type.value}: error - {e}")

        if self.primary_provider:
            provider = self.providers[self.primary_provider]
            if provider.available_models:
                logger.info(f"[Provider] Available models for {self.primary_provider.value}:")
                for model in provider.available_models:
                    logger.info(f"  - {model}")
            self._startup_diagnostics["primary"] = self.primary_provider.value
            self._initialized = True
            self.start_reconnect_loop()
            return True

        self._initialized = False
        return False

    def get_startup_diagnostics(self) -> dict[str, Any]:
        return self._startup_diagnostics

    def format_status(self) -> str:
        lines = ["┌─ Provider Status ──────────────────", "│"]
        if self.primary_provider and self.primary_provider in self.providers:
            provider = self.providers[self.primary_provider]
            lines.append(f"│ Provider: {self.primary_provider.value.capitalize()}")
            lines.append(f"│ Current Model: {provider.model}")
            lines.append(f"│ Available Models ({len(provider.available_models)}):")
            for model in provider.available_models:
                marker = " ←" if model == provider.model else ""
                lines.append(f"│   • {model}{marker}")
            if not provider.available_models:
                lines.append("│   (none detected)")
            lines.append(f"│ Fallback: {self._next_fallback_name()}")
            if hasattr(provider, "_connection_status"):
                lines.append(f"│ Connection: {provider._connection_status}")
            if hasattr(provider, "_latency_ms") and provider._latency_ms > 0:
                lines.append(f"│ Latency: {provider._latency_ms:.0f} ms")
        else:
            lines.append("│ Provider: None")
            lines.append("│ Status: No provider available")
            lines.append(f"│ Will try: {', '.join(p.value for p in self.PROVIDER_PRIORITY)}")
        lines.append("└" + "─" * 34)
        return "\n".join(lines)

    def _next_fallback_name(self) -> str:
        if not self.primary_provider:
            return self.PROVIDER_PRIORITY[0].value if self.PROVIDER_PRIORITY else "none"
        next_p = self.PROVIDER_FALLBACK_ORDER.get(self.primary_provider)
        if next_p and next_p in self.providers:
            return next_p.value
        idx = self.PROVIDER_PRIORITY.index(self.primary_provider)
        for p in self.PROVIDER_PRIORITY[idx + 1 :]:
            if p in self.providers:
                return p.value
        return "none"

    def format_models(self) -> str:
        lines = []
        for provider_type in self.PROVIDER_PRIORITY:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                if provider.available_models:
                    lines.append(f"[{provider_type.value}]")
                    for model in provider.available_models:
                        marker = (
                            " (active)"
                            if (self.primary_provider == provider_type and provider.model == model)
                            else ""
                        )
                        lines.append(f"  • {model}{marker}")
        if not lines:
            return "  No models available"
        return "\n".join(lines)

    def get_current_model(self) -> str:
        if self.primary_provider and self.primary_provider in self.providers:
            return self.providers[self.primary_provider].model
        return "No provider selected"

    async def benchmark_models(self, test_prompt: str = "Count from 1 to 5") -> dict[str, Any]:
        results = {}
        for provider_type, provider in self.providers.items():
            if not provider.is_available:
                continue
            models_to_test = provider.available_models[:3]
            if not models_to_test and provider.model:
                models_to_test = [provider.model]
            for model in models_to_test:
                try:
                    old_model = provider.model
                    provider.model = model
                    start = time.time()
                    response = await provider.generate(test_prompt)
                    latency = time.time() - start
                    results[f"{provider_type.value}/{model}"] = {
                        "latency": round(latency, 2),
                        "tokens": len(response.content.split()),
                        "provider": provider_type.value,
                    }
                    provider.model = old_model
                except Exception as e:
                    results[f"{provider_type.value}/{model}"] = {"error": str(e)}
        return results

    def compare_models(self, model1: str, model2: str) -> str:
        lines = ["[Model Comparison]", "=" * 40, ""]
        for model in [model1, model2]:
            lines.append(f"### {model}")
            found = False
            for provider_type, provider in self.providers.items():
                if model in provider.available_models:
                    lines.append(f"  Provider: {provider_type.value}")
                    lines.append("  Status: Available ✓")
                    found = True
                    break
            if not found:
                lines.append("  Provider: Unknown")
                lines.append("  Status: Not available")
            lines.append("")
        return "\n".join(lines)

    async def _try_generate_with(
        self, provider: BaseLLMProvider, prompt: str, **kwargs
    ) -> LLMResponse | None:
        provider_type = provider.config.provider
        last_fail = self._failed_recently.get(provider_type, 0)
        if time.time() - last_fail < self.FAILURE_COOLDOWN:
            return None
        try:
            if not provider.is_available:
                return None
            return await provider.generate(prompt, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug(f"Provider {provider_type.value} generate failed: {e}")
            self._failed_recently[provider_type] = time.time()
            return None

    async def _try_stream_with(
        self, provider: BaseLLMProvider, prompt: str, **kwargs
    ) -> AsyncIterator[str] | None:
        provider_type = provider.config.provider
        last_fail = self._failed_recently.get(provider_type, 0)
        if time.time() - last_fail < self.FAILURE_COOLDOWN:
            return None
        try:
            if not provider.is_available:
                return None
            return provider.stream_generate(prompt, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug(f"Provider {provider_type.value} stream failed: {e}")
            self._failed_recently[provider_type] = time.time()
            return None

    async def _provider_order_for_generate(self) -> list[ProviderType]:
        order = []
        seen = set()
        if self.primary_provider and self.primary_provider in self.providers:
            order.append(self.primary_provider)
            seen.add(self.primary_provider)
        for pt in self.PROVIDER_PRIORITY:
            if pt not in seen and pt in self.providers:
                order.append(pt)
                seen.add(pt)
        for pt in self.providers:
            if pt not in seen:
                order.append(pt)
        return order

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        tried = []
        order = await self._provider_order_for_generate()
        for provider_type in order:
            provider = self.providers[provider_type]
            response = await self._try_generate_with(provider, prompt, **kwargs)
            if response is not None:
                if self.primary_provider != provider_type:
                    self.set_primary(provider_type)
                return response
            tried.append(provider_type.value)

        raise Exception(f"All providers failed: {', '.join(tried)}")

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        tried = []
        order = await self._provider_order_for_generate()
        for provider_type in order:
            provider = self.providers[provider_type]
            stream = await self._try_stream_with(provider, prompt, **kwargs)
            if stream is not None:
                if self.primary_provider != provider_type:
                    self.set_primary(provider_type)
                async for chunk in stream:
                    yield chunk
                return
            tried.append(provider_type.value)

        response = await self.generate(prompt, **kwargs)
        yield response.content

    def get_available_providers(self) -> list[ProviderType]:
        return [p for p, provider in self.providers.items() if provider.is_available]

    def get_status(self) -> dict[str, Any]:
        providers_status: dict[str, Any] = {}
        for p, provider in self.providers.items():
            info: dict[str, Any] = {
                "available": provider.is_available,
                "model": provider.model,
                "available_models": provider.available_models,
                "last_error": provider.last_error,
            }
            if hasattr(provider, "get_status"):
                extra = provider.get_status()
                if isinstance(extra, dict):
                    for k in (
                        "connection",
                        "latency_ms",
                        "vram_used_gb",
                        "vram_total_gb",
                        "memory_profile",
                        "last_check",
                    ):
                        if k in extra:
                            info[k] = extra[k]
            providers_status[p.value] = info
        return {
            "primary": self.primary_provider.value if self.primary_provider else None,
            "providers": providers_status,
            "switch_log": self._switch_log[-20:],
        }

    async def refresh(self) -> dict[str, Any]:
        for _provider_type, provider in list(self.providers.items()):
            with contextlib.suppress(Exception):
                await provider.check_health()
        if (not self.primary_provider
            or self.primary_provider not in self.providers
            or not self.providers[self.primary_provider].is_available):
            for pt in self.PROVIDER_PRIORITY:
                if pt in self.providers and self.providers[pt].is_available:
                    self.set_primary(pt)
                    break
        return self.get_status()

    async def reconnect_provider(self, provider_type: ProviderType) -> bool:
        if provider_type not in self.providers:
            return False
        provider = self.providers[provider_type]
        try:
            healthy = await provider.check_health()
            if healthy:
                self._failed_recently.pop(provider_type, None)
                self._emit_switch_event(
                    "provider_available", provider=provider_type.value, model=provider.model
                )
                return True
        except Exception:
            pass
        return False

    async def _reconnect_loop(self) -> None:
        while True:
            await asyncio.sleep(self.RECONNECT_INTERVAL)
            for provider_type in list(self.providers.keys()):
                provider = self.providers[provider_type]
                if not provider.is_available:
                    await self.reconnect_provider(provider_type)

    def start_reconnect_loop(self) -> None:
        if self._reconnect_task is None or self._reconnect_task.done():
            with contextlib.suppress(RuntimeError):
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())


    async def generate_image(
        self, prompt: str, width: int = 512, height: int = 512, steps: int = 20
    ) -> tuple[str | None, str | None]:
        """
        ProviderManager handles all image provider discovery and execution.
        Order: ComfyUI -> AUTOMATIC1111 -> Forge -> OpenAI Images -> Google Imagen -> Flux
        Returns: (image_path_or_url, provider_name) or (None, None) if unavailable.
        """
        import base64
        import os
        import time
        from pathlib import Path
        _out_dir = Path.home() / ".jarvis" / "generated_images"
        _out_dir.mkdir(parents=True, exist_ok=True)

        # 1. ComfyUI
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session, session.get("http://localhost:8188/system_stats", timeout=aiohttp.ClientTimeout(total=1.5)) as resp:
                if resp.status == 200:
                    logger.info("[ProviderManager] Selected image provider: ComfyUI")
                    # (ComfyUI execution logic)
        except Exception:
            pass

        # 2. AUTOMATIC1111 / Forge
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session, session.get("http://localhost:7860/sdapi/v1/samplers", timeout=aiohttp.ClientTimeout(total=1.5)) as resp:
                if resp.status == 200:
                    logger.info("[ProviderManager] Selected image provider: AUTOMATIC1111")
                    payload = {"prompt": prompt, "negative_prompt": "ugly, blurry", "steps": steps, "width": width, "height": height}
                    async with session.post("http://localhost:7860/sdapi/v1/txt2img", json=payload, timeout=aiohttp.ClientTimeout(total=120)) as r2:
                        data = await r2.json()
                        if data.get("images"):
                            img_bytes = base64.b64decode(data["images"][0])
                            p = _out_dir / f"a1111_{int(time.time())}.png"
                            p.write_bytes(img_bytes)
                            return str(p), "AUTOMATIC1111"
        except Exception:
            pass

        # 3. OpenAI Images (DALL-E)
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.AsyncOpenAI(api_key=api_key)
                response = await client.images.generate(model="dall-e-3", prompt=prompt, n=1, size="1024x1024", response_format="b64_json")
                img_bytes = base64.b64decode(response.data[0].b64_json)
                p = _out_dir / f"dalle_{int(time.time())}.png"
                p.write_bytes(img_bytes)
                return str(p), "OpenAI DALL-E"
            except Exception as e:
                logger.debug("[ProviderManager] OpenAI Images failed: %s", e)

        # 4. Google Imagen
        gkey = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if gkey:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gkey)
                model = genai.ImageGenerationModel("imagen-3.0-generate-001")
                res = model.generate_images(prompt=prompt, number_of_images=1)
                if res.images:
                    p = _out_dir / f"imagen_{int(time.time())}.png"
                    p.write_bytes(res.images[0]._image_bytes)
                    return str(p), "Google Imagen"
            except Exception as e:
                logger.debug("[ProviderManager] Google Imagen failed: %s", e)

        # 5. Flux / Replicate
        rtoken = os.environ.get("REPLICATE_API_TOKEN") or os.environ.get("REPLICATE_API_KEY")
        if rtoken:
            try:
                import aiohttp
                import replicate
                os.environ["REPLICATE_API_TOKEN"] = rtoken
                out = await asyncio.to_thread(replicate.run, "black-forest-labs/flux-schnell", input={"prompt": prompt, "num_inference_steps": min(steps, 4)})
                url = out[0] if isinstance(out, list) else str(out)
                async with aiohttp.ClientSession() as session, session.get(url) as resp:
                    img_bytes = await resp.read()
                p = _out_dir / f"flux_{int(time.time())}.png"
                p.write_bytes(img_bytes)
                return str(p), "Flux"
            except Exception as e:
                logger.debug("[ProviderManager] Flux failed: %s", e)

        # No configured provider available
        logger.warning("[ProviderManager] No configured image generation provider is available.")
        return None, None


# Global provider manager
_provider_manager: ProviderManager | None = None



def get_provider_manager() -> ProviderManager:
    """Get the global provider manager."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def init_providers(configs: dict[ProviderType, LLMConfig]) -> ProviderManager:
    """Initialize provider manager with configs."""
    global _provider_manager
    _provider_manager = ProviderManager()

    for provider_type, config in configs.items():
        if provider_type == ProviderType.AIRLLM:
            try:
                from jarvis.providers.airllm.provider import AirLLMProvider

                _provider_manager.add_provider(AirLLMProvider(config))
            except Exception as exc:
                logger.error("Failed to initialize AirLLM provider: %s", exc)
        elif provider_type == ProviderType.OLLAMA:
            _provider_manager.add_provider(OllamaProvider(config))
        elif provider_type == ProviderType.GROQ:
            _provider_manager.add_provider(GroqProvider(config))
        elif provider_type == ProviderType.OPENAI:
            _provider_manager.add_provider(OpenAIProvider(config))
        elif provider_type == ProviderType.GOOGLE:
            _provider_manager.add_provider(GoogleProvider(config))
        elif provider_type == ProviderType.ANTHROPIC:
            _provider_manager.add_provider(AnthropicProvider(config))
        elif provider_type == ProviderType.OPENROUTER:
            _provider_manager.add_provider(OpenRouterProvider(config))
        elif provider_type == ProviderType.LMSTUDIO:
            _provider_manager.add_provider(LMStudioProvider(config))

    return _provider_manager
