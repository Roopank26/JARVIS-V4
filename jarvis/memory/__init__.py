"""
Memory module for JARVIS.
"""

from jarvis.memory.base import MemoryBase, MemoryEntry, MemoryCategory
from jarvis.memory.session import SessionMemory
from jarvis.memory.long_term import LongTermMemory
from jarvis.memory.memory_manager import MemoryManager, get_memory_manager, init_memory_manager
from jarvis.memory.user_profile import UserProfile, get_user_profile, init_user_profile
from jarvis.memory.enhanced import EnhancedMemoryManager, get_enhanced_memory, init_enhanced_memory

__all__ = [
    # Base classes
    "MemoryBase",
    "MemoryEntry",
    "MemoryCategory",
    # Core memory
    "SessionMemory",
    "LongTermMemory",
    "MemoryManager",
    "get_memory_manager",
    "init_memory_manager",
    # User profile
    "UserProfile",
    "get_user_profile",
    "init_user_profile",
    # Enhanced memory
    "EnhancedMemoryManager",
    "get_enhanced_memory",
    "init_enhanced_memory",
]
