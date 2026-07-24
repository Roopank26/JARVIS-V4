"""
JARVIS - Just A Rather Very Intelligent System
A cross-platform personal AI assistant with voice, vision, and automation.
"""

__version__ = "3.0.0"
__author__ = "JARVIS Team"

from jarvis.core.agent import JarvisAgent
from jarvis.memory.memory_manager import MemoryManager
from jarvis.tools.registry import ToolRegistry

try:
    from jarvis.background.tasks import BackgroundIntelligence
    from jarvis.conversation.context import ConversationContext
    from jarvis.daily.assistant import DailyAssistant
    from jarvis.notifications.manager import NotificationManager, get_notification_manager
    from jarvis.personality.manager import PersonalityManager, get_personality_manager
    from jarvis.proactive.monitor import ProactiveMonitor, get_proactive_monitor
    from jarvis.proactive.suggestions import SuggestionEngine, get_suggestion_engine
    from jarvis.workspace.awareness import WorkspaceAwareness
except Exception:
    ConversationContext = None
    NotificationManager = None
    get_notification_manager = None
    ProactiveMonitor = None
    get_proactive_monitor = None
    SuggestionEngine = None
    get_suggestion_engine = None
    WorkspaceAwareness = None
    DailyAssistant = None
    BackgroundIntelligence = None
    PersonalityManager = None
    get_personality_manager = None

try:
    from jarvis.github_agent import GitHubAgent
    from jarvis.pdf_expert import PDFExpert
except Exception:
    PDFExpert = None
    GitHubAgent = None

try:
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
    )
    from jarvis.agw.orchestrator import AGWOrchestrator, get_agw_orchestrator
except Exception:
    AGWOrchestrator = None
    get_agw_orchestrator = None
    ArchitectureDirector = None
    AutomationDirector = None
    ExecutiveDirector = None
    KnowledgeDirector = None
    LearningDirector = None
    QualityDirector = None
    ResearchDirector = None
    SecurityDirector = None
    SoftwareEngineeringDirector = None

__all__ = [
    "JarvisAgent",
    "MemoryManager",
    "ToolRegistry",
    "ConversationContext",
    "NotificationManager",
    "get_notification_manager",
    "ProactiveMonitor",
    "get_proactive_monitor",
    "SuggestionEngine",
    "get_suggestion_engine",
    "WorkspaceAwareness",
    "DailyAssistant",
    "BackgroundIntelligence",
    "PersonalityManager",
    "get_personality_manager",
    "AGWOrchestrator",
    "get_agw_orchestrator",
    "ArchitectureDirector",
    "AutomationDirector",
    "ExecutiveDirector",
    "KnowledgeDirector",
    "LearningDirector",
    "QualityDirector",
    "ResearchDirector",
    "SecurityDirector",
    "SoftwareEngineeringDirector",
    "PDFExpert",
    "GitHubAgent",
]
