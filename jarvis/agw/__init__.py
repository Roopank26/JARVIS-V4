"""
JARVIS-V8 AGW — Artificial General Work Director System.

Directors coordinate specialized agents, manage capabilities, and execute
end-to-end workflows instead of isolated prompts.

Builds on existing JARVIS subsystems (multi-agent, evolution, memory, goals,
research, proactive monitoring, repo analysis).
"""

from __future__ import annotations

from jarvis.agw.directors import (
    ArchitectureDirector,
    AutomationDirector,
    ExecutiveDirector,
    KnowledgeDirector,
    LearningDirector,
    QualityDirector,
    ResearchDirector,
    SecurityDirector,
    SoftwareEngineeringDirector,
    get_all_directors,
    get_director,
)

__all__ = [
    "ArchitectureDirector",
    "AutomationDirector",
    "ExecutiveDirector",
    "KnowledgeDirector",
    "LearningDirector",
    "QualityDirector",
    "ResearchDirector",
    "SecurityDirector",
    "SoftwareEngineeringDirector",
    "get_all_directors",
    "get_director",
]
