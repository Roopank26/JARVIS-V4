"""
JARVIS Main Agent
The core AI assistant that combines all components with intent classification.
"""

import asyncio
import contextlib
import logging
import re
from collections.abc import Callable
from typing import Any

from jarvis.api.gemini import SimpleLLMClient
from jarvis.core.capability_router import CapabilityRouter, get_capability_router
from jarvis.core.config import Config, get_config
from jarvis.core.executor import ExecutionResult, Executor
from jarvis.core.goal import Goal
from jarvis.core.planner import Planner
from jarvis.memory.enhanced import EnhancedMemoryManager, get_enhanced_memory
from jarvis.rag import get_rag_system
from jarvis.tools.base import ToolResult
from jarvis.tools.registry import ToolRegistry, get_registry


def _noop_expand(token, ctx, hist):
    return None

try:
    from jarvis.conversation.context import ConversationContext, ConversationState
    from jarvis.conversation.reference import expand_token
except ImportError:
    ConversationContext = None  # type: ignore[misc, assignment]
    ConversationState = None  # type: ignore[misc, attr-defined]
    expand_token = _noop_expand  # type: ignore[assignment]

try:
    from jarvis.personality.manager import get_personality_manager
except ImportError:
    get_personality_manager = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

SEPARATOR_WIDTH = 40
DEFAULT_MAX_ITEMS = 5
LEAK_BLOCK_THRESHOLD = 200
LEAK_HASH_LENGTH = 300
ECHOED_PROMPT_MAX_LENGTH = 80
MIN_QUERY_LENGTH = 3
AUDIO_TEST_DURATION = 3
AUDIO_CALIBRATION_DURATION = 2
MICROPHONE_TEST_SLEEP_MS = 3000
CALIBRATION_SLEEP_MS = 2000
DEFAULT_TONE_FREQUENCY = 440
DEFAULT_TONE_DURATION = 0.5


# Intent types
class Intent:
    CHAT = "chat"  # General conversation/questions
    MEMORY_STORE = "memory_store"  # Remember/save information
    MEMORY_RECALL = "memory_recall"  # Recall/remember information
    PROFILE_QUERY = "profile_query"  # Profile-related queries
    RAG_QUERY = "rag_query"  # RAG/knowledge base queries
    RESEARCH = "research"  # Research/web search queries
    DESKTOP = "desktop"  # Desktop automation commands
    PROVIDER_QUERY = "provider_query"  # Provider/model status queries
    OLLAMA_QUERY = "ollama_query"  # Ollama-specific commands
    GROQ_QUERY = "groq_query"  # Groq-specific commands
    VOICE_STATUS = "voice_status"  # Voice system status queries
    VOICE_CONTROL = "voice_control"  # Voice start/stop/listen
    VOICE_CONFIG = "voice_config"  # Voice calibration/test/devices
    REPO_QUERY = "repo_query"  # Repository analysis queries
    TOOL_EXECUTION = "tool_execution"  # Explicit tool/task execution
    SPEAK = "speak"  # Explicit text-to-speech commands
    IMAGE_GEN = "image_gen"  # Image generation requests
    CAMERA = "camera"  # Camera / screenshot capture requests


# Keywords for intent classification
MEMORY_STORE_PATTERNS = [
    r"^\s*remember\b",  # Starts with "remember"
    r"^\s*save\b",  # Starts with "save"
    r"\bkeep in mind\b",
    r"\bstore\b",
    r"\bnote that\b",
    r"\bsave that\b",
    r"^\s*note\b",
    r"\bi like\b",
    r"\bi prefer\b",
    r"\bi hate\b",
]

MEMORY_RECALL_PATTERNS = [
    r"\bwhat(?:\'s| is)\s+my\b",  # "what is my" or "what's my"
    r"\brecall\b",
    r"\bremember\?",
    r"\bdo you remember\b",
    r"\bwhat do you know about me\b",
    r"\btell me about.*me\b",
    r"\bmy preferences\b",
    r"\bremind me\b",
]

# Profile query patterns
PROFILE_QUERY_PATTERNS = [
    r"\bwho\s+am\s+i\b",
    r"\bwhat\s+do\s+you\s+know\s+about\s+me\b",
    r"\bmy\s+profile\b",
    r"\bsummarize\s+(?:my\s+)?(?:profile|info|information)\b",
    r"\bwhat\s+(?:are\s+)?my\s+(?:details?|facts?)\b",
    r"\btell\s+me\s+about\s+myself\b",
]

# RAG/Study patterns
RAG_QUERY_PATTERNS = [
    r"\bingest\s+(?:pdf|document|file)\b",
    r"\bsummarize\s+(?:this|the|my)?\s*(?:pdf|document|notes?|chapter|module)\b",
    r"\bgenerate\s+(?:important\s+)?questions\b",
    r"\bcreate\s+(?:exam\s+)?revision\s+notes\b",
    r"\bprepare\s+(?:viva\s+)?questions\b",
    r"\bwhat(?:\'s| is)\s+in\s+(?:this|the)?\s*(?:pdf|document|notes?)\b",
    r"\bsearch\s+(?:in\s+)?(?:my\s+)?knowledge\s+base\b",
    r"\bask\s+(?:the\s+)?knowledge\s+base\b",
]

# Research patterns
RESEARCH_PATTERNS = [
    r"\bresearch\s+(?:about|on|for)?\s*\w+",
    r"\bsearch\s+(?:the\s+web\s+)?(?:for\s+)?(?:info|information)\b",
    r"\bweb\s+search\b",
    r"\bsearch\s+the\s+web\b",
    r"\bfind\s+info(?:rmation)?\b",
    r"\blatest\s+news\s+(?:on|about)\b",
    r"\bmonitor\s+(?:topic|news|reddit|hackernews|arxiv)\b",
    r"\bgenerate\s+(?:research\s+)?report\b",
    r"\bdeep\s+research\b",
    r"\bfollow\s+(?:topic|story|news)\b",
    r"\bcompare\s+\S+\s+(?:vs|with|and)\s+\S+",
    r"\bcitation\b",
    r"\bhow\s+do\s+I\s+cite\b",
]

# Desktop automation patterns
DESKTOP_PATTERNS = [
    r"\b(?:open|launch|start)\s+\w+\b",  # open Chrome, launch VS Code
    r"\b(?:close|quit)\s+(?:window|app|application)\b",
    r"\b(?:minimize|maximize)\s+(?:window)?\b",
    r"\b(?:focus|switch to)\s+\w+\b",  # focus Chrome
    r"\blist\s+windows?\b",
    r"\bshow\s+windows?\b",
    r"\bscreenshot\b",
    r"\bcopy\s+(?:to\s+)?clipboard\b",
    r"\bpaste\s+(?:from\s+)?clipboard\b",
    r"\b(?:ctrl|control)\+[a-z]\b",  # ctrl+c
    r"\balt\+[a-z]\b",  # alt+f4
    r"^\s*type\s+\S+\b",
    r"^\s*key(?:press)?\s+\S+\b",
    r"^\s*window\s+(?:manage|management)\b",
]

# Provider/Model patterns
# Voice Status patterns
VOICE_STATUS_PATTERNS = [
    r"\bvoice\s+status\b",
    r"\bvoice\s+check\b",
    r"\bshow\s+voice\b",
    r"\bmic\s+status\b",
    r"\baudio\s+status\b",
]

VOICE_CONTROL_PATTERNS = [
    r"\bvoice\s+start\b",
    r"\bvoice\s+stop\b",
    r"\bvoice\s+listen\b",
    r"\bvoice\s+pause\b",
    r"\bvoice\s+restart\b",
    r"\bstart\s+voice\b",
    r"\bstop\s+voice\b",
    r"\blistening\s+(?:on|start|begin)\b",
    r"\bwake\s+word\s+status\b",
    r"\bvoice\s+wakeword\s+status\b",
]

VOICE_CONFIG_PATTERNS = [
    r"\bvoice\s+calibrate\b",
    r"\bvoice\s+test\b",
    r"\bvoice\s+devices\b",
    r"\blist\s+(?:audio|mic|input)\s+devices\b",
    r"\btest\s+(?:microphone|mic|speaker)\b",
    r"\bcalibrate\s+voice\b",
    r"\bset\s+(?:mic|microphone|speaker)\b",
]

SPEAK_PATTERNS = [
    r"^\s*say\s+(.+)$",
    r"^\s*speak\s+(.+)$",
]

# TTS request patterns — broader than SPEAK_PATTERNS
# Covers implicit requests for voice output
TTS_REQUEST_PATTERNS = [
    r"\bcannot\s+hear\b",
    r"\bcan'?t\s+hear\b",
    r"\bhear\s+(?:your|you|jarvis)\b",
    r"\bno\s+(?:sound|audio|voice)\b",
    r"\bspeak\s+(?:to\s+me|out\s+loud|aloud)\b",
    r"\btalk\s+to\s+me\b",
    r"\bread\s+(?:this|it|that|aloud)\b",
    r"\buse\s+(?:your\s+)?voice\b",
    r"\bvoice\s+(?:output|response|reply)\b",
    r"\bsay\s+(?:hello|hi|that|this)\b",
    r"\bplay\s+(?:audio|sound|voice|speech)\b",
    r"\blet\s+me\s+hear\b",
    r"\bplease\s+(?:speak|talk|say)\b",
    r"\bresponse\s+(?:in\s+)?voice\b",
]

# Image generation patterns
IMAGE_GEN_PATTERNS = [
    r"\bgenerate\s+(?:an?\s+)?image\b",
    r"\bcreate\s+(?:an?\s+)?image\b",
    r"\bdraw\s+(?:me\s+)?(?:an?\s+)?\b",
    r"\bmake\s+(?:an?\s+)?(?:image|picture|wallpaper|logo|art|illustration)\b",
    r"\bpaint\s+\b",
    r"\billustrate\b",
    r"\brender\s+(?:an?\s+)?image\b",
    r"\bvisualize\b",
    r"\bimage\s+(?:of|showing|depicting)\b",
    r"\bpicture\s+of\b",
    r"\bwallpaper\s+(?:of|with|showing)?\b",
    r"\blogo\s+(?:for|of|with)?\b",
    r"\bthumbnail\b",
    r"\banime\s+(?:style|art|image|drawing)?\b",
    r"\bstable\s+diffusion\b",
    r"\bdall.?e\b",
    r"\bflux\b",
    r"\bportrait\s+of\b",
]

# Camera / screenshot patterns
CAMERA_PATTERNS = [
    r"\bopen\s+(?:the\s+)?camera\b",
    r"\bstart\s+(?:the\s+)?camera\b",
    r"\btake\s+(?:a\s+)?photo\b",
    r"\btake\s+(?:a\s+)?picture\b",
    r"\btake\s+(?:a\s+)?snapshot\b",
    r"\bcapture\s+(?:an?\s+)?image\b",
    r"\bwebcam\b",
    r"\bsnap\s+(?:a\s+)?photo\b",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?camera\b",
    r"\bscreenshot\b",
    r"\btake\s+(?:a\s+)?screenshot\b",
    r"\bscreen\s+capture\b",
    r"\bcapture\s+(?:the\s+)?screen\b",
    r"\bwhat\s+(?:does|do)\s+(?:my|the)\s+screen\b",
]

PROVIDER_QUERY_PATTERNS = [
    r"\bprovider\s+status\b",
    r"\blist\s+models?\b",
    r"\bshow\s+models?\b",
    r"\bswitch\s+provider\b",
    r"\bswitch\s+to\b",
    r"\bwhich\s+(?:model|provider|AI)\b",
    r"\bcurrent\s+(?:model|provider)\b",
    r"\bprovider\s+info\b",
    r"\bbenchmark\b",
    r"\bcompare\s+\S+\s+(?:vs|with|and)\s+\S+",
    r"\buse\s+model\b",
    r"\bwhat\s+model\b",
]

OLLAMA_PATTERNS = [
    r"\bollama\s+status\b",
    r"\bollama\s+list\b",
    r"\bollama\s+show\b",
    r"\bollama\s+ps\b",
    r"\bollama\s+run\b",
    r"\bollama\s+pull\b",
    r"\bollama\s+delete\b",
    r"\bollama\s+models\b",
    r"\bdownload\s+(?:a\s+)?(?:ollama\s+)?model\b",
    r"\bremove\s+(?:ollama\s+)?model\b",
    r"\bstart\s+ollama\b",
]

GROQ_PATTERNS = [
    r"\bgroq\s+status\b",
    r"\bgroq\s+models\b",
    r"\bgroq\s+api\b",
    r"\bgroq\s+key\b",
    r"\buse\s+groq\b",
    r"\bcloud\s+AI\b",
    r"\bset\s+groq\b",
]

TOOL_EXECUTION_PATTERNS = [
    # File operations
    r"^\s*(read|open|view|display)\s+(file|document)",
    r"^\s*(write|create|edit|modify)\s+(file|document)",
    r"^\s*(delete|remove)\s+(file|document)",
    r"^\s*(list|show)\s+(files|directory|folder)",
    r"^\s*(search|grep)\s+[^T]",
    r"^\s*(create|delete)\s+directory",
    # Terminal
    r"^\s*(run|execute|start)\s+(command|script|program)",
    r"^\s*(install|uninstall)\s+",
    r"^\s*(kill|stop)\s+(process|app)",
    # Apps
    r"^\s*(open|launch|start)\s+\w+",
    r"^\s*(close|quit)\s+\w+",
    # Specific tools
    r"^\s*cd\s+",
    r"^\s*ls\s+",
    r"^\s*cat\s+",
    r"^\s*mkdir\s+",
    r"^\s*rm\s+",
    r"^\s*cp\s+",
    r"^\s*mv\s+",
    r"^\s*pip\s+",
    r"^\s*git\s+",
    r"^\s*docker\s+",
]

# Repository analysis patterns
REPO_PATTERNS = [
    r"\banalyze\s+(?:this\s+)?repository\b",
    r"\bshow\s+(?:the\s+)?architecture\b",
    r"\bfind\s+(?:all\s+)?(?:TODO|FIXME|HACK)s?\b",
    r"\bfind\s+security\s+(?:issues?|vulnerabilities)\b",
    r"\bfind\s+duplicat(?:e|ed)\s+code\b",
    r"\bfind\s+dead\s+code\b",
    r"\bshow\s+dependency\s+graph\b",
    r"\bgenerate\s+(?:repo|repository)\s+(?:docs?|documentation)\b",
    r"\bcreate\s+UML\s+(?:diagram|overview)\b",
    r"\breview\s+(?:this\s+)?repository\b",
    r"\bscan\s+repository\b",
]

# Questions that should stay in chat mode
CHAT_ONLY_PATTERNS = [
    r"^(what is|what's)\s",
    r"^(who is|who's)\s",
    r"^(how do I|how can I|how to)\s",
    r"^(why do I|why does)\s",
    r"^(explain|tell me about|describe)\s",
    r"^(give me|show me)\s",
    r"^(can you|could you)\s",
    r"^\s*(what|who|why|how|when|where)\b",
    r"\?$",  # Ends with question mark
    # Study/learning plans
    r"create.*study\s+plan",
    r"make.*plan\s+for",
    r"help me study",
    r"learning.*plan",
    r"study.*guide",
]


LEAKAGE_PATTERNS = [
    r"PHASE\s+\d+",
    r"OBJECTIVE:",
    r"ARCHITECTURE:",
    r"Do not commit until",
    r"Rules:",
    r"RULES:",
    r"Guidelines:",
    r"GUIDELINES:",
    r"You are a helpful AI assistant",
    r"You are JARVIS",
    r"Your capabilities:",
    r"Available tools",
    r"Personal memory:",
    r"system prompt",
    r"prompt injection",
    r"instruction:",
    r"INSTRUCTION:",
    r"Task:",
    r"TASK:",
    r"Goal:",
    r"GOAL:",
]


def _sanitize_response(response: str) -> str:
    """
    Strip leaked prompt/instruction blocks from responses.

    Heuristics:
    - Detect instruction-like headings or blocks
    - Detect duplicated long blocks containing leakage-like content
    - Detect accidental echoing of user prompts at start of response
    - Preserve legitimate long outputs (reports, code, docs, analysis)
    """
    if not response or not isinstance(response, str):
        return response

    lines = response.splitlines()
    cleaned = []
    prev_block_hash = None
    dup_count = 0
    first_content_line_index = None

    for _, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        # Preserve empty lines but track first content line
        if not stripped:
            cleaned.append(line)
            continue

        if first_content_line_index is None:
            first_content_line_index = len(cleaned)

        # Detect instruction/leakage headings
        is_leak_heading = False
        for pat in LEAKAGE_PATTERNS:
            if re.search(pat, lower, re.IGNORECASE):
                is_leak_heading = True
                break

        if is_leak_heading:
            # Very long instruction-like blocks (>200 chars) are definitely leaks
            if len(stripped) > LEAK_BLOCK_THRESHOLD:
                break
            # Short headings are skipped
            continue

        # Detect duplicated long blocks that contain leakage-like content
        block_hash = hash(stripped[:LEAK_HASH_LENGTH])
        if block_hash == prev_block_hash and len(stripped) > LEAK_HASH_LENGTH:
            dup_count += 1
            if dup_count >= 2:
                break
        else:
            dup_count = 0
        prev_block_hash = block_hash

        cleaned.append(line)

    result = "\n".join(cleaned).strip()

    # Detect echoed user prompt at start of response
    if result and first_content_line_index is not None:
        first_lines = [ln.strip() for ln in result.splitlines() if ln.strip()]
        if first_lines:
            first = first_lines[0]
            # Heuristic: very long first line (>80 chars) with no sentence-ending
            # punctuation and followed by normal text is likely an echoed prompt.
            if (
                len(first) > ECHOED_PROMPT_MAX_LENGTH
                and first.count(".") + first.count("!") + first.count("?") <= 1
            ):
                # Only strip if there's more content after it
                rest = "\n".join(first_lines[1:]).strip()
                if rest:
                    result = rest

    return result if result else response


SYSTEM_PROMPT = """You are JARVIS, Just A Rather Very Intelligent System.

You are a powerful AI assistant with access to a wide range of tools and plugins.

## ABSOLUTE RULES

1. NEVER say "I cannot", "I am text-only", "I cannot generate images",
   "I cannot speak", "I cannot browse", "I don't have access to" any capability
   UNLESS the Capability Discovery layer has confirmed that NO suitable tool exists.

2. BEFORE answering ANY request that involves a capability:
   - The Planner/CapabilityRouter has ALREADY checked what tools are available.
   - If a tool exists: INVOKE it. Do not refuse.
   - Only state a limitation if the capability was NOT found in the tool registry.

3. When a tool executes successfully: present its output clearly and helpfully.
   Do NOT re-explain what happened — just relay the results.

4. For conversational questions: answer directly and concisely.

## YOUR CAPABILITIES (dynamically discovered — this list is authoritative)

{capabilities}

## MEMORY

{memory}

## CURRENT GOAL

{goal}
"""


def classify_intent(user_input: str) -> Intent:
    """
    Classify the user input into an intent category.

    Args:
        user_input: The user's message

    Returns:
        Intent type
    """
    text = user_input.lower().strip()

    # Check for profile queries FIRST
    for pattern in PROFILE_QUERY_PATTERNS:
        if re.search(pattern, text):
            return Intent.PROFILE_QUERY

    # Check for RAG/knowledge queries
    for pattern in RAG_QUERY_PATTERNS:
        if re.search(pattern, text):
            return Intent.RAG_QUERY
    # Check for voice status queries
    for pattern in VOICE_STATUS_PATTERNS:
        if re.search(pattern, text):
            return Intent.VOICE_STATUS

    # Check for voice control commands (start/stop/listen)
    for pattern in VOICE_CONTROL_PATTERNS:
        if re.search(pattern, text):
            return Intent.VOICE_CONTROL

    # Check for voice config commands (calibrate/test/devices)
    for pattern in VOICE_CONFIG_PATTERNS:
        if re.search(pattern, text):
            return Intent.VOICE_CONFIG

    # Check for explicit speak/say commands
    for pattern in SPEAK_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return Intent.SPEAK

    # Check for broader TTS/voice output requests
    for pattern in TTS_REQUEST_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug("[Planner] Intent: TTS request -> SPEAK")
            return Intent.SPEAK

    # Check for image generation requests
    for pattern in IMAGE_GEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug("[Planner] Intent: image generation -> IMAGE_GEN")
            return Intent.IMAGE_GEN

    # Check for camera / screenshot requests
    for pattern in CAMERA_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug("[Planner] Intent: camera/screenshot -> CAMERA")
            return Intent.CAMERA

    # Check for provider/model queries
    for pattern in PROVIDER_QUERY_PATTERNS:
        if re.search(pattern, text):
            return Intent.PROVIDER_QUERY

    # Check for Ollama-specific commands
    for pattern in OLLAMA_PATTERNS:
        if re.search(pattern, text):
            return Intent.OLLAMA_QUERY

    # Check for Groq-specific commands
    for pattern in GROQ_PATTERNS:
        if re.search(pattern, text):
            return Intent.GROQ_QUERY

    # Check for repository analysis queries
    for pattern in REPO_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return Intent.REPO_QUERY

    # Check for memory recall (questions about personal info)
    for pattern in MEMORY_RECALL_PATTERNS:
        if re.search(pattern, text):
            return Intent.MEMORY_RECALL

    # Check for memory store (explicit remember commands)
    # Only if it's not a question
    if "?" not in user_input:
        for pattern in MEMORY_STORE_PATTERNS:
            if re.search(pattern, text):
                return Intent.MEMORY_STORE

    # Check for research queries BEFORE tool execution (higher priority)
    for pattern in RESEARCH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return Intent.RESEARCH

    # Check for desktop automation commands
    for pattern in DESKTOP_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return Intent.DESKTOP

    # Check for explicit tool execution patterns
    for pattern in TOOL_EXECUTION_PATTERNS:
        if re.search(pattern, text):
            return Intent.TOOL_EXECUTION

    # Check for chat-only patterns (questions, explanations, plans)
    for pattern in CHAT_ONLY_PATTERNS:
        if re.search(pattern, text):
            return Intent.CHAT

    # Default to chat for conversational input
    # Short inputs or casual language
    if len(text) < MIN_QUERY_LENGTH or any(
        casual in text for casual in ["hey", "hi ", "hello", "thanks", "thank you", "please"]
    ):
        return Intent.CHAT

    # If it sounds like a question or explanation, stay in chat
    if text.endswith("?") or text.startswith(("what", "how", "why", "who", "explain")):
        return Intent.CHAT

    # Default to chat mode
    return Intent.CHAT


class JarvisAgent:
    """
    Main JARVIS agent that orchestrates all components.

    Architecture (capability-driven):
      User Input
          ↓
      classify_intent()      ← broad pattern matching
          ↓
      CapabilityRouter       ← confirms tool exists at runtime
          ↓
      Tool Execution         ← actual work happens here
          ↓
      LLM formats response   ← LLM never decides what is possible
    """

    def __init__(
        self,
        config: Config | None = None,
        memory_manager: EnhancedMemoryManager | None = None,
        tool_registry: ToolRegistry | None = None,
        llm_client: Any | None = None,
    ):
        # 1. Configuration
        self.config = config or get_config()

        # 2. Provider Health Monitor
        from jarvis.core.provider_health_monitor import get_provider_health_monitor
        self.health_monitor = get_provider_health_monitor()

        # 3. Observability
        from jarvis.core.observability import get_observability
        self.observability = get_observability()

        # 4. Memory & Tools & LLM
        self.memory = memory_manager or get_enhanced_memory()
        self.tools = tool_registry or get_registry()
        self.llm = llm_client or SimpleLLMClient()

        # 5. Planner and Executor
        self.planner = Planner(llm_client=self.llm)
        self.executor = Executor(self.tools, self.planner)

        # 5a. Continuous Learning Hook
        try:
            from jarvis.learning import ContinuousLearningEngine
            self.learning = ContinuousLearningEngine()
            self.executor.set_after_execute_callback(self._record_experience)
        except Exception as exc:
            logger.debug("Learning engine init failed: %s", exc)
            self.learning = None

        # 6. Capability Discovery & Catalog
        from jarvis.core.capability_discovery import CapabilityDiscovery
        self.capability_discovery = CapabilityDiscovery()
        self.capability_discovery.set_tool_registry(self.tools)

        # 7. Capability Router
        self.capability_router: CapabilityRouter = get_capability_router()
        self.capability_router.discovery = self.capability_discovery

        # Wire router into planner
        self.planner.set_tool_registry(self.tools)
        self.planner.set_capability_router(self.capability_router)

        # 8. RAG system & Context
        self.rag = get_rag_system()
        self._is_running = False
        self._speak_callback: Callable | None = None
        self._message_handlers: list[Callable] = []
        self._device_cache: tuple | None = None
        self._device_cache_ts: float = 0.0
        self._interrupt_flag = asyncio.Event()
        self._conversation_context = ConversationContext() if ConversationContext else None
        self._personality = get_personality_manager() if get_personality_manager else None
        self._current_goal: Goal | None = None

        # 9. Register capability tools & Print Diagnostics
        self._register_capability_tools()

    def request_interrupt(self):
        self._interrupt_flag.set()
        if self.executor is not None:
            self.executor.cancel()

    def clear_interrupt(self):
        self._interrupt_flag.clear()
        if self.executor is not None:
            self.executor.reset()
        if self._conversation_context is not None:
            self._conversation_context.set_state(ConversationState.ACTIVE)  # type: ignore[attr-defined]

    def set_speak_callback(self, callback: Callable):
        """Set callback for voice output."""
        self._speak_callback = callback
        self.executor.set_speak_callback(callback)

    def add_message_handler(self, handler: Callable):
        """Add a handler for messages."""
        self._message_handlers.append(handler)

    def speak(self, message: str):
        """Speak a message through the callback."""
        if self._speak_callback:
            try:
                result = self._speak_callback(message)
                if asyncio.iscoroutine(result):
                    loop = asyncio.get_event_loop()
                    loop.create_task(result)
            except Exception as e:
                logger.error(f"Speak error: {e}")
                logger.error(f"Message: {message}")

    def _format_tools(self) -> str:
        """Format available tools for the prompt."""
        tools = self.tools.get_tools_for_prompt()

        lines = []
        for tool in tools:
            lines.append(f"- {tool['name']}: {tool['description']}")

        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with dynamic capabilities, memory, and goals."""
        rolling_summary = ""
        with contextlib.suppress(Exception):
            rolling_summary = self.memory.get_rolling_summary()

        memory_parts: list[str] = []
        if rolling_summary:
            memory_parts.append(f"[Earlier conversation: {rolling_summary}]")

        memory_str = self.memory.format_for_prompt()
        if isinstance(memory_str, str) and memory_str:
            memory_parts.append(memory_str)

        goal_context = ""
        if self._current_goal:
            goal_context = f"Current Goal: {self._current_goal.value}"

        # Inject live capability list from CapabilityRouter
        try:
            capabilities_str = self.capability_router.build_capabilities_prompt()
        except Exception:
            capabilities_str = self._format_tools()  # fallback to old format

        return SYSTEM_PROMPT.format(
            capabilities=capabilities_str,
            memory="\n\n".join(memory_parts) if memory_parts else "(no memory stored)",
            goal=goal_context if goal_context else "(no active goal)",
        )

    def set_goal(self, goal: Goal | None) -> None:
        self._current_goal = goal

    def get_goal(self) -> Goal | None:
        return self._current_goal

    async def _record_experience(self, result: ExecutionResult, goal: str, duration_ms: float):
        """Record task experience via the continuous learning engine."""
        if self.learning is not None:
            try:
                await self.learning.record_experience(
                    task_id="",
                    input_text=goal,
                    output_text=result.summary or "",
                    success=result.success,
                    duration_ms=duration_ms,
                )
            except Exception as exc:
                logger.debug("Experience recording failed: %s", exc)

        try:
            from jarvis.evolution.experience_collector import get_experience_collector
            collector = get_experience_collector()
            collector.record_task(
                task_id="",
                input_text=goal,
                output_text=result.summary or "",
                success=result.success,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.debug("V7 experience recording failed: %s", exc)

    async def process(self, user_input: str, goal: Goal | None = None) -> str:
        """
        Process a user input and generate a response.

        Args:
            user_input: The user's message or command

        Returns:
            JARVIS's response
        """
        # Handle cancellations
        if self._interrupt_flag.is_set():
            self.clear_interrupt()
            response = "Got it, stopping. What now?"
            self.memory.add_user_message(user_input)
            self.memory.add_assistant_message(response)
            return response

        if goal is not None:
            self._current_goal = goal

        self.memory.add_user_message(user_input)

        if self._conversation_context is not None:
            self._conversation_context.set_state(ConversationState.ACTIVE)  # type: ignore[union-attr]
            self._conversation_context.add_turn("user", user_input)

        expanded_input = user_input
        try:
            if (
                ConversationContext is not None
                and self._conversation_context is not None
                and expand_token
            ):
                expanded = expand_token(
                    user_input, self._conversation_context, self.memory
                )
                if expanded and expanded.lower() != user_input.lower():
                    expanded_input = f"{user_input} (refers to: {expanded})"
        except Exception:
            expanded_input = user_input

        intent = classify_intent(expanded_input)
        logger.info("[Planner] Detected intent: %s", intent)

        matches = self.capability_router.find_capabilities_for_intent(expanded_input, max_results=1)
        if matches:
            top = matches[0]
            logger.info(
                "[Capability Router] Matched capability: %s (confidence=%.2f)",
                top.capability.name, top.confidence
            )

        try:
            response = await self._process_with_intent(intent, expanded_input)
            response = _sanitize_response(response)
            logger.info("[Success] Completed request: %s", intent)
        except Exception as e:
            logger.error("[Failure] Reason: %s", e)
            raise


        if self._conversation_context is not None:
            self._conversation_context.add_turn("assistant", response, intent=intent)
            topic_marker = None
            if intent == Intent.TOOL_EXECUTION:
                topic_marker = user_input.split()[0] if user_input.split() else None
            elif intent == Intent.DESKTOP:
                words = expanded_input.lower().split()
                for w in words:
                    if w not in {"open", "launch", "start", "close", "focus"}:
                        topic_marker = w
                        break
            if topic_marker:
                self._conversation_context.set_topic(topic_marker)

        memory_facts = self._extract_memory_facts(user_input, response)
        for key, value, category in memory_facts:
            with contextlib.suppress(Exception):
                self.memory.remember(key, value, category)

        self.memory.add_assistant_message(response)
        return response

    async def _process_with_intent(self, intent: "Intent", user_input: str) -> str:
        if intent == Intent.PROFILE_QUERY:
            return await self._handle_profile_query(user_input)
        elif intent == Intent.MEMORY_STORE:
            return await self._handle_memory_store(user_input)
        elif intent == Intent.MEMORY_RECALL:
            return await self._handle_memory_recall(user_input)
        elif intent == Intent.RAG_QUERY:
            return await self._handle_rag_query(user_input)
        elif intent == Intent.RESEARCH:
            return await self._handle_research(user_input)
        elif intent == Intent.DESKTOP:
            return await self._handle_desktop_automation(user_input)
        elif intent == Intent.VOICE_STATUS:
            return await self._handle_voice_status(user_input)
        elif intent == Intent.VOICE_CONTROL:
            return await self._handle_voice_control(user_input)
        elif intent == Intent.VOICE_CONFIG:
            return await self._handle_voice_config(user_input)
        elif intent == Intent.SPEAK:
            return await self._handle_tts_request(user_input)
        elif intent == Intent.IMAGE_GEN:
            return await self._handle_image_gen(user_input)
        elif intent == Intent.CAMERA:
            return await self._handle_camera(user_input)
        elif intent == Intent.REPO_QUERY:
            return await self._handle_repo_query(user_input)
        elif intent == Intent.PROVIDER_QUERY:
            return await self._handle_provider_query(user_input)
        elif intent == Intent.OLLAMA_QUERY:
            return await self._handle_ollama_query(user_input)
        elif intent == Intent.GROQ_QUERY:
            return await self._handle_groq_query(user_input)
        elif intent == Intent.TOOL_EXECUTION:
            return await self.execute_task(user_input)
        else:
            return await self.answer_query(user_input)

    def _extract_memory_facts(self, user_input: str, response: str) -> list[tuple[str, str, str]]:
        facts: list[tuple[str, str, str]] = []
        try:
            if not user_input or len(user_input) < 5 or user_input.endswith("?"):
                return facts

            extractions = self.memory.profile.extract_from_text(user_input)
            if extractions:
                for (category, key), value in extractions.items():
                    facts.append((key, value, category))

            lowered = user_input.lower().strip()
            if lowered.startswith("remember ") or lowered.startswith("note that "):
                facts.append(("fact", user_input, "notes"))
        except Exception:
            pass
        return facts

    async def _handle_profile_query(self, user_input: str) -> str:
        """
        Handle profile-related queries.

        Args:
            user_input: The user's query

        Returns:
            Profile information
        """
        text_lower = user_input.lower()

        # Handle "who am I" or summary requests
        if any(
            pattern in text_lower
            for pattern in ["who am i", "my profile", "summarize", "about me", "what do you know"]
        ):
            return self.memory.get_profile_summary()

        # Handle specific field queries
        field_match = re.search(r"what\s+is\s+my\s+(\w+)", text_lower)
        if field_match:
            field = field_match.group(1)
            info = self.memory.profile.get(field)
            if info:
                return f"Your {field.replace('_', ' ')} is: {info}"
            return f"I don't have information about your {field.replace('_', ' ')} stored yet."

        # Default: return full profile
        return self.memory.get_profile_summary()

    async def _handle_desktop_automation(self, user_input: str) -> str:
        """Handle desktop automation commands."""
        from jarvis.desktop.automation import get_desktop_automation

        text = user_input.lower()
        automation = get_desktop_automation()

        # List windows
        if "list windows" in text or "show windows" in text:
            windows = await automation.list_windows()
            return automation.format_windows_list(windows)

        # Screenshot
        if "screenshot" in text:
            path = await automation.take_screenshot()
            if path:
                return f"Screenshot saved to: {path}"
            return "Failed to take screenshot."

        # Launch app
        if any(k in text for k in ["open ", "launch ", "start "]):
            match = re.search(r"(?:open|launch|start)\s+(\S+)", text)
            if match:
                app = match.group(1).strip()
                success = await automation.launch_app(app)
                if success:
                    return f"Launched: {app}"
                return f"Failed to launch: {app}"

        # Close window
        if "close" in text and "window" in text:
            match = re.search(r"close\s+(?:window\s+)?(.+)", text)
            if match:
                title = match.group(1).strip()
                success = await automation.close_window(title)
                if success:
                    return f"Closed window: {title}"
                return f"Failed to close: {title}"

        # Focus window
        if "focus" in text or "switch to" in text:
            match = re.search(r"(?:focus|switch to)\s+(\S+)", text)
            if match:
                title = match.group(1).strip()
                success = await automation.focus_window(title)
                if success:
                    return f"Focused: {title}"
                return f"Failed to focus: {title}"

        # Clipboard operations
        if "get clipboard" in text or "show clipboard" in text:
            content = await automation.get_clipboard()
            if content:
                return f"Clipboard: {content[:200]}..."
            return "Clipboard is empty."

        if "copy" in text and "clipboard" in text:
            # Copy is usually handled by tool execution
            return "Copy what to clipboard? Use: copy <text> to clipboard"

        # Type text
        if text.startswith("type "):
            text_to_type = text[5:].strip()
            success = await automation.type_text(text_to_type)
            if success:
                return f"Typed: {text_to_type}"
            return "Failed to type text."

        # Hotkeys
        hotkey_match = re.search(r"(ctrl|control|alt)\+([a-z])", text)
        if hotkey_match:
            key = hotkey_match.group(2)
            mod = hotkey_match.group(1)
            success = await automation.execute_hotkey([mod, key])
            if success:
                return f"Executed: {mod}+{key}"
            return "Failed to execute hotkey."

        return """Desktop commands:
- list windows - Show open windows
- open <app> - Launch an application
- close window <name> - Close a window
- focus <window> - Focus a window
- screenshot - Take a screenshot
- type <text> - Type text
- get clipboard - Show clipboard content
- <ctrl/alt>+<key> - Execute hotkey"""

    async def _handle_research(self, user_input: str) -> str:
        """Handle research and web search queries."""
        from jarvis.research.research_agent import get_research_agent

        text = user_input.lower()
        agent = get_research_agent()

        # Monitor news
        if "monitor" in text or "news" in text:
            source = "hackernews"
            if "reddit" in text:
                source = "reddit"
            elif "arxiv" in text:
                source = "arxiv"

            match = re.search(r"(?:monitor|news)\s+(?:on\s+)?(?:about\s+)?(.+)", text)
            topic = match.group(1).strip() if match else "artificial intelligence"

            results = await agent.monitor_topic(topic, source)
            if results:
                lines = [
                    f"[{source.replace('hackernews', 'Hacker News').title()} News: {topic}]",
                    "=" * SEPARATOR_WIDTH,
                ]
                for i, item in enumerate(results[:DEFAULT_MAX_ITEMS], 1):
                    lines.append(f"\n{i}. {item.get('title', 'No title')}")
                    if item.get("url"):
                        lines.append(f"   URL: {item.get('url')}")
                    if item.get("points"):
                        lines.append(f"   Points: {item.get('points')}")
                    if item.get("score"):
                        lines.append(f"   Score: {item.get('score')}")
                return "\n".join(lines)
            return f"No news found for topic: {topic}"

        # Research topic
        if "research" in text or "search" in text or "find" in text:
            # Extract query
            match = re.search(r"(?:research|search|find)\s+(?:about|on|for)?\s*(.+)", text)
            query = match.group(1).strip() if match else user_input

            # Remove common prefixes
            for prefix in ["web search ", "search for ", "research about ", "find information "]:
                if query.startswith(prefix):
                    query = query[len(prefix) :]

            if len(query) < 3:
                return "Please provide a research topic. Example: research about AI trends"

            try:
                result = await agent.research(query)

                lines = [f"[Research: {query}]", "=" * SEPARATOR_WIDTH]
                lines.append(f"\nFound {len(result.sources)} sources\n")

                if result.summary:
                    lines.append(f"Summary: {result.summary[:300]}...")

                lines.append("\n\nSources:")
                for i, source in enumerate(result.sources[:DEFAULT_MAX_ITEMS], 1):
                    lines.append(f"\n{i}. {source.title}")
                    lines.append(f"   {source.url}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Research error: {e}")
                return f"Research failed: {e!s}"

        # Generate report
        if "report" in text:
            match = re.search(r"(?:generate\s+)?(?:research\s+)?report\s+(?:on\s+)?(.+)", text)
            if match:
                query = match.group(1).strip()
                try:
                    result = await agent.research(query)
                    report = agent.generate_report(query, result, format="markdown")
                    return f"Report generated:\n\n{report[:2000]}..."
                except Exception as e:
                    return f"Report generation failed: {e}"
            return "Usage: generate report on <topic>"

        # Citations
        if "citation" in text:
            return """[Citation Help]
JARVIS can generate citations for web sources. After doing a research query, I can format citations in:
- APA style
- MLA style
- Chicago style

Example: research about AI, then I'll cite the sources."""

        return "Research commands:\n- research <topic> - Search the web\n- monitor news on <topic> - Track news\n- generate report on <topic> - Create a report\n- citation - Learn about citations"

    async def _handle_rag_query(self, user_input: str) -> str:
        """
        Handle RAG/knowledge base queries.

        Args:
            user_input: The user's query

        Returns:
            RAG response with citations
        """
        text_lower = user_input.lower()

        # Initialize RAG if needed
        await self.rag.initialize()

        # Handle ingest commands
        if "ingest" in text_lower:
            # Extract file path from command
            # Pattern: "ingest pdf notes.pdf"
            match = re.search(r"ingest\s+(?:pdf|document|file)?\s*(.+)", text_lower)
            if match:
                file_path = match.group(1).strip()
                # Try to find the file
                from pathlib import Path

                path = Path(file_path)
                if not path.exists():
                    # Try current directory
                    path = Path.cwd() / file_path
                if path.exists():
                    try:
                        result = await self.rag.ingest_document(path)
                        return f"Successfully ingested '{result['title']}'. Added {result['chunks_added']} chunks to the knowledge base."
                    except Exception as e:
                        return f"Error ingesting document: {e}"
                else:
                    return f"File not found: {file_path}"
            return "Please specify a file to ingest. Example: 'ingest pdf notes.pdf'"

        # Handle summarize commands
        if "summarize" in text_lower:
            # Try to get context for summarization
            results = await self.rag.search(
                text_lower.replace("summarize", ""), limit=DEFAULT_MAX_ITEMS
            )
            if results:
                summary_parts = [r.get("content", "")[:200] for r in results[:3]]
                citations = self.rag.get_citations(results[:3])
                base = "Based on your knowledge base:\n\n"
                base += "\n\n".join(summary_parts)
                if citations:
                    base += f"\n\n{citations}"
                return base
            return "I couldn't find relevant content to summarize. Try ingesting a document first."

        # Handle question generation
        if "question" in text_lower:
            # Search for relevant content
            results = await self.rag.search(
                text_lower.replace("generate", "").replace("question", ""), limit=3
            )
            if results:
                content = " ".join([r.get("content", "")[:300] for r in results])
                citations = self.rag.get_citations(results)
                response = "Based on your documents, here are some questions:\n\n1. What are the main concepts covered in this topic?\n2. How would you explain the key points?\n3. What examples illustrate this concept?"
                if citations:
                    response += f"\n\n{citations}"
                return response
            return "I couldn't find relevant content. Try ingesting a document first."

        # Handle revision notes
        if "revision" in text_lower or "notes" in text_lower:
            results = await self.rag.search(text_lower, limit=DEFAULT_MAX_ITEMS)
            if results:
                notes = ["📝 Revision Notes:\n"]
                for i, r in enumerate(results, 1):
                    content = r.get("content", "")[:150]
                    notes.append(f"{i}. {content}...")
                citations = self.rag.get_citations(results)
                if citations:
                    notes.append(f"\n{citations}")
                return "\n".join(notes)
            return "I couldn't find relevant content for revision notes."

        # Default: search knowledge base
        results = await self.rag.search(text_lower, limit=DEFAULT_MAX_ITEMS)
        if results:
            response = "From your knowledge base:\n\n"
            for i, r in enumerate(results, 1):
                content = r.get("content", "")
                response += f"📄 {i}. {content[:300]}"
                if len(content) > 300:
                    response += "..."
                response += "\n\n"
            citations = self.rag.get_citations(results)
            if citations:
                response += f"{citations}"
            return response

        return "I couldn't find relevant information in your knowledge base. Try ingesting some documents first."

    async def _handle_repo_query(self, user_input: str) -> str:
        """Handle repository analysis queries."""
        from pathlib import Path

        text = user_input.lower()

        try:
            from jarvis.repo.analyzer import RepositoryAnalyzer
            from jarvis.repo.security import SecurityScanner

            # Determine the repo path (current directory)
            repo_path = Path.cwd()

            analyzer = RepositoryAnalyzer(repo_path)
            scanner = SecurityScanner()

            # Route based on query
            if "analyze repository" in text or "scan repository" in text:
                analyzer.analyze()
                return analyzer.format_summary()

            elif "architecture" in text or "show architecture" in text:
                arch = analyzer.get_architecture()
                lines = ["[Repository Architecture]", "=" * SEPARATOR_WIDTH, ""]
                lines.append("Modules:")
                for module, files in arch.get("modules", {}).items():
                    lines.append(f"  📁 {module}/")
                    for f in files[:DEFAULT_MAX_ITEMS]:
                        lines.append(f"      - {f}")
                return "\n".join(lines)

            elif "todo" in text or "find todos" in text:
                todos = analyzer.find_todos()
                if not todos:
                    return "No TODO comments found."
                lines = [f"[TODOs Found: {len(todos)}]", "=" * 40, ""]
                for todo in todos[:20]:
                    lines.append(f"[{todo['file']}:{todo['line']}] {todo['content']}")
                return "\n".join(lines)

            elif "security" in text or "vulnerabilit" in text:
                issues = scanner.scan_directory(str(repo_path))
                if not issues:
                    return "No security issues found. Your code looks secure! 🔒"
                summary = scanner.get_summary()
                return scanner.format_report()

            elif "dependency" in text:
                deps = analyzer.get_dependencies()
                lines = ["[Dependencies]", "=" * SEPARATOR_WIDTH, ""]
                for file, imports in list(deps.items())[:20]:
                    if imports:
                        lines.append(f"📄 {file}:")
                        for imp in imports[:10]:
                            lines.append(f"    - {imp}")
                return "\n".join(lines)

            elif "documentation" in text or "generate docs" in text:
                return analyzer.generate_documentation()

            elif "review repository" in text:
                # Full review
                stats = analyzer.get_statistics()
                todos = analyzer.find_todos()
                scanner.scan_directory(str(repo_path))
                summary = scanner.get_summary()

                lines = [
                    "[Repository Review]",
                    "=" * 50,
                    "",
                    f"📁 Files: {stats.total_files}",
                    f"📝 Lines: {stats.total_lines:,}",
                    f"⚙️ Functions: {stats.total_functions}",
                    f"🏛️ Classes: {stats.total_classes}",
                    f"📋 TODOs: {len(todos)}",
                    f"⚠️ Security Issues: {summary['total']}",
                    "",
                ]

                if summary["by_severity"]["critical"] > 0 or summary["by_severity"]["high"] > 0:
                    lines.append("⚠️ ACTION REQUIRED: Fix critical/high security issues!")
                else:
                    lines.append("✅ Code quality looks good!")

                return "\n".join(lines)

            else:
                # Default: run full analysis
                return analyzer.format_summary()

        except ImportError:
            return "Repository analysis not available. Ensure jarvis.repo module is installed."
        except Exception as e:
            return f"Repository analysis error: {e}"

    async def _handle_voice_status(self, user_input: str) -> str:
        """Handle voice system status queries."""
        try:
            from jarvis.voice.voice_runtime import get_voice_runtime

            runtime = get_voice_runtime()
            if runtime is None:
                return "Voice system not initialized. Run: python setup_voice.sh (Linux) or setup_voice.ps1 (Windows)"

            await runtime.initialize()
            return runtime.format_status()

        except ImportError:
            return "Voice runtime not available. Install dependencies: pip install faster-whisper sounddevice"
        except Exception as e:
            return f"Voice status error: {e}"

    async def _handle_voice_control(self, user_input: str) -> str:
        """Handle voice control commands (start/stop/listen)."""
        text = user_input.lower()

        try:
            from jarvis.voice.voice_runtime import get_voice_runtime

            runtime = get_voice_runtime()
            if runtime is None:
                return "Voice system not initialized."

            await runtime.initialize()

            # Wake-word status
            if "wakeword" in text or "wake word" in text:
                return runtime.get_wake_word_status()

            # Voice restart
            if "restart" in text:
                await runtime.stop_wake_word_listening()
                await runtime.start_wake_word_listening(agent=self)
                return "Voice restarted. Listening for wake word..."

            # Voice start / listen
            if any(x in text for x in ["start", "listen", "begin", "activate"]):
                if runtime._running:
                    return "Voice is already listening."
                await runtime.start_wake_word_listening(agent=self)
                return "Voice activated. Say 'Hey Jarvis' to wake me."

            # Voice stop / pause
            if any(x in text for x in ["stop", "pause", "deactivate", "silence"]):
                if not runtime._running:
                    return "Voice is already stopped."
                await runtime.stop_wake_word_listening()
                return "Voice deactivated."

            return "Usage: voice start | voice stop | voice restart | voice wakeword status"

        except ImportError:
            return "Voice runtime not available."
        except Exception as e:
            return f"Voice control error: {e}"

    async def _handle_voice_config(self, user_input: str) -> str:
        """Handle voice configuration commands (calibrate/test/devices)."""
        text = user_input.lower()

        try:
            # List audio devices
            if "devices" in text or "list" in text:
                return await self._list_audio_devices()

            # Test microphone
            if ("test" in text and "mic" in text) or "microphone" in text:
                return await self._test_microphone()

            # Test speaker
            if "test" in text and "speaker" in text:
                return await self._test_speaker()

            # Calibrate
            if "calibrate" in text:
                return await self._calibrate_voice()

            return "Usage: voice devices | voice test mic | voice test speaker | voice calibrate"

        except ImportError:
            return "Voice configuration not available. Install sounddevice."
        except Exception as e:
            return f"Voice config error: {e}"

    # -----------------------------------------------------------------------
    # Capability Tool Handlers
    # -----------------------------------------------------------------------

    def _register_capability_tools(self) -> None:
        """
        Register TTS, image generation, and camera tools into the ToolRegistry.

        This wires the existing JARVIS voice/vision/camera implementations
        into the tool registry so they are discoverable by the planner.
        Does NOT create new TTS engines or duplicate implementations.
        """
        from jarvis.tools.camera_tool import CameraTool, ScreenshotTool
        from jarvis.tools.image_gen_tool import ImageGenerationTool
        from jarvis.tools.speak_tool import SpeakTool

        try:
            speak_tool = SpeakTool(speak_callback=self._speak_callback)
            self.tools.register(speak_tool)
            logger.debug("[Capability] Registered: speak")
        except Exception as e:
            logger.debug("[Capability] SpeakTool registration failed: %s", e)

        try:
            img_tool = ImageGenerationTool()
            self.tools.register(img_tool)
            logger.debug("[Capability] Registered: generate_image")
        except Exception as e:
            logger.debug("[Capability] ImageGenerationTool registration failed: %s", e)

        try:
            cam_tool = CameraTool()
            self.tools.register(cam_tool)
            screenshot_tool = ScreenshotTool()
            self.tools.register(screenshot_tool)
            logger.debug("[Capability] Registered: open_camera, take_screenshot")
        except Exception as e:
            logger.debug("[Capability] CameraTool registration failed: %s", e)

            # Print startup diagnostic (shows all discovered capabilities)
            with contextlib.suppress(Exception):
                self.capability_router.print_startup_report()

    async def _handle_tts_request(self, user_input: str) -> str:
        """
        Handle TTS / voice output requests via the speak tool.
        """
        logger.info("[Planner] Detected intent: SPEAK")
        logger.info("[Capability Router] Matched capability: speak")
        logger.info("[Registry] Selected tool: speak")

        text_to_speak = user_input
        is_explicit = any(
            re.search(p, user_input, re.IGNORECASE)
            for p in [r"^\s*say\s+", r"^\s*speak\s+"]
        )

        if not is_explicit:
            try:
                response_text = await self.answer_query(
                    f"The user requested a voice response: {user_input}. Generate a friendly spoken reply."
                )
                text_to_speak = response_text
            except Exception:
                text_to_speak = "Hello! I am JARVIS. My voice is active."

        logger.info("[Executor] Executing SpeakTool for text length %d", len(text_to_speak))
        speak_result = await self.tools.execute("speak", {"text": text_to_speak})
        if speak_result and speak_result.success:
            logger.info("[Success] Completed TTS execution")
            return text_to_speak

        self.speak(text_to_speak)
        logger.info("[Success] Completed TTS execution (via callback)")
        return text_to_speak

    async def _handle_image_gen(self, user_input: str) -> str:
        """
        Handle image generation requests via the ImageGenerationTool.
        """
        logger.info("[Planner] Detected intent: IMAGE_GEN")
        logger.info("[Capability Router] Matched capability: generate_image")
        logger.info("[Registry] Selected tool: generate_image")

        prompt = user_input
        for prefix in [
            r"^\s*(?:please\s+)?(?:generate|create|draw|make|paint|render|illustrate)\s+(?:an?\s+)?(?:image|picture|photo|art|wallpaper|logo)?\s*(?:of|showing|depicting|with)?\s*",
            r"^\s*(?:i\s+want|i'd\s+like|can\s+you)\s+(?:an?\s+)?(?:image|picture|photo)?\s*(?:of)?\s*",
        ]:
            cleaned = re.sub(prefix, "", prompt, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) > 2:
                prompt = cleaned
                break

        logger.info("[Executor] Executing ImageGenerationTool for prompt: %r", prompt[:60])
        result = await self.tools.execute("generate_image", {"prompt": prompt})

        if result and result.success:
            output = result.output
            if isinstance(output, dict):
                path = output.get("image_path", "")
                provider = output.get("provider", "unknown")
                logger.info("[Success] Completed image generation via %s: %s", provider, path)
                return (
                    f"Image generated successfully using {provider}.\n"
                    f"Saved to: {path}\n"
                    f"Prompt: {prompt}"
                )
            return str(output)

        error = result.error if result else "No configured image generation provider is available."
        logger.warning("[Failure] Reason: %s", error)
        return f"Image generation failed: {error}"

    async def _handle_camera(self, user_input: str) -> str:
        """
        Handle camera / screenshot requests via CameraTool.
        """
        is_screenshot = any(
            re.search(p, user_input, re.IGNORECASE)
            for p in [r"\bscreenshot\b", r"\bscreen\s+capture\b", r"\bcapture\s+(?:the\s+)?screen\b"]
        )

        tool_name = "take_screenshot" if is_screenshot else "open_camera"
        source = "screen" if is_screenshot else "auto"

        logger.info("[Planner] Detected intent: CAMERA")
        logger.info("[Capability Router] Matched capability: %s", tool_name)
        logger.info("[Registry] Selected tool: %s", tool_name)
        logger.info("[Executor] Executing %s (source=%s)", tool_name, source)

        result = await self.tools.execute(tool_name, {"source": source})

        if result and result.success:
            output = result.output
            if isinstance(output, dict):
                path = output.get("image_path", "")
                source_used = output.get("source", "")
                analysis = output.get("analysis", "")
                msg = f"Captured via {source_used}: {path}"
                if analysis:
                    msg += f"\n\nAnalysis: {analysis}"
                logger.info("[Success] Completed camera capture: %s", path)
                return msg
            return str(output)

        error = result.error if result else "Unknown error"
        logger.warning("[Failure] Reason: %s", error)
        return f"Camera capture failed: {error}"


    async def _handle_speak(self, user_input: str) -> str:
        """Handle explicit speak/say commands (backward compatible)."""
        for pattern in SPEAK_PATTERNS:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                to_speak = match.group(1).strip()
                if to_speak:
                    # Route through speak tool for consistency
                    result = await self.tools.execute("speak", {"text": to_speak})
                    if result and result.success:
                        logger.info("[Success] SpeakTool: %r", to_speak[:40])
                    else:
                        self.speak(to_speak)  # fallback
                    return to_speak
        return "Usage: say <text> | speak <text>"

    def _get_cached_devices(self):
        """Get cached sounddevice devices or re-query if stale."""
        import time

        now = time.time()
        if self._device_cache and (now - self._device_cache_ts) < 2.0:
            return self._device_cache
        import sounddevice as sd

        devices = sd.query_devices()
        self._device_cache = devices
        self._device_cache_ts = now
        return devices

    def _find_input_device(self) -> int | None:
        """Find a usable input device index, or None if none available."""
        try:
            devices = self._get_cached_devices()
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    return i
        except Exception:
            pass
        return None

    def _list_input_devices(self) -> list:
        """List available input devices."""
        try:
            devices = self._get_cached_devices()
            return [
                {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
        except Exception:
            return []

    def _list_output_devices(self) -> list:
        """List available output devices."""
        try:
            devices = self._get_cached_devices()
            return [
                {"index": i, "name": d["name"], "channels": d["max_output_channels"]}
                for i, d in enumerate(devices)
                if d["max_output_channels"] > 0
            ]
        except Exception:
            return []

    async def _list_audio_devices(self) -> str:
        """List available audio input and output devices."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            input_devices = [
                {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
            output_devices = [
                {"index": i, "name": d["name"], "channels": d["max_output_channels"]}
                for i, d in enumerate(devices)
                if d["max_output_channels"] > 0
            ]

            lines = ["[Audio Devices]", "=" * SEPARATOR_WIDTH]

            default_input = sd.default.device[0] if sd.default.device[0] is not None else None
            default_output = sd.default.device[1] if sd.default.device[1] is not None else None
            default_input_name = None
            default_output_name = None

            if default_input is not None:
                with contextlib.suppress(Exception):
                    default_input_name = sd.query_devices(default_input)["name"]
            if default_output is not None:
                with contextlib.suppress(Exception):
                    default_output_name = sd.query_devices(default_output)["name"]

            lines.append(f"\nDefault Input: {default_input_name or 'None'}")
            lines.append(f"\nDefault Output: {default_output_name or 'None'}")
            lines.append(f"\nInput Devices ({len(input_devices)}):")
            for d in input_devices:
                lines.append(f"  [{d['index']}] {d['name']} ({d['channels']} ch)")

            lines.append(f"\nOutput Devices ({len(output_devices)}):")
            for d in output_devices[:10]:
                lines.append(f"  [{d['index']}] {d['name']} ({d['channels']} ch)")

            return "\n".join(lines)

        except ImportError:
            return "sounddevice not installed. Install with: pip install sounddevice"
        except Exception as e:
            return f"Error listing devices: {e}"

    async def _test_microphone(self) -> str:
        """Test microphone input."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            input_devices = [
                {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
            device_index = next((d["index"] for d in input_devices), None)

            lines = ["[Microphone Test]", "=" * SEPARATOR_WIDTH]
            lines.append("\nInput devices found: " + str(len(input_devices)))
            for d in input_devices:
                lines.append(f"  [{d['index']}] {d['name']}")

            if not input_devices:
                lines.append("\nNo input devices detected.")
                lines.append("  Check Windows audio settings and ensure a microphone is enabled.")
                return "\n".join(lines)

            if device_index is None:
                lines.append("\nNo accessible input device available.")
                lines.append(
                    "  This system's audio driver/PortAudio configuration may not support input capture."
                )
                return "\n".join(lines)

            lines.append(
                f"\nListening for {AUDIO_TEST_DURATION} seconds on device {device_index}..."
            )
            lines.append("Speak into your microphone now.\n")

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio status: {status}")
                indata.flatten()

            try:
                stream = sd.InputStream(
                    device=device_index, callback=audio_callback, channels=1, samplerate=16000
                )
                with stream:
                    sd.sleep(MICROPHONE_TEST_SLEEP_MS)
                lines.append("[OK] Microphone is working!")
                lines.append("Audio levels detected successfully.")
            except Exception as e:
                lines.append(f"[FAIL] Microphone test failed: {e}")
                lines.append(
                    "  This system's audio driver/PortAudio configuration may not support input capture. "
                    "Try installing PyAudio or checking Windows audio settings."
                )

            return "\n".join(lines)

        except ImportError:
            return "sounddevice not installed."
        except Exception as e:
            return f"Microphone test error: {e}"

    async def _test_speaker(self) -> str:
        """Test speaker output."""
        try:
            import sounddevice as sd

            lines = ["[Speaker Test]", "=" * SEPARATOR_WIDTH]
            lines.append("\nPlaying test tone...")

            try:
                # Generate a simple sine wave tone
                import numpy as np

                frequency = DEFAULT_TONE_FREQUENCY  # Hz (A4 note)
                duration = DEFAULT_TONE_DURATION  # seconds
                sample_rate = 44100

                t = np.linspace(0, duration, int(sample_rate * duration))
                tone = np.sin(2 * np.pi * frequency * t)

                # Play
                sd.play(tone, sample_rate)
                sd.wait()

                lines.append("✓ Speaker is working!")
                lines.append(f"Played {frequency}Hz test tone for {duration}s.")
            except Exception as e:
                lines.append(f"✗ Speaker test failed: {e}")

            return "\n".join(lines)

        except ImportError:
            return "sounddevice not installed."
        except Exception as e:
            return f"Speaker test error: {e}"

    async def _calibrate_voice(self) -> str:
        """Calibrate voice recognition settings."""
        try:
            import numpy as np
            import sounddevice as sd

            device_index = self._find_input_device()
            input_devices = self._list_input_devices()

            lines = ["[Voice Calibration]", "=" * SEPARATOR_WIDTH]
            lines.append("\nInput devices found: " + str(len(input_devices)))
            for d in input_devices:
                lines.append(f"  [{d['index']}] {d['name']}")

            if not input_devices:
                lines.append("\n✗ No input devices detected for calibration.")
                lines.append("  Check Windows audio settings and ensure a microphone is enabled.")
                return "\n".join(lines)

            if device_index is None:
                lines.append("\n✗ No accessible input device available for calibration.")
                lines.append(
                    "  This system's audio driver/PortAudio configuration may not support input capture. "
                    "Try installing PyAudio or checking Windows audio settings."
                )
                return "\n".join(lines)

            lines.append(f"\nCalibrating microphone on device {device_index}...")
            lines.append("Please remain silent for 2 seconds, then speak.")

            try:
                audio_levels = []

                def callback(indata, frames, time_info, status):
                    audio_data = indata.flatten()
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                    audio_levels.append(rms)

                stream = sd.InputStream(
                    device=device_index, callback=callback, channels=1, samplerate=16000
                )
                with stream:
                    sd.sleep(CALIBRATION_SLEEP_MS)

                if audio_levels:
                    avg_noise = np.mean(audio_levels)
                    suggested_threshold = int(avg_noise * 3)

                    lines.append("\n✓ Calibration complete!")
                    lines.append(f"Average noise level: {avg_noise:.1f}")
                    lines.append(f"Suggested threshold: {suggested_threshold}")
                    lines.append("\nTo update your voice config, run:")
                    lines.append(f"  voice_config.json set energy_threshold={suggested_threshold}")
                else:
                    lines.append("✗ Could not capture audio levels.")

            except Exception as e:
                lines.append(f"✗ Calibration failed: {e}")
                lines.append(
                    "  This system's audio driver/PortAudio configuration may not support input capture. "
                    "Try installing PyAudio or checking Windows audio settings."
                )

            return "\n".join(lines)

        except ImportError:
            return "sounddevice not installed."
        except Exception as e:
            return f"Calibration error: {e}"

    async def _handle_ollama_query(self, user_input: str) -> str:
        """Handle Ollama-specific commands."""
        text = user_input.lower()

        try:
            import subprocess

            # Ollama status
            if any(x in text for x in ["status", "ps"]):
                try:
                    result = subprocess.run(
                        ["ollama", "ps"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return f"[Ollama Status]\n{result.stdout}"
                    return "Ollama is not running. Start with: ollama serve"
                except FileNotFoundError:
                    return "Ollama is not installed. Install from: https://ollama.ai"
                except Exception as e:
                    return f"Ollama status error: {e}"

            # List models
            if any(x in text for x in ["list", "models", "show"]):
                try:
                    result = subprocess.run(
                        ["ollama", "list"], capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        return f"[Ollama Models]\n{result.stdout}"
                    return "Could not list Ollama models."
                except FileNotFoundError:
                    return "Ollama is not installed."
                except Exception as e:
                    return f"Error listing models: {e}"

            # Pull/download model
            if any(x in text for x in ["pull", "download", "run"]):
                match = re.search(r"(?:pull|download|run)\s+(?:model\s+)?(\S+)", text)
                if match:
                    model = match.group(1).strip()
                    return f"To download '{model}', run:\n  ollama pull {model}\n\nOr in your terminal:\n  ollama run {model}"
                return "Usage: ollama pull <model_name>"

            # Delete/remove model
            if "delete" in text or "remove" in text:
                match = re.search(r"(?:delete|remove)\s+(?:model\s+)?(\S+)", text)
                if match:
                    model = match.group(1).strip()
                    return f"To remove '{model}', run:\n  ollama delete {model}\n\n⚠️ This will delete the model locally."
                return "Usage: ollama delete <model_name>"

            # Start Ollama
            if "start" in text or "serve" in text:
                return "To start Ollama, run:\n  ollama serve\n\nOr install as a service."

            return "Ollama commands: status | list | pull <model> | delete <model>"

        except Exception as e:
            return f"Ollama error: {e}"

    async def _handle_groq_query(self, user_input: str) -> str:
        """Handle Groq-specific commands."""
        text = user_input.lower()

        try:
            from jarvis.api.providers import ProviderType, get_provider_manager

            manager = get_provider_manager()

            # Groq status
            if "status" in text:
                if ProviderType.GROQ in manager.providers:
                    groq = manager.providers[ProviderType.GROQ]
                    if groq.is_available:
                        return f"[Groq Status]\n✓ Connected\nModel: {groq.model}"
                    return f"[Groq Status]\n✗ Unavailable\nError: {groq.last_error}"
                return "[Groq Status]\n○ Not configured"

            # List Groq models
            if "models" in text:
                try:
                    from jarvis.api.providers import get_provider_manager
                    pm = get_provider_manager()
                    return pm.format_models() or "No models available"
                except Exception:
                    return "Use the Model Manager view to see available models"

            # API key
            if "api" in text or "key" in text:
                return """[Provider API Keys]
Configure API keys in ~/.jarvis/api_keys.json or set environment variables:
  - GROQ_API_KEY for Groq
  - OPENAI_API_KEY for OpenAI
  - GOOGLE_API_KEY or GEMINI_API_KEY for Gemini
  - ANTHROPIC_API_KEY for Anthropic
  - OPENROUTER_API_KEY for OpenRouter

Local models (Ollama, LM Studio, AirLLM) require no API key."""

            # Use Groq
            if "use groq" in text or "switch to groq" in text:
                if ProviderType.GROQ in manager.providers:
                    manager.set_primary(ProviderType.GROQ)
                    return "Switched to Groq (cloud AI)."
                return "Groq is not configured. Set your API key first."

            return "Groq commands: status | models | api | use groq"

        except Exception as e:
            return f"Groq error: {e}"

    async def _handle_provider_query(self, user_input: str) -> str:
        """Handle provider/model queries."""
        from jarvis.api.providers import get_provider_manager

        text = user_input.lower()
        manager = get_provider_manager()

        # List models
        if "list model" in text or "show models" in text:
            return f"Available models:\n{manager.format_models()}"

        # Current model
        if "current model" in text or "what model" in text:
            model = manager.get_current_model()
            return f"Current Model: {model}"

        # Benchmark models
        if "benchmark" in text:
            results = await manager.benchmark_models()
            if results:
                lines = ["[Benchmark Results]", "=" * 40]
                for model, data in results.items():
                    if "error" in data:
                        lines.append(f"\n{model}: ERROR - {data['error']}")
                    else:
                        lines.append(f"\n{model}:")
                        lines.append(f"  Latency: {data['latency']}s")
                        lines.append(f"  Tokens: {data['tokens']}")
                        lines.append(f"  Provider: {data['provider']}")
                return "\n".join(lines)
            return "No benchmark results available"

        # Compare models
        if "compare" in text:
            match = re.search(r"compare\s+(.+?)\s+(?:vs|with|and)\s+(.+)", text)
            if match:
                model1, model2 = match.group(1).strip(), match.group(2).strip()
                return manager.compare_models(model1, model2)
            return "Usage: compare model1 vs model2"

        # Switch provider
        if "switch provider" in text or "switch to" in text or "use model" in text:
            match = re.search(r"(?:switch|use|to)\s+(?:provider\s+)?(\S+)", text)
            if match:
                model = match.group(1).strip()
                if manager.set_model(model):
                    return f"Provider switched successfully to {model}"
                return f"Could not switch to model: {model}"
            return "Usage: switch provider <model_name>"

        # Provider status (default)
        return manager.format_status()

    async def _handle_memory_store(self, user_input: str) -> str:
        """
        Handle memory storage requests.

        Args:
            user_input: The user's message containing info to remember

        Returns:
            Confirmation message
        """
        text = user_input.lower()

        # Extract what to remember
        # Pattern: "remember my [key] is [value]"
        match = re.search(r"remember\s+(?:my\s+)?(.+?)\s+is\s+(.+)", text)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            self.memory.remember(key, value, "personal")
            return f"Got it! I'll remember that your {key} is {value}."

        # Pattern: "save that I like [thing]"
        match = re.search(r"(?:save that\s+)?I\s+(?:like|prefer|hate|enjoy)\s+(.+)", text)
        if match:
            value = match.group(1).strip()
            self.memory.remember("preference", value, "personal")
            return f"Noted! You {user_input.split()[2]} {value}."

        # Pattern: "my favorite is X"
        match = re.search(r"(?:my\s+)?favorite\s+(?:.+?)\s+is\s+(.+)", text)
        if match:
            value = match.group(1).strip()
            self.memory.remember("favorite", value, "personal")
            return f"Alright! Your favorite is {value}."

        # Default: store the whole thing
        self.memory.remember("fact", user_input, "personal")
        return "I'll keep that in mind."

    async def _handle_memory_recall(self, user_input: str) -> str:
        """
        Handle memory recall requests.

        Args:
            user_input: The user's query

        Returns:
            Retrieved information
        """
        text = user_input.lower()

        # Try to extract what to recall
        # Pattern: "what is my favorite X"
        match = re.search(r"what(?:\'s| is)\s+my\s+(?:favorite\s+)?(.+)", text)
        if match:
            query = match.group(1).strip()
            results = self.memory.recall(query)
            if results:
                return f"You mentioned that your {query} is {results[0].get('value', 'something')}"
            return f"I don't have any information about your {query} stored yet."

        # Pattern: "do you remember my X"
        match = re.search(r"(?:do you\s+)?remember\s+(?:my\s+)?(.+)", text)
        if match:
            query = match.group(1).strip()
            results = self.memory.recall(query)
            if results:
                return f"Yes! Your {query} is {results[0].get('value', 'stored')}"
            return "I don't have that information stored yet."

        # Default: search memory
        results = self.memory.recall(text)
        if results:
            return f"From what you've told me: {results[0].get('value', 'something')}"

        return "I don't have any relevant information stored yet. Is there something specific you'd like me to remember?"

    async def execute_task(self, task: str) -> str:
        """
        Execute a task using the planner and executor.

        Args:
            task: The task to execute

        Returns:
            Execution result
        """
        self.speak("Processing your request...")

        # Get context from memory
        context = self.memory.format_for_prompt()

        # Execute through planner/executor
        result = await self.executor.execute(task, context)

        if result.success:
            self.speak(result.summary)
            return result.summary
        else:
            error_msg = result.error or "Task failed"
            self.speak(f"I encountered an issue: {error_msg}")
            return f"I encountered an issue: {error_msg}\n\nCompleted steps: {len(result.completed_steps)}"

    async def answer_query(self, query: str) -> str:
        """
        Answer a conversational query using the LLM.

        The LLM's role is to explain, summarize, and format responses.
        Execution authority belongs strictly to CapabilityRouter / Planner.
        """
        system_prompt = self._build_system_prompt()


        # Prefer the ProviderManager if it has a usable provider (e.g. Ollama locally).
        manager = getattr(self, "provider_manager", None)
        if manager is not None and manager.primary_provider is None:
            with contextlib.suppress(Exception):
                await manager.initialize()
        if manager is not None and manager.primary_provider is not None:
            primary = manager.providers.get(manager.primary_provider)
            if primary is not None and primary.is_available:
                try:
                    full_prompt = f"{system_prompt}\n\nUser: {query}"
                    response = await manager.generate(full_prompt)
                    content = response.content
                    if content:
                        if self.config.voice_enabled:
                            self.speak(content)
                        return _sanitize_response(content)
                except Exception as e:
                    logger.debug("ProviderManager chat failed, falling back: %s", e)

        response = await self.llm.generate_with_history(
            messages=[{"role": "user", "content": query}],
            system=system_prompt,
            temperature=0.7,
            max_tokens=2048,
        )

        if isinstance(response, str) and response.startswith("Error:"):
            error_response = (
                "I couldn't reach any AI provider. "
                "Please check that Ollama is running or configure a cloud provider API key. "
                "You can also run 'ollama list' to see installed local models."
            )
            if self.config.voice_enabled:
                self.speak(error_response)
            return error_response

        response = _sanitize_response(response)
        if self.config.voice_enabled:
            self.speak(response)
        return response

    async def execute_command(self, command: str, **kwargs) -> ToolResult:
        """
        Execute a single tool command directly.

        Args:
            command: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        return await self.tools.execute(command, kwargs)

    def remember(self, key: str, value: str, category: str = "notes") -> str:
        """Store information in memory."""
        self.memory.remember(key, value, category)
        return f"Remembered: {key}"

    def recall(self, query: str) -> list[dict]:
        """Recall from memory."""
        return self.memory.recall(query)

    def get_history_summary(self) -> dict:
        """Get session history summary."""
        return self.memory.get_history_summary()

    async def start(self):
        """Start the agent."""
        self._is_running = True
        logger.info("Agent started")

    async def stop(self):
        """Stop the agent."""
        self._is_running = False
        logger.info("Agent stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running


# Factory function
def create_jarvis(config: Config | None = None, api_key: str | None = None) -> JarvisAgent:
    """
    Create a configured JARVIS agent.

    Args:
        config: Optional configuration
        api_key: Optional API key for LLM (used for any configured provider)

    Returns:
        Configured JarvisAgent
    """
    if config is None:
        config = get_config()

    if api_key:
        config.set_api_key("groq", api_key)

    llm = None
    try:
        llm = SimpleLLMClient(backend="groq", api_key=api_key)
        if not llm.is_available():
            logger.info("Legacy Groq client unavailable; provider_manager will be primary.")
            llm = None
    except Exception:
        logger.info("Legacy LLM client init skipped; provider_manager will be primary.")

    agent = JarvisAgent(config=config, llm_client=llm)

    try:
        from jarvis.api.providers import (
            AnthropicProvider,
            GoogleProvider,
            GroqProvider,
            LLMConfig,
            LMStudioProvider,
            OllamaProvider,
            OpenAIProvider,
            OpenRouterProvider,
            ProviderType,
            get_provider_manager,
        )

        manager = get_provider_manager()

        airllm_cfg = LLMConfig(
            provider=ProviderType.AIRLLM,
            model=config.get("airllm_model") if hasattr(config, "get") else None,
            max_tokens=4096,
            timeout=300.0,
        )
        try:
            from jarvis.providers.airllm.provider import AirLLMProvider

            manager.add_provider(AirLLMProvider(airllm_cfg))
        except Exception as exc:
            logger.debug("AirLLM provider init skipped: %s", exc)

        ollama_cfg = LLMConfig(
            provider=ProviderType.OLLAMA,
            model=config.get("ollama_model") if hasattr(config, "get") else None,
            base_url="http://localhost:11434",
            timeout=300.0,
        )
        manager.add_provider(OllamaProvider(ollama_cfg))

        groq_key = api_key
        if not groq_key:
            import os
            groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key and hasattr(config, "get_api_key"):
            groq_key = config.get_api_key("groq")
        if groq_key:
            manager.add_provider(
                GroqProvider(
                    LLMConfig(
                        provider=ProviderType.GROQ,
                        model=config.get("live_model") if hasattr(config, "get") else None,
                        api_key=groq_key,
                    )
                )
            )

        openai_key = None
        if hasattr(config, "get_api_key"):
            openai_key = config.get_api_key("openai")
        if not openai_key:
            import os
            openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            manager.add_provider(
                OpenAIProvider(
                    LLMConfig(
                        provider=ProviderType.OPENAI,
                        model=config.get("openai_model") if hasattr(config, "get") else None,
                        api_key=openai_key,
                    )
                )
            )

        google_key = None
        if hasattr(config, "get_api_key"):
            google_key = config.get_api_key("google")
        if not google_key:
            import os
            google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if google_key:
            manager.add_provider(
                GoogleProvider(
                    LLMConfig(
                        provider=ProviderType.GOOGLE,
                        model=config.get("google_model") if hasattr(config, "get") else None,
                        api_key=google_key,
                    )
                )
            )

        anthropic_key = None
        if hasattr(config, "get_api_key"):
            anthropic_key = config.get_api_key("anthropic")
        if not anthropic_key:
            import os
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            manager.add_provider(
                AnthropicProvider(
                    LLMConfig(
                        provider=ProviderType.ANTHROPIC,
                        model=config.get("anthropic_model") if hasattr(config, "get") else None,
                        api_key=anthropic_key,
                    )
                )
            )

        openrouter_key = None
        if hasattr(config, "get_api_key"):
            openrouter_key = config.get_api_key("openrouter")
        if not openrouter_key:
            import os
            openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            manager.add_provider(
                OpenRouterProvider(
                    LLMConfig(
                        provider=ProviderType.OPENROUTER,
                        model=config.get("openrouter_model") if hasattr(config, "get") else None,
                        api_key=openrouter_key,
                    )
                )
            )

        lmstudio_cfg = LLMConfig(
            provider=ProviderType.LMSTUDIO,
            model=config.get("lmstudio_model") if hasattr(config, "get") else None,
            base_url="http://localhost:1234",
            timeout=300.0,
        )
        manager.add_provider(LMStudioProvider(lmstudio_cfg))

        agent.provider_manager = manager
    except Exception as e:
        logger.debug(f"Provider manager init skipped: {e}")

    return agent


def get_llm_client(backend: str = "groq", api_key: str | None = None) -> SimpleLLMClient | None:
    """Return a ready-to-use SimpleLLMClient, or None if unavailable."""
    try:
        client = SimpleLLMClient(backend=backend, api_key=api_key)
        if client.is_available():
            return client
    except Exception:
        pass
    return None
