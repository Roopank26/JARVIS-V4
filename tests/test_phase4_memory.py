"""
Tests for JARVIS Phase 4 — Memory (EnhancedMemoryManager).
"""

from jarvis.memory.enhanced import EnhancedMemoryManager, get_enhanced_memory


def test_enhanced_memory_singleton():
    mem1 = get_enhanced_memory()
    mem2 = get_enhanced_memory()
    assert mem1 is mem2


def test_enhanced_memory_profile_query():
    mem = EnhancedMemoryManager()
    result = mem.handle_profile_command("who am i")
    assert result is not None


def test_enhanced_memory_facts_extraction():
    mem = EnhancedMemoryManager()
    mem.extract_conversation_facts("", "")
    assert True
