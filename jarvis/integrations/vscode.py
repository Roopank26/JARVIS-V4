"""
VS Code integration for JARVIS.
Provides two-way communication between JARVIS and VS Code.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for VS Code communication."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    EVENT = "event"


@dataclass
class EditorContext:
    """Context from VS Code editor."""
    current_file: Optional[str] = None
    current_file_content: Optional[str] = None
    cursor_position: tuple = (0, 0)
    selection: Optional[str] = None
    language: str = ""
    open_files: List[str] = None
    errors: List[Dict] = None
    terminal_output: Optional[str] = None
    workspace_root: Optional[str] = None

    def __post_init__(self):
        if self.open_files is None:
            self.open_files = []
        if self.errors is None:
            self.errors = []


@dataclass
class VSCodeMessage:
    """Message structure for VS Code communication."""
    id: str
    type: MessageType
    method: str
    params: Dict[str, Any] = None
    result: Any = None
    error: Optional[str] = None


class VSCodeBridge:
    """
    Bridge for VS Code extension communication.
    Provides JSON-RPC based communication with VS Code.
    """

    def __init__(self, port: int = 8765):
        self.port = port
        self._server = None
        self._connected = False
        self._client_reader = None
        self._client_writer = None
        self._handlers: Dict[str, Callable] = {}
        self._request_handlers: Dict[str, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start_server(self) -> bool:
        """Start the VS Code bridge server."""
        try:
            server = await asyncio.start_server(
                self._handle_client,
                host='127.0.0.1',
                port=self.port
            )
            self._server = server
            self._running = True
            
            addr = server.sockets[0].getsockname()
            logger.info(f"VS Code bridge started on {addr}")
            
            # Start message processor
            asyncio.create_task(self._process_messages())
            
            return True

        except Exception as e:
            logger.error(f"Failed to start VS Code bridge: {e}")
            return False

    async def stop_server(self) -> None:
        """Stop the VS Code bridge server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("VS Code bridge stopped")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming client connection."""
        self._client_reader = reader
        self._client_writer = writer
        self._connected = True
        
        logger.info("VS Code client connected")
        
        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode())
                    await self._message_queue.put(message)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from VS Code")

        except Exception as e:
            logger.error(f"Client connection error: {e}")
        
        finally:
            self._connected = False
            writer.close()
            await writer.wait_closed()
            logger.info("VS Code client disconnected")

    async def _process_messages(self) -> None:
        """Process incoming messages."""
        while self._running:
            try:
                message = await self._message_queue.get()
                
                msg_type = MessageType(message.get("type", "notification"))
                method = message.get("method", "")
                
                if msg_type == MessageType.REQUEST:
                    # Handle request with response
                    handler = self._request_handlers.get(method)
                    if handler:
                        result = await handler(message.get("params", {}))
                        await self._send_response(
                            message["id"],
                            result=result
                        )
                    else:
                        await self._send_response(
                            message["id"],
                            error=f"Unknown method: {method}"
                        )
                
                elif msg_type == MessageType.NOTIFICATION:
                    # Handle notification
                    handler = self._handlers.get(method)
                    if handler:
                        await handler(message.get("params", {}))

            except Exception as e:
                logger.error(f"Message processing error: {e}")

    async def _send_response(
        self,
        msg_id: str,
        result: Any = None,
        error: str = None
    ) -> None:
        """Send response to client."""
        if not self._client_writer:
            return

        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result if not error else None,
            "error": {"message": error} if error else None
        }

        try:
            self._client_writer.write(
                (json.dumps(response) + "\n").encode()
            )
            await self._client_writer.drain()
        except Exception as e:
            logger.error(f"Failed to send response: {e}")

    def register_handler(self, method: str, handler: Callable) -> None:
        """Register notification handler."""
        self._handlers[method] = handler

    def register_request_handler(self, method: str, handler: Callable) -> None:
        """Register request handler (expects response)."""
        self._request_handlers[method] = handler

    async def send_notification(self, method: str, params: Dict = None) -> None:
        """Send notification to VS Code."""
        if not self._client_writer:
            return

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        try:
            self._client_writer.write(
                (json.dumps(message) + "\n").encode()
            )
            await self._client_writer.drain()
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def send_request(
        self,
        method: str,
        params: Dict = None,
        timeout: float = 30.0
    ) -> Optional[Any]:
        """Send request and wait for response."""
        if not self._client_writer:
            return None

        import uuid
        msg_id = str(uuid.uuid4())
        
        message = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {}
        }

        response_queue = asyncio.Queue()
        
        async def response_handler(msg):
            if msg.get("id") == msg_id:
                await response_queue.put(msg)

        # Register temporary handler
        handler = self.register_request_handler(f"_response_{msg_id}", response_handler)
        self._request_handlers[f"_response_{msg_id}"] = response_handler

        try:
            self._client_writer.write(
                (json.dumps(message) + "\n").encode()
            )
            await self._client_writer.drain()

            response = await asyncio.wait_for(
                response_queue.get(),
                timeout=timeout
            )

            if response.get("error"):
                logger.error(f"VS Code error: {response['error']}")
                return None

            return response.get("result")

        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {method}")
            return None
        finally:
            # Cleanup temporary handler
            self._request_handlers.pop(f"_response_{msg_id}", None)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # Convenience methods for common operations

    async def get_editor_context(self) -> EditorContext:
        """Get current editor context from VS Code."""
        context = EditorContext()
        
        try:
            # Get current file
            files = await self.send_request("jarvis.getOpenFiles")
            if files:
                context.open_files = files
            
            # Get current file content
            current = await self.send_request("jarvis.getCurrentFile")
            if current:
                context.current_file = current.get("path")
                context.current_file_content = current.get("content")
                context.language = current.get("language", "")
            
            # Get cursor position
            cursor = await self.send_request("jarvis.getCursorPosition")
            if cursor:
                context.cursor_position = (cursor.get("line", 0), cursor.get("column", 0))
            
            # Get selection
            selection = await self.send_request("jarvis.getSelection")
            if selection:
                context.selection = selection.get("text")
            
            # Get errors
            errors = await self.send_request("jarvis.getErrors")
            if errors:
                context.errors = errors
            
            # Get workspace root
            root = await self.send_request("jarvis.getWorkspaceRoot")
            context.workspace_root = root

        except Exception as e:
            logger.warning(f"Failed to get editor context: {e}")

        return context

    async def insert_text(self, text: str, position: dict = None) -> bool:
        """Insert text at cursor or position."""
        try:
            await self.send_notification("jarvis.insertText", {
                "text": text,
                "position": position
            })
            return True
        except Exception as e:
            logger.error(f"Failed to insert text: {e}")
            return False

    async def replace_selection(self, text: str) -> bool:
        """Replace current selection with text."""
        try:
            await self.send_notification("jarvis.replaceSelection", {
                "text": text
            })
            return True
        except Exception as e:
            logger.error(f"Failed to replace selection: {e}")
            return False

    async def run_command(self, command: str, args: List = None) -> bool:
        """Execute VS Code command."""
        try:
            await self.send_notification("jarvis.executeCommand", {
                "command": command,
                "args": args or []
            })
            return True
        except Exception as e:
            logger.error(f"Failed to run command: {e}")
            return False

    async def open_file(self, path: str) -> bool:
        """Open file in VS Code."""
        return await self.run_command("vscode.open", [path])

    async def show_message(self, message: str, type: str = "info") -> bool:
        """Show message in VS Code."""
        try:
            await self.send_notification("jarvis.showMessage", {
                "message": message,
                "type": type  # info, warning, error
            })
            return True
        except Exception as e:
            logger.error(f"Failed to show message: {e}")
            return False

    async def get_terminal_output(self) -> Optional[str]:
        """Get output from integrated terminal."""
        try:
            return await self.send_request("jarvis.getTerminalOutput")
        except Exception as e:
            logger.warning(f"Failed to get terminal output: {e}")
            return None

    async def run_in_terminal(self, command: str, cwd: str = None) -> bool:
        """Run command in VS Code integrated terminal."""
        try:
            await self.send_notification("jarvis.runInTerminal", {
                "command": command,
                "cwd": cwd
            })
            return True
        except Exception as e:
            logger.error(f"Failed to run in terminal: {e}")
            return False


class VSCodeCommands:
    """
    Command handlers for VS Code extension.
    These are called by the VS Code extension.
    """

    def __init__(self, jarvis):
        self.jarvis = jarvis

    async def handle_explain(self, params: Dict) -> str:
        """Handle /explain command."""
        code = params.get("code", "")
        if not code:
            return "No code provided"

        prompt = f"Explain this code:\n```\n{code}\n```"
        result = await self.jarvis.process_command(prompt)
        return result or "Could not explain code"

    async def handle_document(self, params: Dict) -> str:
        """Handle /document command."""
        code = params.get("code", "")
        language = params.get("language", "python")

        prompt = f"Add docstrings to this {language} code:\n```\n{code}\n```"
        result = await self.jarvis.process_command(prompt)
        return result or "Could not document code"

    async def handle_test(self, params: Dict) -> str:
        """Handle /test command."""
        code = params.get("code", "")
        language = params.get("language", "python")

        prompt = f"Write unit tests for this {language} code:\n```\n{code}\n```"
        result = await self.jarvis.process_command(prompt)
        return result or "Could not generate tests"

    async def handle_refactor(self, params: Dict) -> str:
        """Handle /refactor command."""
        code = params.get("code", "")
        instruction = params.get("instruction", "improve this code")

        prompt = f"{instruction}:\n```\n{code}\n```"
        result = await self.jarvis.process_command(prompt)
        return result or "Could not refactor code"

    async def handle_find_bug(self, params: Dict) -> str:
        """Handle /find_bug command."""
        code = params.get("code", "")

        prompt = f"Find potential bugs in this code:\n```\n{code}\n```"
        result = await self.jarvis.process_command(prompt)
        return result or "Could not analyze code"

    async def handle_search(self, params: Dict) -> Dict:
        """Handle /search command."""
        query = params.get("query", "")
        
        # Search in knowledge base
        results = await self.jarvis.knowledge_base.search(query)
        
        return {
            "results": [
                {"content": r.get("content", ""), "source": r.get("source", "")}
                for r in results[:5]
            ]
        }
