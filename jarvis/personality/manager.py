"""
Personality Manager for JARVIS.
Controls voice personality, response style, and naturalness preferences.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    tone: str = "natural"
    verbosity: str = "concise"
    use_first_person: bool = True
    confirm_completion: bool = True
    avoid_formal: bool = True
    voice_only_short: bool = True

    def respond_templates(self) -> dict[str, str]:
        return {
            "open_app": "Opening {app}.",
            "close_window": "Closed {window}.",
            "screenshot": "Screenshot saved.",
            "tests_pass": "Your tests completed successfully.",
            "tests_fail": "Your tests finished, but there are failures.",
            "build_complete": "Build complete.",
            "build_fail": "Build failed.",
            "index_complete": "Finished indexing {repo}.",
            "research_done": "Research complete.",
            "task_aborted": "Got it, stopping.",
            "task_switched": "On it.",
        }


class PersonalityManager:
    def __init__(self):
        self.profile = PersonalityProfile()

    def load(self, profile: dict[str, Any] | None = None):
        if profile:
            self.profile.tone = profile.get("tone", self.profile.tone)
            self.profile.verbosity = profile.get("verbosity", self.profile.verbosity)
            self.profile.use_first_person = profile.get("use_first_person", True)
            self.profile.confirm_completion = profile.get("confirm_completion", True)
            self.profile.avoid_formal = profile.get("avoid_formal", True)
            self.profile.voice_only_short = profile.get("voice_only_short", True)

    def get_response(self, action: str, **kwargs) -> str:
        templates = self.profile.respond_templates()
        template = templates.get(action, action)
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    def prefer_short(self, is_voice: bool = False) -> bool:
        if not is_voice:
            return False
        return self.profile.voice_only_short


_manager: PersonalityManager | None = None


def get_personality_manager() -> PersonalityManager:
    global _manager
    if _manager is None:
        _manager = PersonalityManager()
    return _manager
