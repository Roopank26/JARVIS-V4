"""
Friendly error handling for JARVIS.

Maps raw technical exceptions (auth failures, network errors, missing keys,
audio device issues, tool errors) to concise, user-facing messages with a
suggested fix and an optional retry hook. The backend keeps raising normal
exceptions; this layer translates them at the UX boundary only.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FriendlyError:
    """A user-facing error with reason, fix, and optional retry."""

    title: str
    reason: str
    fix: str
    diagnostic: str | None = None
    retry: Callable[[], Any] | None = None
    retry_label: str = "Try again"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "reason": self.reason,
            "fix": self.fix,
            "diagnostic": self.diagnostic,
            "retry_label": self.retry_label,
        }


def _lower(obj: Any) -> str:
    try:
        return str(obj).lower()
    except Exception:
        return ""


def handle_error(
    error: Exception,
    context: str = "",
    retry: Callable[[], Any] | None = None,
) -> FriendlyError:
    """
    Translate an exception into a :class:`FriendlyError`.

    Args:
        error: The raw exception.
        context: Short description of what was happening.
        retry: Optional callable to retry the operation.

    Returns:
        FriendlyError with reason/fix/diagnostic.
    """
    msg = _lower(error)
    context_str = f" while {context}" if context else ""

    # API key / authentication
    if any(
        t in msg
        for t in ["401", "invalid api key", "invalid_api_key", "unauthorized", "authentication"]
    ):
        return FriendlyError(
            title="API key missing or invalid",
            reason="JARVIS couldn't authenticate with the AI provider.",
            fix=(
                "Set a valid API key. For Groq, get a free key at "
                "console.groq.com/keys and add it to ~/.jarvis/api_keys.json "
                "under 'groq_api_key', or export GROQ_API_KEY."
            ),
            diagnostic=str(error),
            retry=retry,
        )

    # Rate limits / quota
    if any(t in msg for t in ["429", "rate limit", "quota", "too many requests"]):
        return FriendlyError(
            title="Rate limit reached",
            reason="The AI provider is temporarily limiting requests.",
            fix="Wait a few moments and try again. Consider switching to a local model via 'switch to ollama'.",
            diagnostic=str(error),
            retry=retry,
        )

    # Network / connectivity
    if any(
        t in msg
        for t in [
            "connection",
            "timeout",
            "timed out",
            "name or service",
            "failed to resolve",
            "503",
            "502",
            "504",
        ]
    ):
        return FriendlyError(
            title="Connection problem",
            reason=f"JARVIS couldn't reach the service{context_str}.",
            fix="Check your internet connection and try again. If using a cloud provider, a local model avoids this entirely.",
            diagnostic=str(error),
            retry=retry,
        )

    # Audio / microphone
    if any(
        t in msg
        for t in [
            "portaudio",
            "sounddevice",
            "no usable input",
            "input device",
            "mic",
            "microphone",
            "4040",
        ]
    ):
        return FriendlyError(
            title="Microphone unavailable",
            reason="No working microphone input was found.",
            fix="Open your OS sound settings, enable a microphone, and grant JARVIS permission to use it. Voice input is optional — you can still type.",
            diagnostic=str(error),
        )

    # Missing optional dependency
    if "importerror" in msg or "modulenotfounderror" in msg or "no module named" in msg:
        missing = _extract_module(str(error))
        return FriendlyError(
            title="Optional feature not installed",
            reason=f"A dependency needed for this feature is missing{context_str}.",
            fix=(
                f"Install it with: pip install {missing}"
                if missing
                else "Install the missing dependency from requirements.txt."
            ),
            diagnostic=str(error),
            retry=retry,
        )

    # Tool execution failure
    if "tool" in msg or context.startswith("running tool"):
        return FriendlyError(
            title="Tool failed",
            reason=f"A tool could not complete{context_str}.",
            fix="Check the inputs and permissions, then retry. Some tools (deletes, terminal) need confirmation.",
            diagnostic=str(error),
            retry=retry,
        )

    # Generic fallback
    return FriendlyError(
        title="Something went wrong",
        reason=f"JARVIS hit an unexpected error{context_str}.",
        fix="You can retry, or type 'status' to check system health.",
        diagnostic=str(error),
        retry=retry,
    )


def _extract_module(error_text: str) -> str:
    import re

    match = re.search(r"no module named '([^']+)'", error_text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"import ([\w\.]+)", error_text)
    if match:
        return match.group(1)
    return ""
