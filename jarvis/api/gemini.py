"""
LLM API client for JARVIS.
Supports Groq (primary) with Gemini fallback.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default model for Groq
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    """
    Client for Groq API.
    Fast inference with llama models.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self._client = None

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config or environment."""
        # Check environment
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            return api_key

        # Check config file
        config_dir = Path.home() / ".jarvis"
        config_path = config_dir / "api_keys.json"

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    keys = json.load(f)
                    return keys.get("groq_api_key") or keys.get("groq")
            except Exception:
                pass

        # Legacy Gemini key check
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    keys = json.load(f)
                    # Also accept gemini key as fallback
                    return keys.get("gemini_api_key")
            except Exception:
                pass

        return None

    def _ensure_client(self):
        """Ensure the API client is initialized."""
        if self._client is None and self.api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info("[Groq] Client initialized")
            except ImportError:
                logger.warning("[Groq] groq package not installed. Run: pip install groq")
                return None
        return self._client

    async def generate(
        self,
        system: str = "",
        prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = DEFAULT_MODEL
    ) -> str:
        """
        Generate a text response.

        Args:
            system: System prompt
            prompt: User prompt
            temperature: Response creativity (0-1)
            max_tokens: Maximum response length
            model: Model to use

        Returns:
            Generated text response
        """
        client = self._ensure_client()
        if client is None:
            return "API client not available"

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[Groq] Generation error: {e}")
            return f"Error: {e}"

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = DEFAULT_MODEL
    ) -> str:
        """
        Generate response with conversation history.

        Args:
            messages: List of {"role": "user"/"assistant", "content": "..."}
            system: System prompt
            temperature: Response creativity
            max_tokens: Maximum response length
            model: Model to use

        Returns:
            Generated text response
        """
        client = self._ensure_client()
        if client is None:
            return "API client not available"

        try:
            chat_messages = []

            # Add system prompt
            if system:
                chat_messages.append({"role": "system", "content": system})

            # Add conversation history
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                chat_messages.append({"role": role, "content": msg["content"]})

            response = client.chat.completions.create(
                model=model,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[Groq] Generation error: {e}")
            return f"Error: {e}"

    def is_available(self) -> bool:
        """Check if the API client is available."""
        return self._ensure_client() is not None and self.api_key is not None


# Backward compatibility alias
GeminiClient = GroqClient


class SimpleLLMClient:
    """
    Simple LLM client that can work with different backends.
    Defaults to Groq, falls back to echo for testing.
    """

    def __init__(self, backend: str = "groq", **kwargs):
        self.backend = backend.lower()
        self.config = kwargs

        if backend == "groq":
            self._client = GroqClient(api_key=kwargs.get("api_key"))
        elif backend == "gemini":
            # Legacy Gemini support (if key exists)
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if gemini_key:
                try:
                    from google import genai
                    self._client = GeminiClient(api_key=gemini_key)
                except ImportError:
                    self._client = None
            else:
                self._client = GroqClient(api_key=kwargs.get("api_key"))
        else:
            self._client = GroqClient(api_key=kwargs.get("api_key"))

    async def generate(
        self,
        system: str = "",
        prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = DEFAULT_MODEL
    ) -> str:
        """Generate a response."""
        if hasattr(self._client, "generate"):
            return await self._client.generate(
                system=system,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model
            )

        # Fallback for testing
        return f"[Echo] {prompt[:100]}..."

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = DEFAULT_MODEL
    ) -> str:
        """Generate response with history."""
        if hasattr(self._client, "generate_with_history"):
            return await self._client.generate_with_history(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model
            )

        # Fallback
        last_msg = messages[-1] if messages else {"content": ""}
        return f"[Echo] {last_msg.get('content', '')[:100]}..."

    def is_available(self) -> bool:
        """Check if client is available."""
        if hasattr(self._client, "is_available"):
            return self._client.is_available()
        return True  # Echo fallback is always available
