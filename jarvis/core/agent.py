"""
JARVIS Main Agent
The core AI assistant that combines all components.
"""

from typing import Any, Callable, Dict, List, Optional

from jarvis.core.config import Config, get_config
from jarvis.core.planner import Planner
from jarvis.core.executor import Executor
from jarvis.memory.memory_manager import MemoryManager
from jarvis.tools.base import ToolResult
from jarvis.tools.registry import ToolRegistry, get_registry
from jarvis.api.gemini import SimpleLLMClient


SYSTEM_PROMPT = """You are JARVIS, Just A Rather Very Intelligent System.
You are a helpful AI assistant that can help users with various tasks.

Your capabilities:
- File operations (read, write, list, search, delete)
- Terminal/command execution
- System information and control
- Memory of personal facts and preferences
- Planning and executing multi-step tasks

Guidelines:
- Be concise and helpful
- Use tools to accomplish tasks - never guess
- Remember personal information for future reference
- Execute commands safely and report results clearly
- Address the user respectfully

Available tools:
{tools}

Personal memory:
{memory}

Remember to use the appropriate tool for each task. If you need to run a command, use bash.
If you need to read a file, use read_file. If you need to write a file, use write_file.
"""


class JarvisAgent:
    """
    Main JARVIS agent that orchestrates all components.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        memory_manager: Optional[MemoryManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        llm_client: Optional[Any] = None
    ):
        self.config = config or get_config()
        self.memory = memory_manager or MemoryManager()
        self.tools = tool_registry or get_registry()
        self.llm = llm_client or SimpleLLMClient()

        # Initialize planner and executor
        self.planner = Planner(llm_client=self.llm)
        self.executor = Executor(self.tools, self.planner)

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

        # Check if input looks like a task to execute
        task_keywords = ["do ", "execute ", "run ", "create ", "find ", "open ", "search ",
                        "tell me about", "what is", "show me", "list "]

        is_task = any(user_input.lower().startswith(kw) for kw in task_keywords)

        # Simple heuristic: longer inputs or specific keywords are tasks
        if len(user_input) > 50 or any(kw in user_input.lower() for kw in
            ["帮我", "请", "could you", "can you", "please", "would you"]):
            is_task = True

        if is_task:
            # Execute as a task
            result = await self.execute_task(user_input)
            self.memory.add_assistant_message(result)
            return result
        else:
            # Process as a query
            response = await self.answer_query(user_input)
            self.memory.add_assistant_message(response)
            return response

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
        Answer a query using the LLM.

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
        config.set_api_key("gemini", api_key)

    # Create LLM client (default to Groq)
    llm = SimpleLLMClient(backend="groq", api_key=api_key)

    # Create agent
    agent = JarvisAgent(
        config=config,
        llm_client=llm
    )

    return agent
