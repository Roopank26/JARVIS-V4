"""
JARVIS Exception Classes
Custom exceptions for clear error handling and debugging.
"""

from typing import Any


class JarvisError(Exception):
    """Base exception for JARVIS."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(JarvisError):
    """Configuration-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)


class ProviderError(JarvisError):
    """AI provider errors (Groq, Ollama, etc.)."""

    def __init__(self, message: str, provider: str | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.provider = provider


class ProviderNotAvailableError(ProviderError):
    """Provider is not available."""

    def __init__(self, provider: str, **kwargs):
        super().__init__(
            f"Provider '{provider}' is not available",
            provider=provider,
            **kwargs,
        )
        self.provider = provider


class ModelError(ProviderError):
    """Model-related errors."""

    def __init__(self, message: str, model: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.model = model


class ModelNotFoundError(ModelError):
    """Model not found."""

    def __init__(self, model: str, **kwargs):
        super().__init__(
            f"Model '{model}' not found",
            model=model,
            **kwargs,
        )
        self.model = model


class VoiceError(JarvisError):
    """Voice system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)


class MicrophoneError(VoiceError):
    """Microphone-related errors."""

    def __init__(self, message: str = "Microphone not available", **kwargs):
        super().__init__(message, **kwargs)


class SpeakerError(VoiceError):
    """Speaker/audio output errors."""

    def __init__(self, message: str = "Speaker not available", **kwargs):
        super().__init__(message, **kwargs)


class WakeWordError(JarvisError):
    """Wake word detection errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)


class MemoryError(JarvisError):
    """Memory system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)


class RAGError(JarvisError):
    """RAG system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)


class DocumentError(RAGError):
    """Document processing errors."""

    def __init__(self, message: str, document: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.document = document


class DesktopError(JarvisError):
    """Desktop automation errors."""

    def __init__(self, message: str, recoverable: bool = True, **kwargs):
        super().__init__(message, recoverable=recoverable, **kwargs)


class ToolError(JarvisError):
    """Tool execution errors."""

    def __init__(self, message: str, tool: str | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.tool = tool


class TaskError(JarvisError):
    """Task execution errors."""

    def __init__(self, message: str, task_id: str | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.task_id = task_id


class SecurityError(JarvisError):
    """Security-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            recoverable=False,
            **kwargs,
        )


class PermissionError(SecurityError):
    """Permission denied errors."""

    def __init__(self, message: str, operation: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.operation = operation


class AuthenticationError(SecurityError):
    """Authentication errors."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)


class ValidationError(JarvisError):
    """Input validation errors."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.field = field


class TimeoutError(JarvisError):
    """Operation timeout errors."""

    def __init__(self, message: str, timeout: float | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.timeout = timeout


class ResourceError(JarvisError):
    """Resource-related errors (memory, CPU, etc.)."""

    def __init__(self, message: str, resource: str | None = None, **kwargs):
        super().__init__(message, recoverable=True, **kwargs)
        self.resource = resource


def format_exception(exc: Exception) -> str:
    """
    Format an exception for user-friendly display.

    Args:
        exc: Exception to format

    Returns:
        User-friendly error message
    """
    if isinstance(exc, JarvisError):
        return exc.message

    # Handle common exceptions
    exc_name = type(exc).__name__

    if "Connection" in exc_name or "Timeout" in exc_name:
        return f"Connection error: {exc}"

    if "Permission" in exc_name or "Access" in exc_name:
        return f"Permission denied: {exc}"

    if "NotFound" in exc_name or "File" in exc_name:
        return f"Resource not found: {exc}"

    # Default formatting
    return f"{exc_name}: {exc}"


def get_recovery_suggestion(error: JarvisError) -> str | None:
    """
    Get a recovery suggestion for an error.

    Args:
        error: The error

    Returns:
        Suggestion string or None
    """
    suggestions = {
        ProviderNotAvailableError: "Check your internet connection or try a different provider.",
        MicrophoneError: "Ensure your microphone is connected and accessible.",
        SpeakerError: "Check your audio output settings.",
        TimeoutError: "Try again with a smaller request or check your connection.",
        MemoryError: "Try clearing some memory or restart JARVIS.",
        AuthenticationError: "Check your API credentials in the configuration.",
    }

    for error_type, suggestion in suggestions.items():
        if isinstance(error, error_type):
            return suggestion

    return None
