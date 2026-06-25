"""
JARVIS Main Agent
The core AI assistant that combines all components with intent classification.
"""

import re
from typing import Any, Callable, Dict, List, Optional

from jarvis.core.config import Config, get_config
from jarvis.core.planner import Planner
from jarvis.core.executor import Executor
from jarvis.memory.enhanced import EnhancedMemoryManager, get_enhanced_memory
from jarvis.rag import RAGSystem, get_rag_system
from jarvis.tools.base import ToolResult
from jarvis.tools.registry import ToolRegistry, get_registry
from jarvis.api.gemini import SimpleLLMClient


# Intent types
class Intent:
    CHAT = "chat"              # General conversation/questions
    MEMORY_STORE = "memory_store"  # Remember/save information
    MEMORY_RECALL = "memory_recall"  # Recall/remember information
    PROFILE_QUERY = "profile_query"  # Profile-related queries
    RAG_QUERY = "rag_query"    # RAG/knowledge base queries
    PROVIDER_QUERY = "provider_query"  # Provider/model status queries
    VOICE_STATUS = "voice_status"  # Voice system status queries
    VOICE_CONTROL = "voice_control"  # Voice start/stop/listen
    VOICE_CONFIG = "voice_config"  # Voice calibration/test/devices
    REPO_QUERY = "repo_query"  # Repository analysis queries
    TOOL_EXECUTION = "tool_execution"  # Explicit tool/task execution


# Keywords for intent classification
MEMORY_STORE_PATTERNS = [
    r"^\s*remember\b",           # Starts with "remember"
    r"^\s*save\b",                # Starts with "save"
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
    r"\bstart\s+voice\b",
    r"\bstop\s+voice\b",
    r"\blistening\s+(?:on|start|begin)\b",
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


SYSTEM_PROMPT = """You are JARVIS, Just A Rather Very Intelligent System.
You are a helpful AI assistant that can help users with various tasks.

Your capabilities:
- Answer questions about any topic
- Remember personal facts and preferences
- File operations (read, write, list, search, delete)
- Terminal/command execution
- Planning and executing multi-step tasks

Guidelines:
- Be concise and helpful
- Answer factual questions directly without using tools
- Use tools only when explicitly needed for system operations
- Remember personal information for future reference
- Execute commands safely and report results clearly
- Address the user respectfully

Personal memory:
{memory}

Available tools (use only when system operations are needed):
{tools}
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

    # Check for provider/model queries
    for pattern in PROVIDER_QUERY_PATTERNS:
        if re.search(pattern, text):
            return Intent.PROVIDER_QUERY

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
    if len(text) < 30 or any(casual in text for casual in 
        ["hey", "hi ", "hello", "thanks", "thank you", "please"]):
        return Intent.CHAT
    
    # If it sounds like a question or explanation, stay in chat
    if text.endswith("?") or text.startswith(("what", "how", "why", "who", "explain")):
        return Intent.CHAT
    
    # Default to chat mode
    return Intent.CHAT


class JarvisAgent:
    """
    Main JARVIS agent that orchestrates all components.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        memory_manager: Optional[EnhancedMemoryManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        llm_client: Optional[Any] = None
    ):
        self.config = config or get_config()
        # Use enhanced memory manager for better profile support
        self.memory = memory_manager or get_enhanced_memory()
        self.tools = tool_registry or get_registry()
        self.llm = llm_client or SimpleLLMClient()

        # Initialize planner and executor
        self.planner = Planner(llm_client=self.llm)
        self.executor = Executor(self.tools, self.planner)
        
        # Initialize RAG system
        self.rag = get_rag_system()

        # State
        self._is_running = False
        self._speak_callback: Optional[Callable] = None
        self._message_handlers: List[Callable] = []

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
                self._speak_callback(message)
            except Exception as e:
                print(f"[Jarvis] Speak error: {e}")
                print(f"[Jarvis] Message: {message}")

    def _format_tools(self) -> str:
        """Format available tools for the prompt."""
        tools = self.tools.get_tools_for_prompt()

        lines = []
        for tool in tools:
            lines.append(f"- {tool['name']}: {tool['description']}")

        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tools and memory."""
        tools_str = self._format_tools()
        memory_str = self.memory.format_for_prompt()

        return SYSTEM_PROMPT.format(
            tools=tools_str,
            memory=memory_str if memory_str else "(no memory stored)"
        )

    async def process(self, user_input: str) -> str:
        """
        Process a user input and generate a response.

        Args:
            user_input: The user's message or command

        Returns:
            JARVIS's response
        """
        # Add to session memory
        self.memory.add_user_message(user_input)

        # Classify intent
        intent = classify_intent(user_input)

        # Route based on intent
        if intent == Intent.PROFILE_QUERY:
            result = await self._handle_profile_query(user_input)
        elif intent == Intent.MEMORY_STORE:
            result = await self._handle_memory_store(user_input)
        elif intent == Intent.MEMORY_RECALL:
            result = await self._handle_memory_recall(user_input)
        elif intent == Intent.RAG_QUERY:
            result = await self._handle_rag_query(user_input)
        elif intent == Intent.VOICE_STATUS:
            result = await self._handle_voice_status(user_input)
        elif intent == Intent.VOICE_CONTROL:
            result = await self._handle_voice_control(user_input)
        elif intent == Intent.VOICE_CONFIG:
            result = await self._handle_voice_config(user_input)
        elif intent == Intent.REPO_QUERY:
            result = await self._handle_repo_query(user_input)
        elif intent == Intent.PROVIDER_QUERY:
            result = await self._handle_provider_query(user_input)
        elif intent == Intent.TOOL_EXECUTION:
            result = await self.execute_task(user_input)
        else:
            # CHAT - answer directly without tools
            result = await self.answer_query(user_input)

        self.memory.add_assistant_message(result)
        return result


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
        if any(pattern in text_lower for pattern in ["who am i", "my profile", "summarize", "about me", "what do you know"]):
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

    async def _handle_rag_query(self, user_input: str) -> str:
        """
        Handle RAG/knowledge base queries.
        
        Args:
            user_input: The user's query
            
        Returns:
            RAG response
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
            results = await self.rag.search(text_lower.replace("summarize", ""), limit=5)
            if results:
                summary_parts = [r.get('content', '')[:200] for r in results[:3]]
                return "Based on your knowledge base:\n\n" + "\n\n".join(summary_parts)
            return "I couldn't find relevant content to summarize. Try ingesting a document first."
        
        # Handle question generation
        if "question" in text_lower:
            # Search for relevant content
            results = await self.rag.search(text_lower.replace("generate", "").replace("question", ""), limit=3)
            if results:
                content = " ".join([r.get('content', '')[:300] for r in results])
                return f"Based on your documents, here are some questions:\n\n1. What are the main concepts covered in this topic?\n2. How would you explain the key points?\n3. What examples illustrate this concept?"
            return "I couldn't find relevant content. Try ingesting a document first."
        
        # Handle revision notes
        if "revision" in text_lower or "notes" in text_lower:
            results = await self.rag.search(text_lower, limit=5)
            if results:
                notes = ["📝 Revision Notes:\n"]
                for i, r in enumerate(results, 1):
                    content = r.get('content', '')[:150]
                    notes.append(f"{i}. {content}...")
                return "\n".join(notes)
            return "I couldn't find relevant content for revision notes."
        
        # Default: search knowledge base
        results = await self.rag.search(text_lower, limit=5)
        if results:
            response = "From your knowledge base:\n\n"
            for i, r in enumerate(results, 1):
                content = r.get('content', '')
                response += f"📄 {i}. {content[:300]}"
                if len(content) > 300:
                    response += "..."
                response += "\n\n"
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
                result = analyzer.analyze()
                return analyzer.format_summary()

            elif "architecture" in text or "show architecture" in text:
                arch = analyzer.get_architecture()
                lines = ["[Repository Architecture]", "=" * 40, ""]
                lines.append("Modules:")
                for module, files in arch.get("modules", {}).items():
                    lines.append(f"  📁 {module}/")
                    for f in files[:5]:
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
                lines = ["[Dependencies]", "=" * 40, ""]
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
                security = scanner.scan_directory(str(repo_path))
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

                if summary['by_severity']['critical'] > 0 or summary['by_severity']['high'] > 0:
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
            from jarvis.voice.voice_runtime import get_voice_runtime, VoiceRuntime

            runtime = get_voice_runtime()
            if runtime is None:
                return "Voice system not initialized. Run: python setup_voice.sh (Linux) or setup_voice.ps1 (Windows)"

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
            
            # Voice start / listen
            if any(x in text for x in ["start", "listen", "begin", "activate"]):
                if runtime._running:
                    return "Voice is already listening."
                runtime._running = True
                return "Voice activated. I'm listening..."
            
            # Voice stop / pause
            if any(x in text for x in ["stop", "pause", "deactivate", "silence"]):
                if not runtime._running:
                    return "Voice is already stopped."
                runtime._running = False
                return "Voice deactivated."
            
            return "Usage: voice start | voice stop"
            
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
            if "test" in text and "mic" in text or "microphone" in text:
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

    async def _list_audio_devices(self) -> str:
        """List available audio input and output devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            lines = ["[Audio Devices]", "=" * 40]
            lines.append(f"\nDefault Input: {sd.query_devices(kind='input')['name']}")
            lines.append(f"Default Output: {sd.query_devices(kind='output')['name']}")
            lines.append("\nAll Devices:")
            
            if isinstance(devices, dict):
                devices = [devices]
            
            for i, dev in enumerate(devices):
                dev_type = "Input" if dev['max_input_channels'] > 0 else "Output"
                lines.append(f"\n  [{i}] {dev['name']}")
                lines.append(f"      Type: {dev_type}, Channels: {dev['max_input_channels'] or dev['max_output_channels']}")
                lines.append(f"      Sample Rate: {dev['default_samplerate']} Hz")
            
            return "\n".join(lines)
            
        except ImportError:
            return "sounddevice not installed. Install with: pip install sounddevice"
        except Exception as e:
            return f"Error listing devices: {e}"

    async def _test_microphone(self) -> str:
        """Test microphone input."""
        try:
            import sounddevice as sd
            import numpy as np
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio status: {status}")
                audio_data = indata.flatten()
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                level = min(100, int(rms / 100))
                
            lines = ["[Microphone Test]", "=" * 40]
            lines.append("\nListening for 3 seconds...")
            lines.append("Speak into your microphone now.\n")
            
            try:
                stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=16000)
                with stream:
                    sd.sleep(3000)
                lines.append("✓ Microphone is working!")
                lines.append("Audio levels detected successfully.")
            except Exception as e:
                lines.append(f"✗ Microphone test failed: {e}")
            
            return "\n".join(lines)
            
        except ImportError:
            return "sounddevice not installed."
        except Exception as e:
            return f"Microphone test error: {e}"

    async def _test_speaker(self) -> str:
        """Test speaker output."""
        try:
            import sounddevice as sd
            
            lines = ["[Speaker Test]", "=" * 40]
            lines.append("\nPlaying test tone...")
            
            try:
                # Generate a simple sine wave tone
                import numpy as np
                frequency = 440  # Hz (A4 note)
                duration = 0.5   # seconds
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
            import sounddevice as sd
            import numpy as np
            
            lines = ["[Voice Calibration]", "=" * 40]
            lines.append("\nCalibrating microphone...")
            lines.append("Please remain silent for 2 seconds, then speak.")
            
            try:
                audio_levels = []
                
                def callback(indata, frames, time_info, status):
                    audio_data = indata.flatten()
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                    audio_levels.append(rms)
                
                # Listen for background noise
                stream = sd.InputStream(callback=callback, channels=1, samplerate=16000)
                with stream:
                    sd.sleep(2000)
                
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
            
            return "\n".join(lines)
            
        except ImportError:
            return "sounddevice not installed."
        except Exception as e:
            return f"Calibration error: {e}"

    async def _handle_provider_query(self, user_input: str) -> str:
        """Handle provider/model queries."""
        from jarvis.api.providers import get_provider_manager, ProviderType

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
            return f"I don't have that information stored yet."
        
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
        Answer a query using the LLM (no tools).

        Args:
            query: The user's question

        Returns:
            Answer
        """
        system_prompt = self._build_system_prompt()

        response = await self.llm.generate_with_history(
            messages=[
                {"role": "user", "content": query}
            ],
            system=system_prompt,
            temperature=0.7,
            max_tokens=2048
        )

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

    def recall(self, query: str) -> List[Dict]:
        """Recall from memory."""
        return self.memory.recall(query)

    def get_history_summary(self) -> Dict:
        """Get session history summary."""
        return self.memory.get_history_summary()

    async def start(self):
        """Start the agent."""
        self._is_running = True
        print("[Jarvis] Agent started")

    async def stop(self):
        """Stop the agent."""
        self._is_running = False
        print("[Jarvis] Agent stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running


# Factory function
def create_jarvis(
    config: Optional[Config] = None,
    api_key: Optional[str] = None
) -> JarvisAgent:
    """
    Create a configured JARVIS agent.

    Args:
        config: Optional configuration
        api_key: Optional API key for LLM

    Returns:
        Configured JarvisAgent
    """
    # Initialize config
    if config is None:
        config = get_config()

    # Set API key if provided
    if api_key:
        config.set_api_key("groq", api_key)

    # Create LLM client (default to Groq)
    llm = SimpleLLMClient(backend="groq", api_key=api_key)

    # Create agent
    agent = JarvisAgent(
        config=config,
        llm_client=llm
    )

    return agent
