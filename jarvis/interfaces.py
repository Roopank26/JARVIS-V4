"""
JARVIS shared interfaces, protocols, dataclasses, and singletons.

This module centralizes:
- Structural ``Protocol`` interfaces for every major JARVIS subsystem
- Shared dataclasses / DTOs
- Thin wrapper implementations that satisfy the protocols
- Module-level singleton accessors
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Protocols
# ──────────────────────────────────────────────────────────────────────────────


@runtime_checkable
class IEventBus(Protocol):
    """Protocol for event bus implementations."""

    def subscribe(
        self,
        event_type: Any,
        handler: Callable[[Any], None],
    ) -> Callable[[], None]: ...

    def unsubscribe(self, event_type: Any, handler: Callable[[Any], None]) -> None: ...

    def emit(self, event_type: Any, data: dict[str, Any] | None = None) -> Any: ...

    def history(self, event_type: Any | None = None) -> list[Any]: ...

    def clear_history(self) -> None: ...


@runtime_checkable
class IProvider(Protocol):
    """Protocol for AI provider implementations."""

    @property
    def is_available(self) -> bool: ...

    @property
    def last_error(self) -> str | None: ...

    @property
    def available_models(self) -> list[str]: ...

    @property
    def model(self) -> str: ...

    async def initialize(self) -> bool: ...

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> Any: ...

    async def list_models(self) -> list[str]: ...

    async def health_check(self) -> bool: ...


@runtime_checkable
class ILifecycleComponent(Protocol):
    """Protocol for lifecycle-managed components."""

    @property
    def name(self) -> str: ...

    @property
    def state(self) -> Any: ...

    @property
    def is_running(self) -> bool: ...

    @property
    def error(self) -> Exception | None: ...

    async def start(self) -> bool: ...

    async def stop(self) -> bool: ...

    async def restart(self) -> bool: ...


@runtime_checkable
class IAgent(Protocol):
    """Protocol for agent implementations."""

    @property
    def name(self) -> str: ...

    @property
    def agent_id(self) -> str: ...

    @property
    def agent_type(self) -> Any: ...

    def is_running(self) -> bool: ...

    async def initialize(self) -> None: ...

    async def process(self, input_data: Any) -> Any: ...


@runtime_checkable
class ITool(Protocol):
    """Protocol for tool implementations."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def category(self) -> str: ...

    @property
    def parameters(self) -> dict[str, Any]: ...

    @property
    def is_read_only(self) -> bool: ...

    @property
    def is_dangerous(self) -> bool: ...

    def get_permission_level(self) -> Any: ...

    def check_permission(self, input_data: dict[str, Any]) -> Any: ...

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]: ...

    def format_for_display(self, input_data: dict[str, Any]) -> str: ...

    async def execute(
        self,
        input_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any: ...

    def format_result(self, result: Any) -> str: ...


@runtime_checkable
class IMemory(Protocol):
    """Protocol for memory implementations."""

    def remember(self, key: str, value: Any, category: str = "general") -> None: ...

    def recall(self, query: str) -> list[Any]: ...

    def forget(self, key: str, category: str = "general") -> bool: ...

    def format_for_prompt(self) -> str: ...

    def clear(self) -> None: ...


@runtime_checkable
class IPlugin(Protocol):
    """Protocol for plugin implementations."""

    @property
    def plugin_id(self) -> str: ...

    @property
    def plugin_name(self) -> str: ...

    @property
    def plugin_version(self) -> str: ...

    @property
    def plugin_description(self) -> str: ...

    @property
    def plugin_author(self) -> str: ...

    @property
    def config(self) -> dict[str, Any]: ...

    @property
    def enabled(self) -> bool: ...

    async def initialize(self, jarvis_instance: Any) -> bool: ...

    async def execute(self, context: dict[str, Any]) -> Any: ...

    async def shutdown(self) -> None: ...

    def get_health(self) -> str: ...


@runtime_checkable
class IVoiceEngine(Protocol):
    """Protocol for voice engine implementations."""

    @property
    def name(self) -> str: ...

    @property
    def is_running(self) -> bool: ...

    @property
    def is_listening(self) -> bool: ...

    @property
    def is_speaking(self) -> bool: ...

    async def start(self) -> bool: ...

    async def stop(self) -> None: ...

    async def listen(self) -> str | None: ...

    async def speak(self, text: str) -> None: ...

    def set_speak_callback(self, callback: Callable[[str], None]) -> None: ...

    def request_interrupt(self) -> None: ...

    def clear_interrupt(self) -> None: ...


@runtime_checkable
class IDirector(Protocol):
    """Protocol for director implementations."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]: ...

    def can_handle(self, task: str) -> bool: ...


@runtime_checkable
class IResearchProvider(Protocol):
    """Protocol for research providers."""

    @property
    def name(self) -> str: ...

    async def search(self, query: str, num_results: int = 10) -> list[Any]: ...

    async def get_content(self, url: str) -> str: ...


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────


class PermissionLevel(Enum):
    """Permission levels for tool execution."""

    AUTOMATIC = "automatic"
    ASK_ONCE = "ask_once"
    ASK_ALWAYS = "ask_always"
    DENY = "deny"


# ──────────────────────────────────────────────────────────────────────────────
# Dataclasses / DTOs
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolResult:
    """Result of tool execution."""

    success: bool
    output: Any
    error: str | None = None

    def __str__(self) -> str:
        if self.success:
            return str(self.output)
        return f"Error: {self.error}"


@dataclass(frozen=True)
class GenerationResult:
    """Result from text generation."""

    text: str
    model: str
    provider: str
    tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    """Standardized LLM response."""

    content: str
    provider: Any
    model: str
    usage: dict[str, int] | None = None
    latency: float = 0.0
    error: str | None = None


@dataclass(frozen=True)
class ProviderStatus:
    """Detailed provider status."""

    name: str
    provider: Any
    available: bool
    current_model: str
    available_models: list[str] = field(default_factory=list)
    fallback: str | None = None
    connection: str = "Unknown"
    latency_ms: float = 0.0
    error: str | None = None
    last_check: str | None = None


@dataclass(frozen=True)
class Source:
    """A research source."""

    title: str
    url: str
    content: str = ""
    author: str = ""
    publisher: str = ""
    published_date: str = ""
    accessed_date: str = ""
    source_type: str = "web"
    relevance_score: float = 0.0


@dataclass(frozen=True)
class Task:
    """A unit of work assigned to a specialized agent."""

    id: str
    description: str
    type: Any
    status: str = "pending"
    priority: int = 1
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    """Inter-agent communication message."""

    sender: str
    receiver: str
    content: Any
    message_type: str = "message"
    reply_to: str | None = None


@dataclass(frozen=True)
class PluginInfo:
    """Plugin metadata."""

    id: str
    name: str
    version: str
    description: str
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    min_jarvis_version: str = "1.0.0"
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoiceConfig:
    """Voice system configuration."""

    wake_words: list[str] = field(default_factory=lambda: ["jarvis", "computer", "hey jarvis"])
    wake_sensitivity: float = 0.5
    wake_audio_threshold: float = 0.5
    stt_model: str = "base"
    stt_language: str = "en"
    stt_use_gpu: bool = False
    tts_voice: str = "en_US-lessac-medium"
    tts_model: str = "medium"
    tts_rate: float = 1.0
    tts_pitch: float = 1.0
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    silence_threshold: float = 500.0
    silence_duration: float = 1.5
    interrupt_on_speech: bool = True
    continuous_listening: bool = True
    stream_audio: bool = True
    conversation_timeout: float = 30.0
    energy_threshold: float = 0.01
    pause_threshold: float = 0.8


@dataclass(frozen=True)
class Capabilities:
    """System capabilities snapshot."""

    providers: list[dict[str, Any]] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    system: dict[str, Any] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    plugins: list[str] = field(default_factory=list)
    network: dict[str, Any] = field(default_factory=dict)
    filesystem: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LifecycleEvent:
    """Lifecycle event data."""

    state: Any
    component: str
    error: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a provider."""

    name: str
    priority: int = 0
    base_url: str | None = None
    api_key: str | None = None
    models: list[str] = field(default_factory=list)
    default_model: str | None = None
    timeout: float = 60.0
    max_retries: int = 3


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for LLM providers."""

    provider: str = "groq"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 60.0
    stream: bool = True


@dataclass(frozen=True)
class ModelInfo:
    """Information about an AI model."""

    name: str
    provider: str
    size: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    supports_streaming: bool = True
    is_reasoning: bool = False
    recommended_for: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProductionResearchResult:
    """Result from production research query."""

    query: str
    findings: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    summary: str = ""
    citations: list[str] = field(default_factory=list)
    conflicting_info: list[dict[str, str]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Wrapper implementations
# ──────────────────────────────────────────────────────────────────────────────


class WrapperEventBus:
    """Adapter wrapping an object to satisfy IEventBus."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def subscribe(
        self,
        event_type: Any,
        handler: Callable[[Any], None],
    ) -> Callable[[], None]:
        return self._inner.subscribe(event_type, handler)

    def unsubscribe(self, event_type: Any, handler: Callable[[Any], None]) -> None:
        self._inner.unsubscribe(event_type, handler)

    def emit(self, event_type: Any, data: dict[str, Any] | None = None) -> Any:
        return self._inner.emit(event_type, data)

    def history(self, event_type: Any | None = None) -> list[Any]:
        return self._inner.history(event_type)

    def clear_history(self) -> None:
        self._inner.clear_history()


class WrapperProvider:
    """Adapter wrapping an object to satisfy IProvider."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def is_available(self) -> bool:
        return self._inner.is_available

    @property
    def last_error(self) -> str | None:
        return self._inner.last_error

    @property
    def available_models(self) -> list[str]:
        return self._inner.available_models

    @property
    def model(self) -> str:
        return self._inner.model

    async def initialize(self) -> bool:
        return await self._inner.initialize()

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return await self._inner.generate(prompt, model, **kwargs)

    async def list_models(self) -> list[str]:
        return await self._inner.list_models()

    async def health_check(self) -> bool:
        return await self._inner.health_check()


class WrapperLifecycleComponent:
    """Adapter wrapping an object to satisfy ILifecycleComponent."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def state(self) -> Any:
        return self._inner.state

    @property
    def is_running(self) -> bool:
        return self._inner.is_running

    @property
    def error(self) -> Exception | None:
        return self._inner.error

    async def start(self) -> bool:
        return await self._inner.start()

    async def stop(self) -> bool:
        return await self._inner.stop()

    async def restart(self) -> bool:
        return await self._inner.restart()


class WrapperAgent:
    """Adapter wrapping an object to satisfy IAgent."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def agent_id(self) -> str:
        return self._inner.agent_id

    @property
    def agent_type(self) -> Any:
        return self._inner.agent_type

    def is_running(self) -> bool:
        return self._inner.is_running()

    async def initialize(self) -> None:
        await self._inner.initialize()

    async def process(self, input_data: Any) -> Any:
        return await self._inner.process(input_data)


class WrapperTool:
    """Adapter wrapping an object to satisfy ITool."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def description(self) -> str:
        return self._inner.description

    @property
    def category(self) -> str:
        return self._inner.category

    @property
    def parameters(self) -> dict[str, Any]:
        return self._inner.parameters

    @property
    def is_read_only(self) -> bool:
        return self._inner.is_read_only

    @property
    def is_dangerous(self) -> bool:
        return self._inner.is_dangerous

    def get_permission_level(self) -> Any:
        return self._inner.get_permission_level()

    def check_permission(self, input_data: dict[str, Any]) -> Any:
        return self._inner.check_permission(input_data)

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        return self._inner.validate_input(input_data)

    def format_for_display(self, input_data: dict[str, Any]) -> str:
        return self._inner.format_for_display(input_data)

    async def execute(
        self,
        input_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        return await self._inner.execute(input_data, context)

    def format_result(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        return str(result)


class WrapperMemory:
    """Adapter wrapping an object to satisfy IMemory."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def remember(self, key: str, value: Any, category: str = "general") -> None:
        self._inner.remember(key, value, category)

    def recall(self, query: str) -> list[Any]:
        return self._inner.recall(query)

    def forget(self, key: str, category: str = "general") -> bool:
        return self._inner.forget(key, category)

    def format_for_prompt(self) -> str:
        return self._inner.format_for_prompt()

    def clear(self) -> None:
        self._inner.clear()


class WrapperPlugin:
    """Adapter wrapping an object to satisfy IPlugin."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def plugin_id(self) -> str:
        return self._inner.plugin_id

    @property
    def plugin_name(self) -> str:
        return self._inner.plugin_name

    @property
    def plugin_version(self) -> str:
        return self._inner.plugin_version

    @property
    def plugin_description(self) -> str:
        return self._inner.plugin_description

    @property
    def plugin_author(self) -> str:
        return self._inner.plugin_author

    @property
    def config(self) -> dict[str, Any]:
        return self._inner.config

    @property
    def enabled(self) -> bool:
        return self._inner.enabled

    async def initialize(self, jarvis_instance: Any) -> bool:
        return await self._inner.initialize(jarvis_instance)

    async def execute(self, context: dict[str, Any]) -> Any:
        return await self._inner.execute(context)

    async def shutdown(self) -> None:
        await self._inner.shutdown()

    def get_health(self) -> str:
        return self._inner.get_health()


class WrapperVoiceEngine:
    """Adapter wrapping an object to satisfy IVoiceEngine."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def is_running(self) -> bool:
        return self._inner.is_running

    @property
    def is_listening(self) -> bool:
        return self._inner.is_listening

    @property
    def is_speaking(self) -> bool:
        return self._inner.is_speaking

    async def start(self) -> bool:
        return await self._inner.start()

    async def stop(self) -> None:
        await self._inner.stop()

    async def listen(self) -> str | None:
        return await self._inner.listen()

    async def speak(self, text: str) -> None:
        await self._inner.speak(text)

    def set_speak_callback(self, callback: Callable[[str], None]) -> None:
        self._inner.set_speak_callback(callback)

    def request_interrupt(self) -> None:
        self._inner.request_interrupt()

    def clear_interrupt(self) -> None:
        self._inner.clear_interrupt()


class WrapperDirector:
    """Adapter wrapping an object to satisfy IDirector."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def description(self) -> str:
        return self._inner.description

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return await self._inner.execute(task, context)

    def can_handle(self, task: str) -> bool:
        return self._inner.can_handle(task)


class WrapperResearchProvider:
    """Adapter wrapping an object to satisfy IResearchProvider."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    async def search(self, query: str, num_results: int = 10) -> list[Any]:
        return await self._inner.search(query, num_results)

    async def get_content(self, url: str) -> str:
        return await self._inner.get_content(url)


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton helpers
# ──────────────────────────────────────────────────────────────────────────────


def get_event_bus() -> Any:
    """Get (or create) the process-wide event bus."""
    from jarvis.events import get_event_bus as _get

    return _get()


def reset_event_bus() -> None:
    """Reset the global event bus (used by tests)."""
    from jarvis.events import reset_event_bus as _reset

    _reset()


def get_provider_manager() -> Any:
    """Get (or create) the process-wide provider manager."""
    from jarvis.api.providers import get_provider_manager as _get

    return _get()


def reset_provider_manager() -> None:
    """Reset the global provider manager."""
    global _provider_manager_singleton
    _provider_manager_singleton = None
    try:
        import jarvis.api.providers as providers

        providers._provider_manager = None
    except ImportError:
        pass


def get_memory_manager() -> Any:
    """Get (or create) the process-wide memory manager."""
    from jarvis.memory.memory_manager import get_memory_manager as _get

    return _get()


def reset_memory_manager() -> None:
    """Reset the global memory manager."""
    global _memory_manager_singleton
    _memory_manager_singleton = None
    try:
        import jarvis.memory.memory_manager as memory_manager

        memory_manager._memory_manager = None
    except ImportError:
        pass


def get_agent_coordinator() -> Any:
    """Get (or create) the process-wide agent coordinator."""
    from jarvis.agents.multi_agent import get_orchestrator as _get

    return _get()


def reset_agent_coordinator() -> None:
    """Reset the global agent coordinator."""
    global _agent_coordinator_singleton
    _agent_coordinator_singleton = None
    try:
        import jarvis.agents.multi_agent as multi_agent

        multi_agent._orchestrator = None
    except ImportError:
        pass


def get_plugin_manager() -> Any:
    """Get (or create) the process-wide plugin manager."""
    from jarvis.plugins.plugin_manager import get_plugin_manager as _get

    return _get()


def reset_plugin_manager() -> None:
    """Reset the global plugin manager."""
    global _plugin_manager_singleton
    _plugin_manager_singleton = None
    try:
        import jarvis.plugins.plugin_manager as plugin_manager

        plugin_manager._plugin_manager = None
    except ImportError:
        pass


def get_voice_runtime() -> Any:
    """Get (or create) the process-wide voice runtime."""
    from jarvis.voice.voice_runtime import get_voice_runtime as _get

    return _get()


def reset_voice_runtime() -> None:
    """Reset the global voice runtime."""
    global _voice_runtime_singleton
    _voice_runtime_singleton = None
    try:
        import jarvis.voice.voice_runtime as voice_runtime

        voice_runtime._voice_runtime_instance = None
    except ImportError:
        pass


__all__ = [
    # Protocols
    "IEventBus",
    "IProvider",
    "ILifecycleComponent",
    "IAgent",
    "ITool",
    "IMemory",
    "IPlugin",
    "IVoiceEngine",
    "IDirector",
    "IResearchProvider",
    # Enums
    "PermissionLevel",
    # Dataclasses
    "ToolResult",
    "GenerationResult",
    "LLMResponse",
    "ProviderStatus",
    "Source",
    "ProductionResearchResult",
    "Task",
    "Message",
    "PluginInfo",
    "VoiceConfig",
    "Capabilities",
    "LifecycleEvent",
    "ProviderConfig",
    "LLMConfig",
    "ModelInfo",
    # Wrappers
    "WrapperEventBus",
    "WrapperProvider",
    "WrapperLifecycleComponent",
    "WrapperAgent",
    "WrapperTool",
    "WrapperMemory",
    "WrapperPlugin",
    "WrapperVoiceEngine",
    "WrapperDirector",
    "WrapperResearchProvider",
    # Singletons
    "get_event_bus",
    "reset_event_bus",
    "get_provider_manager",
    "reset_provider_manager",
    "get_memory_manager",
    "reset_memory_manager",
    "get_agent_coordinator",
    "reset_agent_coordinator",
    "get_plugin_manager",
    "reset_plugin_manager",
    "get_voice_runtime",
    "reset_voice_runtime",
]
