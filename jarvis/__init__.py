"""
JARVIS - Just A Rather Very Intelligent System
A cross-platform personal AI assistant with voice, vision, and automation.
"""

__version__ = "1.0.0"
__author__ = "JARVIS Team"

from jarvis.core.agent import JarvisAgent
from jarvis.memory.memory_manager import MemoryManager
from jarvis.tools.registry import ToolRegistry

__all__ = ["JarvisAgent", "MemoryManager", "ToolRegistry"]
