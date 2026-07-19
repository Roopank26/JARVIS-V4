"""
Comprehensive utilities for JARVIS.
"""

import logging as _logging
import platform
import re
import sys
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from jarvis.utils.diagnostics import (
    DiagnosticCheck,
    DiagnosticResult,
    DiagnosticsRunner,
    run_startup_diagnostics,
)
from jarvis.utils.exceptions import (
    ConfigurationError,
    DesktopError,
    JarvisError,
    MemoryError,
    PermissionError,
    ProviderError,
    RAGError,
    SecurityError,
    ToolError,
    ValidationError,
    VoiceError,
    format_exception,
)
from jarvis.utils.lifecycle import (
    LifecycleComponent,
    LifecycleManager,
    LifecycleState,
    StartupDiagnostics,
    lifespan_context,
)

# Import new utilities
from jarvis.utils.logging import configure_logging, get_logger, setup_logging

__all__ = [
    # Platform utilities
    "get_platform",
    "is_linux",
    "is_macos",
    "is_windows",
    "get_home_dir",
    "get_jarvis_dir",
    "get_memory_path",
    "ensure_jarvis_dir",
    # String utilities
    "truncate_string",
    "format_path",
    # Logging
    "get_logger",
    "configure_logging",
    "setup_logging",
    # Time utilities
    "Timer",
    "format_duration",
    "format_size",
    # Cache
    "Cache",
    # Validation
    "Validator",
    # ID generation
    "generate_id",
    # File utilities
    "ensure_dir",
    "atomic_write",
    # Retry
    "retry",
    # Exceptions
    "JarvisError",
    "ConfigurationError",
    "ProviderError",
    "VoiceError",
    "MemoryError",
    "RAGError",
    "DesktopError",
    "ToolError",
    "SecurityError",
    "PermissionError",
    "ValidationError",
    "format_exception",
    # Lifecycle
    "LifecycleState",
    "LifecycleComponent",
    "LifecycleManager",
    "lifespan_context",
    "StartupDiagnostics",
    # Diagnostics
    "DiagnosticResult",
    "DiagnosticCheck",
    "DiagnosticsRunner",
    "run_startup_diagnostics",
]


# Platform utilities
def get_platform() -> str:
    """Get the current platform."""
    return platform.system().lower()


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_platform() == "darwin"


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform() == "windows"


# Path utilities
def get_home_dir() -> Path:
    """Get the user's home directory."""
    return Path.home()


def get_jarvis_dir() -> Path:
    """Get the JARVIS configuration directory."""
    return get_home_dir() / ".jarvis"


def get_memory_path() -> Path:
    """Get the memory storage path."""
    return get_jarvis_dir() / "memory" / "long_term.json"


def ensure_jarvis_dir() -> Path:
    """Ensure the JARVIS directory exists."""
    jarvis_dir = get_jarvis_dir()
    jarvis_dir.mkdir(parents=True, exist_ok=True)
    return jarvis_dir


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length."""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def format_path(path: str) -> str:
    """Format a path for display."""
    path_obj = Path(path).expanduser()
    try:
        return str(path_obj.resolve())
    except Exception:
        return str(path_obj)


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


# Logging utilities
class Logger:
    """Enhanced logger wrapper with colored output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def __init__(self, name: str, level: int = _logging.INFO):
        self.logger = _logging.getLogger(name)
        self.logger.setLevel(level)
        self._colored = sys.stderr.isatty()

        if not self.logger.handlers:
            handler = _logging.StreamHandler()
            handler.setFormatter(
                _logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
            )
            self.logger.addHandler(handler)

    def _colorize(self, level: str, msg: str) -> str:
        if self._colored and level in self.COLORS:
            return f"{self.COLORS[level]}{msg}{self.COLORS['RESET']}"
        return msg

    def debug(self, msg: str):
        self.logger.debug(self._colorize("DEBUG", msg))

    def info(self, msg: str):
        self.logger.info(self._colorize("INFO", msg))

    def warning(self, msg: str):
        self.logger.warning(self._colorize("WARNING", msg))

    def error(self, msg: str):
        self.logger.error(self._colorize("ERROR", msg))

    def critical(self, msg: str):
        self.logger.critical(self._colorize("CRITICAL", msg))


class Timer:
    """Context manager for timing operations."""

    def __init__(self, name: str = "Operation", callback: Callable | None = None):
        self.name = name
        self.callback = callback
        self.start_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, *args):
        self.duration = (datetime.now() - self.start_time).total_seconds()
        msg = f"{self.name}: {format_duration(self.duration)}"
        if self.callback:
            self.callback(self.duration, msg)
        else:
            print(msg)


class Cache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    return value
                del self._cache[key]
        return default

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl or self.default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        with self._lock:
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup(self) -> int:
        now = datetime.now()
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for k in expired:
                del self._cache[k]
            return len(expired)


class Validator:
    """Input validation utilities."""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        return bool(re.match(r"^https?://\S+$", url))

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        filename = re.sub(r'[<>:"\'|?*]', "_", filename)
        return filename[:255]

    @staticmethod
    def sanitize_command(command: str) -> str:
        return re.sub(r"[^a-zA-Z0-9 _\-./]", "", command)


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    uid = str(uuid.uuid4())
    return f"{prefix}{uid}" if prefix else uid


def format_size(bytes: int) -> str:
    """Format bytes as human-readable."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    return f"{hours}h {mins}m"


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write file atomically."""
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(content, encoding=encoding)
        temp.replace(path)
    except Exception:
        if temp.exists():
            temp.unlink()
        raise


@contextmanager
def retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Retry context manager."""
    for attempt in range(max_attempts):
        try:
            yield attempt
            return
        except exceptions:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay * (attempt + 1))
