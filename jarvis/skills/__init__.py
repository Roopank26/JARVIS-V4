"""
JARVIS Phase 3 — Self-Improving Skills System.

Every skill collects execution metrics and automatically improves prompts
and execution strategies over time.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.skills.manager import SkillManager, SkillMetrics

logger = logging.getLogger(__name__)

_default_skill_manager: SkillManager | None = None


def get_skill_manager() -> SkillManager:
    global _default_skill_manager
    if "_default_skill_manager" not in globals() or _default_skill_manager is None:
        _default_skill_manager = SkillManager()
    return _default_skill_manager


def reset_skill_manager() -> None:
    global _default_skill_manager
    _default_skill_manager = None


def get_skill(name: str) -> Any | None:
    return get_skill_manager().get(name)


def register_builtins(manager: SkillManager | None = None) -> None:
    if manager is None:
        manager = get_skill_manager()
    from jarvis.skills.code_explainer import CodeExplainerSkill
    from jarvis.skills.comparison import FileComparisonSkill
    from jarvis.skills.docs_generator import DocsGeneratorSkill
    from jarvis.skills.pdf_summarizer import PDFSummarizerSkill
    from jarvis.skills.repo_analysis import RepoAnalysisSkill
    from jarvis.skills.research_writer import ResearchWriterSkill
    from jarvis.skills.test_generator import TestGeneratorSkill

    manager.register("repo_analysis", RepoAnalysisSkill())
    manager.register("code_explainer", CodeExplainerSkill())
    manager.register("docs_generator", DocsGeneratorSkill())
    manager.register("test_generator", TestGeneratorSkill())
    manager.register("pdf_summarizer", PDFSummarizerSkill())
    manager.register("research_writer", ResearchWriterSkill())
    manager.register("comparison", FileComparisonSkill())


__all__ = [
    "SkillMetrics",
    "SkillManager",
    "get_skill_manager",
    "reset_skill_manager",
    "get_skill",
    "register_builtins",
]
