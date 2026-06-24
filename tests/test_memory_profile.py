"""
Tests for User Profile and Enhanced Memory features.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from jarvis.memory.user_profile import UserProfile
from jarvis.memory.enhanced import EnhancedMemoryManager


class TestUserProfile:
    """Tests for UserProfile class."""

    @pytest.fixture
    def profile_path(self):
        """Create a temporary profile file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def profile(self, profile_path):
        """Create a UserProfile instance with temporary storage."""
        return UserProfile(profile_path)

    def test_set_and_get(self, profile):
        """Test setting and getting profile values."""
        profile.set("name", "John Doe", "identity")
        assert profile.get("name", "identity") == "John Doe"

    def test_get_nonexistent(self, profile):
        """Test getting non-existent value returns None."""
        assert profile.get("name", "identity") is None

    def test_delete(self, profile):
        """Test deleting profile values."""
        profile.set("name", "John", "identity")
        assert profile.get("name", "identity") == "John"
        
        result = profile.delete("name", "identity")
        assert result is True
        assert profile.get("name", "identity") is None

    def test_get_all(self, profile):
        """Test getting all values in a category."""
        profile.set("name", "John", "identity")
        profile.set("age", "25", "identity")
        
        all_identity = profile.get_all("identity")
        assert "name" in all_identity
        assert "age" in all_identity

    def test_extract_name(self, profile):
        """Test extracting name from natural language."""
        extractions = profile.extract_from_text("My name is Roopank")
        assert ("identity", "name") in extractions
        assert extractions[("identity", "name")] == "Roopank"

    def test_extract_field_of_study(self, profile):
        """Test extracting field of study."""
        extractions = profile.extract_from_text("I study AIML")
        assert ("education", "field") in extractions
        assert extractions[("education", "field")] == "AIML"

    def test_extract_favorite_color(self, profile):
        """Test extracting favorite color."""
        extractions = profile.extract_from_text("My favorite color is blue")
        assert ("preferences", "favorite_color") in extractions
        assert extractions[("preferences", "favorite_color")] == "blue"

    def test_extract_age(self, profile):
        """Test extracting age."""
        extractions = profile.extract_from_text("I am 25 years old")
        assert ("identity", "age") in extractions
        assert extractions[("identity", "age")] == "25"

    def test_extract_city(self, profile):
        """Test extracting city."""
        extractions = profile.extract_from_text("I live in Delhi")
        assert ("identity", "city") in extractions
        assert extractions[("identity", "city")] == "Delhi"

    def test_update_from_extraction(self, profile):
        """Test updating profile from extractions."""
        extractions = {
            ("identity", "name"): "John",
            ("preferences", "favorite_color"): "blue"
        }
        count = profile.update_from_extraction(extractions)
        assert count == 2
        assert profile.get("name", "identity") == "John"
        assert profile.get("favorite_color", "preferences") == "blue"

    def test_format_summary_empty(self, profile):
        """Test formatting empty profile."""
        summary = profile.format_summary()
        assert "don't have any information" in summary

    def test_format_summary_with_data(self, profile):
        """Test formatting profile with data."""
        profile.set("name", "Roopank", "identity")
        profile.set("field", "AIML", "education")
        profile.set("favorite_color", "blue", "preferences")
        
        summary = profile.format_summary()
        assert "Roopank" in summary
        assert "AIML" in summary
        assert "blue" in summary


class TestEnhancedMemoryManager:
    """Tests for EnhancedMemoryManager."""

    @pytest.fixture
    def enhanced_memory(self):
        """Create EnhancedMemoryManager with mocked dependencies."""
        with patch('jarvis.memory.enhanced.get_user_profile') as mock_profile:
            mock_profile.return_value = UserProfile()
            return EnhancedMemoryManager()

    def test_is_profile_query_who_am_i(self, enhanced_memory):
        """Test detecting 'who am I' queries."""
        assert enhanced_memory.is_profile_query("who am I?") is True
        assert enhanced_memory.is_profile_query("Who am i") is True

    def test_is_profile_query_summary(self, enhanced_memory):
        """Test detecting summary requests."""
        assert enhanced_memory.is_profile_query("summarize my profile") is True
        assert enhanced_memory.is_profile_query("what do you know about me?") is True

    def test_is_profile_query_my_profile(self, enhanced_memory):
        """Test detecting profile requests."""
        assert enhanced_memory.is_profile_query("my profile") is True
        assert enhanced_memory.is_profile_query("tell me about myself") is True

    def test_is_profile_update(self, enhanced_memory):
        """Test detecting profile updates."""
        assert enhanced_memory.is_profile_update("remember my name is John") is True
        assert enhanced_memory.is_profile_update("I study AIML") is True

    def test_is_not_profile_update_question(self, enhanced_memory):
        """Test that questions are not profile updates."""
        assert enhanced_memory.is_profile_update("what is my name?") is False

    def test_extract_and_store(self, enhanced_memory):
        """Test extracting and storing profile info."""
        result = enhanced_memory.extract_and_store("My name is Roopank")
        assert result is not None
        assert "Roopank" in result

    def test_get_profile_summary(self, enhanced_memory):
        """Test getting profile summary."""
        enhanced_memory.profile.set("name", "Test", "identity")
        summary = enhanced_memory.get_profile_summary()
        assert "Test" in summary


class TestIntentClassification:
    """Tests for profile-related intent classification."""

    def test_profile_query_intent(self):
        """Test that profile queries are classified correctly."""
        from jarvis.core.agent import classify_intent, Intent
        
        # These should be PROFILE_QUERY
        assert classify_intent("who am I") == Intent.PROFILE_QUERY
        assert classify_intent("what do you know about me?") == Intent.PROFILE_QUERY
        assert classify_intent("summarize my profile") == Intent.PROFILE_QUERY
        assert classify_intent("tell me about myself") == Intent.PROFILE_QUERY

    def test_memory_recall_intent(self):
        """Test that memory recall is still classified correctly."""
        from jarvis.core.agent import classify_intent, Intent
        
        # These should be MEMORY_RECALL
        assert classify_intent("what is my favorite color") == Intent.MEMORY_RECALL
        assert classify_intent("what's my favorite food") == Intent.MEMORY_RECALL

    def test_memory_store_intent(self):
        """Test that memory store is still classified correctly."""
        from jarvis.core.agent import classify_intent, Intent
        
        # These should be MEMORY_STORE
        assert classify_intent("remember my name is John") == Intent.MEMORY_STORE
        assert classify_intent("save that I like pizza") == Intent.MEMORY_STORE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
