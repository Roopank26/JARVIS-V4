"""
Adaptive Personality Engine for JARVIS.

Adjusts responses based on:
- Context
- Task
- User preferences
- History
- Communication style
- Urgency
- Environment

Maintains consistent personality while adapting behavior.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jarvis.personality.manager import PersonalityManager, PersonalityProfile

logger = logging.getLogger(__name__)


class CommunicationStyle(StrEnum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    DETAILED = "detailed"


class UrgencyLevel(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InteractionHistory:
    user_input: str
    response_style: str
    context: str = ""
    timestamp: float = field(default_factory=time.time)


class AdaptivePersonalityEngine:
    """
    Personality layer that adapts response style based on context and history.
    """

    def __init__(self, base_manager: PersonalityManager | None = None) -> None:
        self._base = base_manager or PersonalityManager()
        self._style: CommunicationStyle = CommunicationStyle.CASUAL
        self._history: list[InteractionHistory] = []
        self._max_history = 200
        self._user_preferences: dict[str, Any] = {
            "preferred_style": CommunicationStyle.CASUAL,
            "verbosity": "medium",
            "formality": 0.3,
            "use_humor": True,
            "use_emojis": False,
            "confirm_actions": True,
        }
        self._environment: dict[str, Any] = {
            "time_of_day": "day",
            "is_work_hours": True,
            "is_voice": False,
            "platform": "cli",
        }

    def adapt(self, context: str = "", task: str = "", urgency: UrgencyLevel = UrgencyLevel.NORMAL) -> PersonalityProfile:
        profile = PersonalityProfile()

        style = self._infer_style(task, context, urgency)
        profile.tone = style.value
        profile.verbosity = self._infer_verbosity(urgency, context)
        profile.use_first_person = True
        profile.confirm_completion = self._user_preferences.get("confirm_actions", True) and urgency != UrgencyLevel.LOW
        profile.avoid_formal = style != CommunicationStyle.FORMAL

        if urgency == UrgencyLevel.CRITICAL:
            profile.verbosity = "concise"
            profile.confirm_completion = False

        return profile

    def apply(self, text: str, context: str = "", task: str = "", urgency: UrgencyLevel = UrgencyLevel.NORMAL) -> str:
        profile = self.adapt(context=context, task=task, urgency=urgency)
        self._base.profile = profile
        response = self._base.get_response(text)
        self._record_history(text, profile.tone, context)
        return response

    def record_feedback(self, user_input: str, response: str, feedback: str | None = None) -> None:
        self._history.append(InteractionHistory(
            user_input=user_input,
            response_style=self._style.value,
            context=feedback or "",
        ))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def set_user_preference(self, key: str, value: Any) -> None:
        self._user_preferences[key] = value

    def get_user_preferences(self) -> dict[str, Any]:
        return dict(self._user_preferences)

    def set_environment(self, **kwargs: Any) -> None:
        self._environment.update(kwargs)

    def _infer_style(self, task: str, context: str, urgency: UrgencyLevel) -> CommunicationStyle:
        combined = f"{task} {context}".lower()
        if urgency in (UrgencyLevel.HIGH, UrgencyLevel.CRITICAL):
            return CommunicationStyle.CONCISE
        if any(k in combined for k in ["api", "code", "debug", "error", "fix", "implement"]):
            return CommunicationStyle.TECHNICAL
        if any(k in combined for k in ["hello", "morning", "good", "ok", "thanks"]):
            return CommunicationStyle.FRIENDLY
        preferred = self._user_preferences.get("preferred_style", CommunicationStyle.CASUAL)
        if isinstance(preferred, str):
            try:
                return CommunicationStyle(preferred)
            except ValueError:
                pass
        return preferred if isinstance(preferred, CommunicationStyle) else CommunicationStyle.CASUAL

    def _infer_verbosity(self, urgency: UrgencyLevel, context: str) -> str:
        if urgency == UrgencyLevel.CRITICAL:
            return "concise"
        if urgency == UrgencyLevel.LOW:
            return "detailed"
        v = self._user_preferences.get("verbosity", "medium")
        if v not in ("concise", "medium", "detailed"):
            v = "medium"
        return v

    def _record_history(self, user_input: str, style: str, context: str) -> None:
        self._history.append(InteractionHistory(user_input=user_input, response_style=style, context=context))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": True,
            "style": self._style.value,
            "history_size": len(self._history),
            "preferences": self._user_preferences,
        }


def get_adaptive_personality() -> AdaptivePersonalityEngine:
    global _default_adaptive
    if "_default_adaptive" not in globals():
        _default_adaptive = AdaptivePersonalityEngine()
    return _default_adaptive
