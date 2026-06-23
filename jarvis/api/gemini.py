"""
Gemini API client for JARVIS.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional


class GeminiClient:
    """
    Client for Google's Gemini API.
    Supports both text and multimodal interactions.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self._client = None

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config or environment."""
        # Check environment
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            return api_key

        # Check config file
        config_dir = Path.home() / ".jarvis"
        config_path = config_dir / "api_keys.json"

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    keys = json.load(f)
                    return keys.get("gemini_api_key")
            except Exception:
                pass

        return None

    def _ensure_client(self):
        """Ensure the API client is initialized."""
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                print("[Gemini] google-genai not installed")
                return None
        return self._client

    async def generate(
        self,
        system: str = "",
        prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = "gemini-2.0-flash"
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
            full_prompt = f"{system}\n\n{prompt}" if system else prompt

            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

            return response.text

        except Exception as e:
            print(f"[Gemini] Generation error: {e}")
            return f"Error: {e}"

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: str = "gemini-2.0-flash"
    ) -> str:
        """
        Generate response with conversation history.

        Args:
            messages: List of {"role": "user"/"model", "content": "..."}
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
            contents = []

            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

            config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            if system:
                config["system_instruction"] = system

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )

            return response.text

        except Exception as e:
            print(f"[Gemini] Generation error: {e}")
            return f"Error: {e}"

    def is_available(self) -> bool:
        """Check if the API client is available."""
        return self._ensure_client() is not None and self.api_key is not None


class SimpleLLMClient:
    """
    Simple LLM client that can work with different backends.
    Falls back to a simple echo if no API is available.
    """

    def __init__(self, backend: str = "gemini", **kwargs):
        self.backend = backend.lower()
        self.config = kwargs

        if backend == "gemini":
            self._client = GeminiClient(api_key=kwargs.get("api_key"))
        else:
            self._client = None

    async def generate(
        self,
        system: str = "",
        prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Generate a response."""
        if hasattr(self._client, "generate"):
            return await self._client.generate(
                system=system,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

        # Fallback for testing
        return f"[Echo] {prompt[:100]}..."

    async def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Generate response with history."""
        if hasattr(self._client, "generate_with_history"):
            return await self._client.generate_with_history(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens
            )

        # Fallback
        last_msg = messages[-1] if messages else {"content": ""}
        return f"[Echo] {last_msg.get('content', '')[:100]}..."

    def is_available(self) -> bool:
        """Check if client is available."""
        if hasattr(self._client, "is_available"):
            return self._client.is_available()
        return True  # Echo fallback is always available
