"""
JARVIS CLI - Command-line interface.
"""

import asyncio
import logging
import os
import sys

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from jarvis.core.agent import JarvisAgent, create_jarvis
from jarvis.tools.file_tools import (
    DeleteFileTool,
    DiskUsageTool,
    FindFilesTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from jarvis.tools.registry import get_registry
from jarvis.tools.system_tools import (
    GetClipboardTool,
    GetEnvironmentTool,
    GetSystemInfoTool,
    OpenAppTool,
    SetClipboardTool,
    SetEnvironmentTool,
)
from jarvis.tools.terminal_tools import BashTool, CreateTempFileTool, RunScriptTool

logger = logging.getLogger(__name__)


class JarvisCLI:
    """
    Command-line interface for JARVIS.
    """

    def __init__(self, agent: JarvisAgent | None = None):
        self.console = Console() if HAS_RICH else None
        self.agent = agent
        self._running = False

    def _print(self, message: str, style: str = ""):
        """Print a message."""
        if self.console:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        else:
            print(message)

    def _print_panel(self, title: str, content: str):
        """Print a panel."""
        if self.console:
            self.console.print(Panel(content, title=title))
        else:
            print(f"=== {title} ===")
            print(content)

    def _print_markdown(self, content: str):
        """Print markdown content."""
        if self.console:
            self.console.print(Markdown(content))
        else:
            print(content)

    def register_tools(self):
        """Register all tools with the registry."""
        registry = get_registry()

        # File tools
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())
        registry.register(ListDirectoryTool())
        registry.register(FindFilesTool())
        registry.register(DeleteFileTool())
        registry.register(DiskUsageTool())

        # Terminal tools
        registry.register(BashTool())
        registry.register(RunScriptTool())
        registry.register(CreateTempFileTool())

        # System tools
        registry.register(GetSystemInfoTool())
        registry.register(OpenAppTool())
        registry.register(GetEnvironmentTool())
        registry.register(SetEnvironmentTool())
        registry.register(GetClipboardTool())
        registry.register(SetClipboardTool())

    async def initialize(self, api_key: str | None = None):
        """Initialize the CLI and agent."""
        self.register_tools()
        self.agent = create_jarvis(api_key=api_key)

        await self._start_v7_background()

        # Initialize voice runtime for TTS
        try:
            from jarvis.voice.voice_runtime import get_voice_runtime

            voice_runtime = get_voice_runtime()
            await voice_runtime.initialize()

            def _speak_callback(text: str):
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(voice_runtime.speak(text))
                except RuntimeError:
                    pass

            self.agent.set_speak_callback(_speak_callback)
            print("[Jarvis] Voice output enabled")
        except Exception as e:
            print(f"[Jarvis] Voice output unavailable: {e}")

        await self.agent.start()

    async def _start_v7_background(self) -> None:
        """Start JARVIS-V7 background evolution if available."""
        try:
            from jarvis.evolution.v7_orchestrator import get_v7_orchestrator
            v7 = get_v7_orchestrator()
            await v7.start_background()
            print("[Jarvis-V7] Background evolution engine started")
        except Exception as e:
            print(f"[Jarvis-V7] Background evolution unavailable: {e}")

    def print_banner(self):
        """Print the JARVIS banner."""
        banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║     ██╗    ██╗ █████╗ ██████╗ ███╗   ██╗██╗  ██╗ ║
║     ██║    ██║██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝ ║
║     ██║ █╗ ██║███████║██████╔╝██╔██╗ ██║█████╔╝  ║
║     ██║███╗██║██╔══██║██╔══██╗██║╚██╗██║██╔═██╗  ║
║     ╚███╔███╔╝██║  ██║██║  ██║██║ ╚████║██║  ██╗ ║
║      ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ║
║                                                      ║
║   Just A Rather Very Intelligent System              ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
        """
        self._print(banner, style="bold blue")

    def print_help(self):
        """Print help information."""
        help_text = """
# JARVIS Commands

## Direct Commands
- `help` - Show this help message
- `tools` - List available tools
- `status` - Show agent status
- `memory` - Show stored memory
- `clear` - Clear the screen
- `exit` / `quit` - Exit JARVIS

## Interacting with JARVIS
Just type your request naturally! For example:
- "Read the file at ~/notes.txt"
- "List the files in the current directory"
- "Show me system information"
- "Create a file called hello.py with hello world"
- "What is my home directory?"

## Tool Commands
You can also use tools directly:
- `read <path>` - Read a file
- `write <path> <content>` - Write a file
- `ls <path>` - List directory
- `find <pattern>` - Find files
- `bash <command>` - Run shell command
        """
        self._print_markdown(help_text)

    def print_tools(self):
        """Print available tools."""
        registry = get_registry()
        tools = registry.get_all()

        if self.console:
            table = Table(title="Available Tools")
            table.add_column("Name", style="cyan")
            table.add_column("Category", style="green")
            table.add_column("Description")

            for tool in tools:
                table.add_row(tool.name, tool.category, tool.description)

            self.console.print(table)
        else:
            self._print("=== Available Tools ===")
            for tool in tools:
                self._print(f"  {tool.name}: {tool.description}")

    def print_status(self):
        """Print agent status."""
        if not self.agent:
            self._print("Agent not initialized", style="red")
            return

        summary = self.agent.get_history_summary()

        if self.console:
            table = Table(title="JARVIS Status")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Status", "Running" if self.agent.is_running else "Stopped")
            table.add_row("Total Messages", str(summary.get("total_messages", 0)))
            table.add_row("User Messages", str(summary.get("user_messages", 0)))
            table.add_row("Assistant Messages", str(summary.get("assistant_messages", 0)))
            table.add_row("Tool Calls", str(summary.get("tool_calls", 0)))

            self.console.print(table)
        else:
            self._print("=== JARVIS Status ===")
            self._print(f"Status: {'Running' if self.agent.is_running else 'Stopped'}")
            self._print(f"Total Messages: {summary.get('total_messages', 0)}")

    def print_evolution_status(self):
        """Print JARVIS-V7 evolution system status."""
        try:
            from jarvis.evolution.v7_orchestrator import get_v7_orchestrator
            v7 = get_v7_orchestrator()
            status = v7.get_evolution_status()

            if self.console:
                table = Table(title="JARVIS-V7 Evolution Status")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                evo = status.get("evolution_engine", {})
                table.add_row("Evolution Running", str(evo.get("running", False)))
                table.add_row("Total Experiences", str(evo.get("total_experiences", 0)))
                table.add_row("Total Reflections", str(evo.get("total_reflections", 0)))
                table.add_row("Candidates Trained", str(evo.get("total_candidates_trained", 0)))
                table.add_row("CPU Usage", f"{evo.get('cpu_usage', 0):.1f}%")
                table.add_row("RAM Usage", f"{evo.get('ram_usage', 0):.1f}%")

                registry = status.get("model_registry", {})
                table.add_row("Total Models", str(registry.get("total_models", 0)))
                for stage, count in registry.get("by_stage", {}).items():
                    table.add_row(f"  Models {stage}", str(count))

                kg = status.get("knowledge_graph", {})
                table.add_row("Graph Nodes", str(kg.get("nodes", 0)))
                table.add_row("Graph Edges", str(kg.get("edges", 0)))

                insights = status.get("experience_insights", {})
                table.add_row("Experience Success Rate", f"{insights.get('success_rate', 0):.2%}")

                suggestions = status.get("improvement_suggestions", [])
                if suggestions:
                    table.add_row("Improvements", str(len(suggestions)))

                self.console.print(table)
            else:
                self._print("=== JARVIS-V7 Evolution Status ===")
                evo = status.get("evolution_engine", {})
                self._print(f"Running: {evo.get('running', False)}")
                self._print(f"Experiences: {evo.get('total_experiences', 0)}")
                self._print(f"Reflections: {evo.get('total_reflections', 0)}")
                self._print(f"Candidates Trained: {evo.get('total_candidates_trained', 0)}")
                registry = status.get("model_registry", {})
                self._print(f"Models: {registry.get('total_models', 0)}")
                kg = status.get("knowledge_graph", {})
                self._print(f"Graph: {kg.get('nodes', 0)} nodes, {kg.get('edges', 0)} edges")
        except Exception as e:
            self._print(f"Evolution status unavailable: {e}", style="red")

    def print_memory(self):
        """Print stored memory."""
        if not self.agent:
            self._print("Agent not initialized", style="red")
            return

        memory_str = self.agent.memory.format_for_prompt()

        if memory_str:
            self._print_panel("Long-term Memory", memory_str)
        else:
            self._print("No memory stored yet.", style="yellow")

    async def handle_direct_command(self, command: str) -> bool:
        """
        Handle a direct command (starting with / or specific keywords).

        Returns:
            True if command was handled, False otherwise
        """
        cmd = command.strip().lower()

        if cmd in ["help", "/help", "-h", "--help"]:
            self.print_help()
            return True

        if cmd in ["tools", "/tools"]:
            self.print_tools()
            return True

        if cmd in ["status", "/status"]:
            self.print_status()
            return True

        if cmd in ["evolution", "/evolution", "v7"]:
            self.print_evolution_status()
            return True

        if cmd in ["memory", "/memory"]:
            self.print_memory()
            return True

        if cmd in ["clear", "/clear", "cls"]:
            if self.console:
                self.console.clear()
            else:
                import os

                os.system("cls" if os.name == "nt" else "clear")
            return True

        if cmd in ["exit", "quit", "/exit", "/quit", "q"]:
            await self.shutdown()
            return True

        return False

    async def shutdown(self):
        """Shutdown the CLI."""
        self._running = False
        try:
            from jarvis.evolution.v7_orchestrator import get_v7_orchestrator
            v7 = get_v7_orchestrator()
            await v7.stop_background()
        except Exception:
            pass
        if self.agent:
            await self.agent.stop()
        self._print("Goodbye, sir.", style="bold blue")

    async def run(self):
        """Run the CLI."""
        self.print_banner()

        # Initialize if needed
        if not self.agent:
            await self.initialize()

        self._running = True

        # Auto-start wake-word listening
        try:
            from jarvis.voice.voice_runtime import get_voice_runtime

            voice_runtime = get_voice_runtime()
            await voice_runtime.start_wake_word_listening(agent=self.agent)
            self._print("[Jarvis] Wake-word listening active. Say 'Hey Jarvis' to wake me.\n")
        except Exception as e:
            self._print(f"[Jarvis] Wake-word unavailable: {e}\n")

        self._print("\nType 'help' for available commands or just ask me anything!\n")

        while self._running:
            try:
                # Get input
                if self.console:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: Prompt.ask("[bold cyan]You[/bold cyan]")
                    )
                else:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("You: ")
                    )

                if not user_input.strip():
                    continue

                # Check for direct commands
                if await self.handle_direct_command(user_input):
                    continue

                # Process through agent
                self._print("\n[JARVIS] Processing...", style="yellow")

                response = await self.agent.process(user_input)

                self._print(f"\n[bold blue]JARVIS:[/bold blue] {response}\n")

            except KeyboardInterrupt:
                self._print("\n", end="")
                break
            except EOFError:
                self._print("\nNon-interactive session detected. Goodbye.")
                break
            except Exception as e:
                self._print(f"\nError: {e}", style="red")

        await self.shutdown()


async def run_cli(api_key: str | None = None):
    """Run the JARVIS CLI."""
    cli = JarvisCLI()
    await cli.initialize(api_key=api_key)
    await cli.run()


if __name__ == "__main__":
    # Allow passing API key via environment variable (not CLI arg for security)
    api_key = os.environ.get("JARVIS_API_KEY")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        logger.warning(
            "Passing API key as CLI argument is insecure; use JARVIS_API_KEY env var instead"
        )

    asyncio.run(run_cli(api_key=api_key))
