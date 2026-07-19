"""
Enhanced Memory Manager for JARVIS.
Integrates user profile with long-term and session memory.
"""

import re
from typing import Any

from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.user_profile import UserProfile, get_user_profile


class EnhancedMemoryManager:
    """
    Enhanced memory manager with user profile integration.

    Features:
    - User profile with structured categories
    - Natural language profile extraction
    - Profile summary generation
    - Profile-aware responses
    """

    # Patterns for detecting profile-related queries
    WHO_AM_I_PATTERNS = [
        r"who\s+am\s+i",
        r"what\s+do\s+you\s+know\s+about\s+me",
        r"tell\s+me\s+about\s+myself",
        r"my\s+profile",
        r"summarize\s+(?:my\s+)?(?:profile|info|information)",
        r"what\s+(?:are\s+)?my\s+(?:details?|facts?)",
    ]

    # Patterns for detecting profile updates
    PROFILE_UPDATE_PATTERNS = [
        r"(?:remember|note|save)\s+(?:that\s+)?(?:my\s+)?",
        r"i\s+am\s+(?:a|an)?",
        r"my\s+\w+\s+is\s+",
        r"(?:my name|my age|my city|i study|i work|i live|i like|i prefer)",
    ]

    def __init__(
        self, memory_manager: MemoryManager | None = None, user_profile: UserProfile | None = None
    ):
        self.memory = memory_manager or MemoryManager()
        self.profile = user_profile or get_user_profile()

    def is_profile_query(self, text: str) -> bool:
        """Check if text is a profile-related query."""
        text_lower = text.lower().strip()

        # Check who am I patterns
        for pattern in self.WHO_AM_I_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        # Check for simple questions about the user
        question_patterns = [
            r"what\s+is\s+my\s+\w+",
            r"what\s+are\s+my\s+\w+",
            r"what\s+do\s+i\s+\w+",
        ]
        return any(re.search(pattern, text_lower) and "?" in text for pattern in question_patterns)

    def is_profile_update(self, text: str) -> bool:
        """Check if text contains profile information to store."""
        text_lower = text.lower().strip()

        # Must not be a question
        if text.endswith("?"):
            return False

        # Check update patterns
        for pattern in self.PROFILE_UPDATE_PATTERNS:
            if re.search(pattern, text_lower) and len(text) > 10:
                return True

        return False

    def extract_and_store(self, text: str) -> str | None:
        """
        Extract profile information from text and store it.

        Returns:
            Description of what was stored, or None if nothing was extracted
        """
        extractions = self.profile.extract_from_text(text)

        if extractions:
            self.profile.update_from_extraction(extractions)

            # Also store in long-term memory
            for (category, key), value in extractions.items():
                self.memory.remember(key, value, category)

            # Format what was stored
            stored = []
            for (_, key), value in extractions.items():
                stored.append(f"{key.replace('_', ' ')} = {value}")

            return f"I've learned: {', '.join(stored)}"

        # Fallback: store the whole thing as a note
        if len(text) > 10 and not text.endswith("?"):
            self.memory.remember("fact", text, "notes")
            return f"I've noted that: {text[:50]}..."

        return None

    def get_profile_summary(self) -> str:
        """Get a formatted profile summary."""
        return self.profile.format_summary()

    def get_profile_info(self) -> dict[str, Any]:
        """Get the full profile data."""
        return self.profile.get_all()

    def handle_profile_command(self, text: str) -> str | None:
        """
        Handle a profile-related command.

        Returns:
            Response string if handled, None otherwise
        """
        text_lower = text.lower().strip()

        # Who am I queries
        if re.search(r"who\s+am\s+i", text_lower):
            return self.get_profile_summary()

        if re.search(r"(?:what\s+do\s+you\s+know|tell\s+me\s+about)", text_lower):
            return self.get_profile_summary()

        if re.search(r"(?:my\s+)?profile", text_lower) or re.search(r"summarize", text_lower):
            return self.get_profile_summary()

        # Specific field queries
        field_match = re.search(r"what\s+is\s+my\s+(\w+)", text_lower)
        if field_match:
            field = field_match.group(1)
            value = self.profile.get(field)
            if value:
                return f"Your {field.replace('_', ' ')} is: {value}"
            return f"I don't have information about your {field.replace('_', ' ')}."

        return None

    # Delegate other methods to underlying memory
    def remember(self, key: str, value: Any, category: str = "general") -> None:
        """Store information in long-term memory."""
        self.memory.remember(key, value, category)

    def recall(self, query: str) -> list[dict[str, Any]]:
        """Recall from long-term memory."""
        return self.memory.recall(query)

    def format_for_prompt(self) -> str:
        """Format memory for prompts."""
        parts = []

        # Add profile summary
        profile = self.profile.format_summary()
        if profile and "don't have" not in profile:
            parts.append(profile)

        # Add long-term memory
        ltm = self.memory.format_for_prompt()
        if ltm:
            parts.append(ltm)

        return "\n\n".join(parts)

    def add_user_message(self, content: str) -> None:
        """Add user message to session."""
        self.memory.add_user_message(content)

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to session."""
        self.memory.add_assistant_message(content)

    def get_context(self, max_messages: int = 20) -> str:
        """Get conversation context."""
        return self.memory.get_context(max_messages)


# Global instance
_enhanced_memory: EnhancedMemoryManager | None = None


def get_enhanced_memory() -> EnhancedMemoryManager:
    """Get the global enhanced memory instance."""
    global _enhanced_memory
    if _enhanced_memory is None:
        _enhanced_memory = EnhancedMemoryManager()
    return _enhanced_memory


def init_enhanced_memory(
    memory_manager: MemoryManager | None = None, user_profile: UserProfile | None = None
) -> EnhancedMemoryManager:
    """Initialize the global enhanced memory."""
    global _enhanced_memory
    _enhanced_memory = EnhancedMemoryManager(memory_manager, user_profile)
    return _enhanced_memory
