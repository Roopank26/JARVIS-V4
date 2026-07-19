"""
User Profile Manager for JARVIS.
Provides structured personal information storage with natural language extraction.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


class UserProfile:
    """
    Structured user profile with categories for personal information.

    Categories:
    - identity: Name, age, birthday, location, occupation
    - education: School, university, field of study, skills
    - preferences: Hobbies, favorite things, interests
    - relationships: Family, friends, colleagues
    - goals: Career goals, learning goals, projects
    - work: Job, company, role, tools
    """

    DEFAULT_CATEGORIES = [
        "identity",
        "education",
        "preferences",
        "relationships",
        "goals",
        "work",
        "interests",
    ]

    # Key mappings for natural language to structured fields
    FIELD_MAPPINGS = {
        # Identity
        "name": ["name", "my name", "i am called", "call me"],
        "age": ["age", "i am years old", "years old"],
        "birthday": ["birthday", "born on", "date of birth"],
        "city": ["city", "i live in", "living in", "from"],
        "country": ["country", "from", "country of"],
        "occupation": ["occupation", "job", "profession", "work as", "employed as"],
        # Education
        "school": ["school", "studying at", "attended", "high school"],
        "university": ["university", "college", "institute"],
        "field": ["field", "studying", "major", "degree in", "pursuing"],
        "skills": ["skill", "know", "proficient", "experience with"],
        "programming_languages": ["programming", "python", "java", "javascript", "coding"],
        # Preferences
        "favorite_color": ["favorite color", "fav color", "color i like"],
        "favorite_food": ["favorite food", "fav food", "food i like", "like to eat"],
        "favorite_movie": ["favorite movie", "fav movie"],
        "favorite_music": ["favorite music", "music genre", "i listen to"],
        "hobbies": ["hobby", "hobbies", "i enjoy", "i like to", "passion"],
        # Relationships
        "family": ["family", "father", "mother", "sister", "brother", "parent"],
        "friends": ["friend", "friends"],
        "colleagues": ["colleague", "coworker", "teammate"],
        # Goals
        "career_goal": ["career goal", "career objective", "want to become"],
        "learning_goal": ["learning", "study", "learn about", "master"],
        "current_project": ["project", "working on", "currently doing"],
    }

    def __init__(self, profile_path: Path | None = None):
        if profile_path is None:
            base_dir = self._get_base_dir()
            profile_dir = base_dir / "memory"
            profile_dir.mkdir(parents=True, exist_ok=True)
            self.profile_path = profile_dir / "user_profile.json"
        else:
            self.profile_path = profile_path

        self._lock = Lock()
        self._profile: dict[str, dict[str, Any]] = {}
        self._load_or_initialize()

    def _get_base_dir(self) -> Path:
        """Get the base directory for JARVIS config."""
        return Path.home() / ".jarvis"

    def _empty_profile(self) -> dict[str, dict[str, Any]]:
        """Return the empty profile structure."""
        return {
            "identity": {},
            "education": {},
            "preferences": {},
            "relationships": {},
            "goals": {},
            "work": {},
            "interests": {},
            "_meta": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        }

    def _load_or_initialize(self) -> None:
        """Load existing profile or initialize new."""
        if not self.profile_path.exists():
            self._profile = self._empty_profile()
            self._save()
            return

        with self._lock:
            try:
                with open(self.profile_path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._profile = data
                else:
                    self._profile = self._empty_profile()
            except Exception:
                self._profile = self._empty_profile()

    def _save(self) -> None:
        """Save profile to disk."""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self._profile["_meta"]["updated_at"] = datetime.now().isoformat()

        with self._lock, open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self._profile, f, indent=2, ensure_ascii=False)

    def set(self, key: str, value: Any, category: str = "identity") -> None:
        """Set a profile field."""
        if category not in self._profile:
            self._profile[category] = {}

        self._profile[category][key] = {"value": str(value), "updated": datetime.now().isoformat()}
        self._save()

    def get(self, key: str, category: str = "identity") -> str | None:
        """Get a profile field."""
        entry = self._profile.get(category, {}).get(key)
        if entry and isinstance(entry, dict):
            return entry.get("value")
        return entry if entry else None

    def get_all(self, category: str | None = None) -> dict[str, Any]:
        """Get all fields in a category or all categories."""
        if category:
            return self._profile.get(category, {}).copy()
        return self._profile.copy()

    def delete(self, key: str, category: str = "identity") -> bool:
        """Delete a profile field."""
        if category in self._profile and key in self._profile[category]:
            del self._profile[category][key]
            self._save()
            return True
        return False

    def extract_from_text(self, text: str) -> dict[str, dict[str, str]]:
        """
        Extract profile information from natural language text.

        Returns:
            Dict mapping (category, key) -> extracted value
        """
        extracted = {}

        # Name patterns
        name_patterns = [
            r"(?:my name is|i am|i'm|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"(?:name[:\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted[("identity", "name")] = match.group(1).strip()
                break

        # Field of study patterns
        field_patterns = [
            r"(?:studying|study|major in|degree in|field of)\s+([A-Za-z\s]+(?:AI|ML|Machine Learning|Computer Science|Engineering|Data Science|Physics|Math|Chemistry|Biology|Medicine|Law|Business|Economics|Art|Design|Music)?)",
            r"(?:i am a)\s+([A-Za-z\s]+(?:student|engineer|developer|researcher|designer))",
        ]
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Normalize field names
                if "aiml" in value.lower() or "machine learning" in value.lower():
                    value = "AIML"
                elif "computer science" in value.lower():
                    value = "Computer Science"
                extracted[("education", "field")] = value
                break

        # Skill/interest patterns
        skill_patterns = [
            r"(?:i like|i love|i am interested in|i enjoy)\s+([A-Za-z\s,]+)",
            r"(?:skills?|proficient in|experience with)\s+([A-Za-z\s,]+)",
        ]
        for pattern in skill_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Determine category based on content
                if any(
                    prog in value.lower()
                    for prog in ["python", "java", "javascript", "coding", "programming"]
                ):
                    extracted[("education", "skills")] = value
                else:
                    extracted[("interests", "topics")] = value
                break

        # Favorite color pattern
        color_match = re.search(r"(?:favorite|fav)\s+color\s+is\s+(\w+)", text, re.IGNORECASE)
        if color_match:
            extracted[("preferences", "favorite_color")] = color_match.group(1).strip()

        # Age pattern
        age_match = re.search(
            r"(?:i am|age\s+is|aged?)\s+(\d+)\s*(?:years?\s+old)?", text, re.IGNORECASE
        )
        if age_match:
            extracted[("identity", "age")] = age_match.group(1).strip()

        # City/Location pattern
        city_match = re.search(
            r"(?:i live in|living in|from|city\s+is)\s+([A-Za-z\s]+?)(?:\.|$|,)",
            text,
            re.IGNORECASE,
        )
        if city_match:
            extracted[("identity", "city")] = city_match.group(1).strip()

        # Hobby pattern
        hobby_match = re.search(
            r"(?:my hobbies?|i enjoy|i like to do)\s+(?:are\s+)?([A-Za-z\s,]+?)(?:\.|$|,)",
            text,
            re.IGNORECASE,
        )
        if hobby_match:
            extracted[("preferences", "hobbies")] = hobby_match.group(1).strip()

        return extracted

    def update_from_extraction(self, extractions: dict[tuple, str]) -> int:
        """
        Update profile from extractions.

        Returns:
            Number of fields updated
        """
        count = 0
        for (category, key), value in extractions.items():
            self.set(key, value, category)
            count += 1
        return count

    def format_summary(self) -> str:
        """
        Format the profile as a human-readable summary.

        Returns:
            Formatted profile string
        """
        lines = ["📋 **Your Profile**", ""]

        # Identity
        identity = self._profile.get("identity", {})
        if identity:
            lines.append("**👤 Identity**")
            for key, entry in identity.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Education
        education = self._profile.get("education", {})
        if education:
            lines.append("**📚 Education**")
            for key, entry in education.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Work
        work = self._profile.get("work", {})
        if work:
            lines.append("**💼 Work**")
            for key, entry in work.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Preferences
        prefs = self._profile.get("preferences", {})
        if prefs:
            lines.append("**❤️ Preferences**")
            for key, entry in prefs.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Interests
        interests = self._profile.get("interests", {})
        if interests:
            lines.append("**⭐ Interests**")
            for key, entry in interests.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Goals
        goals = self._profile.get("goals", {})
        if goals:
            lines.append("**🎯 Goals**")
            for key, entry in goals.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Relationships
        rels = self._profile.get("relationships", {})
        if rels:
            lines.append("**👥 Relationships**")
            for key, entry in rels.items():
                value = entry.get("value", "") if isinstance(entry, dict) else entry
                if value:
                    lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        if len(lines) == 2:
            return "I don't have any information about you yet. Tell me about yourself!"

        return "\n".join(lines)

    def format_for_prompt(self) -> str:
        """Format profile for inclusion in prompts."""
        return self.format_summary()

    def clear(self) -> None:
        """Clear all profile data."""
        self._profile = self._empty_profile()
        self._save()


# Global profile instance
_profile: UserProfile | None = None


def get_user_profile() -> UserProfile:
    """Get the global user profile instance."""
    global _profile
    if _profile is None:
        _profile = UserProfile()
    return _profile


def init_user_profile(profile_path: Path | None = None) -> UserProfile:
    """Initialize the global user profile."""
    global _profile
    _profile = UserProfile(profile_path)
    return _profile
