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
    r"^\s*(search|find|grep)\s+",
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

    # Check for provider/model queries
    for pattern in PROVIDER_QUERY_PATTERNS:
        if re.search(pattern, text):
            return Intent.PROVIDER_QUERY

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
