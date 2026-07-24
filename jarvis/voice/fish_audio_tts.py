"""
Fish Audio Text-to-Speech Provider for JARVIS.

Communicates with the Fish Audio S2.1 Pro API to provide
high-quality voice synthesis with streaming support.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import aiohttp

from jarvis.voice.voice_runtime import (
    ComponentInitResult,
    VoiceComponent,
    VoiceComponentStatus,
)

logger = logging.getLogger(__name__)


class TTSProvider(StrEnum):
    """Supported TTS providers."""

    LOCAL = "local"
    FISH_AUDIO = "fish_audio"


@dataclass
class FishAudioConfig:
    """Configuration for Fish Audio TTS."""

    api_key: str = ""
    voice_id: str = ""
    model: str = "s2.1-pro"
    format: str = "wav"
    speed: float = 1.0
    volume: float = 1.0
    emotion: str = ""
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> FishAudioConfig:
        """Load configuration from environment variables."""
        return cls(
            api_key=os.environ.get("FISH_AUDIO_API_KEY", ""),
            voice_id=os.environ.get("FISH_AUDIO_VOICE_ID", ""),
        )

    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        return bool(self.api_key and self.voice_id)

    def validate(self) -> str | None:
        """Validate configuration and return error message if invalid."""
        if not self.api_key:
            return "Fish Audio API key is not configured"
        if not self.voice_id:
            return "Fish Audio voice ID is not configured"
        if not (0.5 <= self.speed <= 2.0):
            return f"Speed must be between 0.5 and 2.0, got {self.speed}"
        if not (0.0 <= self.volume <= 1.0):
            return f"Volume must be between 0.0 and 1.0, got {self.volume}"
        return None


class FishAudioTTS(VoiceComponent):
    """
    Fish Audio Text-to-Speech provider.

    Supports:
    - Fish Audio S2.1 Pro model
    - Streaming audio generation
    - Adjustable speed and volume
    - Emotion/style parameters

    Falls back to local TTS if Fish Audio fails.
    """

    BASE_URL = "https://api.fish.audio/v1"

    def __init__(self, config: FishAudioConfig | None = None):
        super().__init__("FishAudioTTS")
        self.config = config or FishAudioConfig.from_env()
        self._session: Any = None
        self._connection_status: str = "Not initialized"
        self._latency_ms: float = 0.0
        self._request_count: int = 0
        self._success_count: int = 0
        self._failure_count: int = 0
        self._last_error: str | None = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 300.0

    async def initialize(self) -> ComponentInitResult:
        """Initialize the Fish Audio TTS provider."""
        self.status = VoiceComponentStatus.INITIALIZING
        logger.info("Initializing Fish Audio TTS provider...")

        validation_error = self.config.validate()
        if validation_error:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = validation_error
            logger.warning("Fish Audio TTS configuration error: %s", validation_error)
            return ComponentInitResult.fail(validation_error)

        try:
            import aiohttp

            self._session = aiohttp.ClientSession()
            health_ok = await self._check_health()
            if health_ok:
                self.status = VoiceComponentStatus.READY
                self._connection_status = "Connected"
                logger.info(
                    "Fish Audio TTS initialized successfully (model: %s)", self.config.model
                )
                return ComponentInitResult.ok(
                    status=VoiceComponentStatus.READY,
                    message=f"Fish Audio S2.1 Pro connected (voice: {self.config.voice_id})",
                )
            self.status = VoiceComponentStatus.ERROR
            self._connection_status = "Health check failed"
            return ComponentInitResult.fail("Fish Audio health check failed")
        except ImportError as e:
            self.status = VoiceComponentStatus.DISABLED
            self.error_message = f"aiohttp not installed: {e}"
            logger.warning("Fish Audio TTS disabled: aiohttp not installed")
            return ComponentInitResult.fail(str(e), status=VoiceComponentStatus.DISABLED)
        except Exception as e:
            self.status = VoiceComponentStatus.ERROR
            self.error_message = str(e)
            logger.error("Fish Audio TTS initialization failed: %s", e)
            return ComponentInitResult.fail(str(e))

    async def _check_health(self) -> bool:
        """Check if the Fish Audio API is reachable."""
        if not self._session:
            return False
        try:
            start = time.perf_counter()
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            async with self._session.get(
                f"{self.BASE_URL}/health",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                self._latency_ms = (time.perf_counter() - start) * 1000.0
                return resp.status == 200
        except Exception as e:
            logger.debug("Fish Audio health check failed: %s", e)
            return False

    async def speak(self, text: str) -> bytes | None:
        """Synthesize speech for the given text and return audio bytes."""
        if self.status != VoiceComponentStatus.READY:
            logger.debug("Fish Audio TTS not ready")
            return None
        if not text or not text.strip():
            return None

        try:
            audio = await self._synthesize(text)
            if audio:
                self._success_count += 1
                self._request_count += 1
            return audio
        except Exception as e:
            self._failure_count += 1
            self._request_count += 1
            self._last_error = str(e)
            logger.error("Fish Audio TTS synthesis error: %s", e)
            return None

    async def _synthesize(self, text: str) -> bytes | None:
        """Synthesize speech using the Fish Audio API."""
        if not self._session:
            return None

        import aiohttp

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "text": text,
            "reference_id": self.config.voice_id,
            "format": self.config.format,
            "speed": self.config.speed,
            "volume": self.config.volume,
        }
        if self.config.emotion:
            payload["emotion"] = self.config.emotion

        try:
            start = time.perf_counter()
            async with self._session.post(
                f"{self.BASE_URL}/tts",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                self._latency_ms = (time.perf_counter() - start) * 1000.0
                if resp.status == 401:
                    raise PermissionError("Invalid Fish Audio API key")
                if resp.status == 422:
                    error_text = await resp.text()
                    raise ValueError(f"Invalid request parameters: {error_text}")
                if resp.status == 429:
                    raise RuntimeError("Fish Audio rate limit exceeded")
                resp.raise_for_status()
                return await resp.read()
        except TimeoutError:
            raise TimeoutError("Fish Audio synthesis timed out") from None
        except aiohttp.ClientResponseError as e:
            raise RuntimeError(f"Fish Audio API error ({e.status}): {e.message}") from e

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Stream synthesized audio chunks."""
        if self.status != VoiceComponentStatus.READY:
            return

        try:
            audio = await self.speak(text)
            if audio:
                yield audio
        except Exception as e:
            logger.error("Fish Audio streaming error: %s", e)
            return

    async def test_connection(self) -> dict[str, Any]:
        """Test the connection and return status details."""
        if not self.config.is_configured():
            return {
                "connected": False,
                "error": "Not configured: API key or voice ID missing",
                "provider": "fish_audio",
            }

        validation_error = self.config.validate()
        if validation_error:
            return {
                "connected": False,
                "error": validation_error,
                "provider": "fish_audio",
            }

        try:
            await self.initialize()
            if self.status == VoiceComponentStatus.READY:
                test_audio = await self.speak(
                    "Hello Roopank, Fish Audio has been successfully integrated into JARVIS."
                )
                return {
                    "connected": True,
                    "error": None,
                    "provider": "fish_audio",
                    "model": self.config.model,
                    "voice_id": self.config.voice_id,
                    "audio_generated": test_audio is not None and len(test_audio) > 0,
                    "latency_ms": self._latency_ms,
                }
            return {
                "connected": False,
                "error": self.error_message,
                "provider": "fish_audio",
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "provider": "fish_audio",
            }

    def get_status(self) -> dict[str, Any]:
        """Return detailed provider status."""
        return {
            "provider": "fish_audio",
            "status": self.status.value,
            "connection_status": self._connection_status,
            "model": self.config.model,
            "voice_id": self.config.voice_id,
            "configured": self.config.is_configured(),
            "request_count": self._request_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self._success_count / max(1, self._request_count),
            "latency_ms": self._latency_ms,
            "last_error": self._last_error,
            "error_message": self.error_message,
            "speed": self.config.speed,
            "volume": self.config.volume,
        }

    async def shutdown(self) -> None:
        """Shutdown the provider."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self.status = VoiceComponentStatus.NOT_INITIALIZED
        logger.info("Fish Audio TTS shutdown")
