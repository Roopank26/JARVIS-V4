"""
JARVIS Desktop UI
Modern dark-themed desktop interface.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("jarvis.ui.desktop")


@dataclass
class UITheme:
    """UI theme configuration."""
    name: str = "dark"
    background: str = "#1a1a2e"
    surface: str = "#16213e"
    primary: str = "#0f3460"
    accent: str = "#e94560"
    text: str = "#eaeaea"
    text_secondary: str = "#a0a0a0"
    success: str = "#4ade80"
    warning: str = "#fbbf24"
    error: str = "#ef4444"


@dataclass
class ConversationMessage:
    """A conversation message."""
    role: str  # user, assistant, system
    content: str
    timestamp: str | None = None
    metadata: dict[str, Any] | None = None


class DesktopUI:
    """
    Modern desktop UI for JARVIS.
    
    Features:
    - Dark theme with JARVIS styling
    - Live conversation display
    - Voice waveform visualization
    - Memory browser
    - Model/provider selector
    - Plugin manager
    - System monitor
    - Notification center
    """
    
    def __init__(self, theme: UITheme | None = None):
        self.theme = theme or UITheme()
        self._running = False
        self._messages: list[ConversationMessage] = []
        self._listeners: dict[str, list[Callable]] = {}
        
        # UI State
        self._current_model = "qwen3"
        self._current_provider = "ollama"
        self._is_speaking = False
        self._is_listening = False
        self._is_interrupted = False
        self._conversation_active = False
        self._cpu_usage = 0.0
        self._memory_usage = 0.0
    
    async def start(self) -> bool:
        """Start the UI."""
        logger.info("Starting desktop UI...")
        self._running = True
        return True
    
    async def stop(self) -> None:
        """Stop the UI."""
        logger.info("Stopping desktop UI...")
        self._running = False
    
    def add_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        """Add a message to the conversation."""
        from datetime import datetime
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().strftime("%H:%M"),
            metadata=metadata,
        )
        self._messages.append(message)
        self._emit("message", message)
    
    def get_conversation(self) -> list[ConversationMessage]:
        """Get the current conversation."""
        return self._messages.copy()
    
    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._messages.clear()
        self._emit("clear", None)
    
    def set_model(self, model: str) -> None:
        """Set the current model."""
        self._current_model = model
        self._emit("model_change", model)
    
    def set_provider(self, provider: str) -> None:
        """Set the current provider."""
        self._current_provider = provider
        self._emit("provider_change", provider)
    
    def set_speaking(self, speaking: bool) -> None:
        """Set speaking state."""
        self._is_speaking = speaking
        self._emit("speaking", speaking)
    
    def set_listening(self, listening: bool) -> None:
        """Set listening state."""
        self._is_listening = listening
        self._emit("listening", listening)
    
    def update_stats(self, cpu: float, memory: float) -> None:
        """Update system statistics."""
        self._cpu_usage = cpu
        self._memory_usage = memory
        self._emit("stats", {"cpu": cpu, "memory": memory})
    
    def on(self, event: str, callback: Callable) -> None:
        """Register an event listener."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def _emit(self, event: str, data: Any) -> None:
        """Emit an event."""
        for callback in self._listeners.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    def get_html(self) -> str:
        """Get the UI as HTML (for web-based rendering)."""
        messages_html = ""
        for msg in self._messages[-50:]:  # Last 50 messages
            role_class = "user" if msg.role == "user" else "assistant"
            messages_html += f"""
                <div class="message {role_class}">
                    <div class="message-content">{self._escape_html(msg.content)}</div>
                    <div class="message-time">{msg.timestamp or ''}</div>
                </div>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: {self.theme.background};
            color: {self.theme.text};
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: {self.theme.surface};
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            border-bottom: 1px solid {self.theme.primary};
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: {self.theme.accent};
        }}
        .status {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .indicator {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: {self.theme.success};
        }}
        .indicator.listening {{ animation: pulse 1s infinite; background: {self.theme.accent}; }}
        .indicator.speaking {{ animation: pulse 0.5s infinite; background: {self.theme.success}; }}
        @keyframes pulse {{ 
            0%, 100% {{ opacity: 1; }} 
            50% {{ opacity: 0.5; }} 
        }}
        .main {{
            flex: 1;
            display: flex;
            overflow: hidden;
        }}
        .sidebar {{
            width: 250px;
            background: {self.theme.surface};
            padding: 15px;
            border-right: 1px solid {self.theme.primary};
        }}
        .sidebar-section {{
            margin-bottom: 20px;
        }}
        .sidebar-title {{
            font-size: 12px;
            text-transform: uppercase;
            color: {self.theme.text_secondary};
            margin-bottom: 8px;
        }}
        .conversation {{
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 20px;
            overflow-y: auto;
        }}
        .message {{
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 80%;
        }}
        .message.user {{
            background: {self.theme.primary};
            margin-left: auto;
        }}
        .message.assistant {{
            background: {self.theme.surface};
            border: 1px solid {self.theme.primary};
        }}
        .message-content {{
            line-height: 1.5;
        }}
        .message-time {{
            font-size: 11px;
            color: {self.theme.text_secondary};
            margin-top: 5px;
        }}
        .input-area {{
            padding: 15px 20px;
            background: {self.theme.surface};
            border-top: 1px solid {self.theme.primary};
        }}
        .input-row {{
            display: flex;
            gap: 10px;
        }}
        .input-field {{
            flex: 1;
            padding: 12px 16px;
            background: {self.theme.background};
            border: 1px solid {self.theme.primary};
            border-radius: 8px;
            color: {self.theme.text};
            font-size: 14px;
        }}
        .btn {{
            padding: 12px 24px;
            background: {self.theme.accent};
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .stats {{
            font-size: 12px;
            color: {self.theme.text_secondary};
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">JARVIS</div>
        <div class="status">
            <div class="indicator {'listening' if self._is_listening else ''}"></div>
            <span>{'Listening' if self._is_listening else 'Idle'}</span>
        </div>
        <div class="status">
            <span>Model: {self._current_model}</span>
        </div>
        <div class="status">
            <span>Provider: {self._current_provider}</span>
        </div>
        <div class="stats">
            CPU: {self._cpu_usage:.1f}% | Memory: {self._memory_usage:.1f}%
        </div>
    </div>
    <div class="main">
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-title">Model</div>
                <div>{self._current_model}</div>
            </div>
            <div class="sidebar-section">
                <div class="sidebar-title">Provider</div>
                <div>{self._current_provider}</div>
            </div>
            <div class="sidebar-section">
                <div class="sidebar-title">Memory</div>
                <div>{len(self._messages)} messages</div>
            </div>
        </div>
        <div class="conversation">
            {messages_html}
        </div>
    </div>
    <div class="input-area">
        <div class="input-row">
            <input type="text" class="input-field" placeholder="Ask JARVIS..." />
            <button class="btn">Send</button>
        </div>
    </div>
</body>
</html>
        """
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
    
    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    @property
    def is_interrupted(self) -> bool:
        return getattr(self, '_is_interrupted', False)

    @property
    def conversation_active(self) -> bool:
        return getattr(self, '_conversation_active', False)

    def set_interrupted(self, interrupted: bool) -> None:
        """Set interrupted state."""
        self._is_interrupted = interrupted
        self._emit("interrupted", interrupted)

    def set_conversation_active(self, active: bool) -> None:
        """Set conversation mode state."""
        self._conversation_active = active
        self._emit("conversation_active", active)

    def get_voice_status(self) -> dict[str, Any]:
        """Get current voice status for UI."""
        return {
            "is_speaking": self._is_speaking,
            "is_listening": self._is_listening,
            "is_interrupted": getattr(self, '_is_interrupted', False),
            "conversation_active": getattr(self, '_conversation_active', False),
            "state": self._get_voice_state_label(),
        }

    def _get_voice_state_label(self) -> str:
        if getattr(self, '_is_interrupted', False):
            return "Interrupted"
        if self._is_speaking:
            return "Speaking"
        if self._is_listening:
            return "Listening"
        if getattr(self, '_conversation_active', False):
            return "Conversation Active"
        return "Idle"

    def get_status(self) -> dict[str, Any]:
        """Get UI status."""
        status = {
            "running": self._running,
            "theme": self.theme.name,
            "current_model": self._current_model,
            "current_provider": self._current_provider,
            "is_speaking": self._is_speaking,
            "is_listening": self._is_listening,
            "message_count": len(self._messages),
        }
        status.update(self.get_voice_status())
        return status


# Console UI fallback
class ConsoleUI:
    """Simple console-based UI."""
    
    def __init__(self):
        self._running = False
    
    async def start(self) -> bool:
        self._running = True
        print("=" * 50)
        print("  JARVIS - Just A Rather Very Intelligent System")
        print("=" * 50)
        return True
    
    async def stop(self) -> None:
        self._running = False
    
    def add_message(self, role: str, content: str) -> None:
        prefix = "You" if role == "user" else "JARVIS"
        print(f"\n[{prefix}]")
        print(content)
    
    def get_status(self) -> dict[str, Any]:
        return {"running": self._running, "type": "console"}
