"""
JARVIS Logging Module
Production-ready logging with structured output, rotation, and multiple handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class JarvisLogger:
    """
    Centralized logging for JARVIS with structured output and multiple handlers.
    """
    
    _instance: Optional["JarvisLogger"] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._loggers: dict[str, logging.Logger] = {}
        self._config = {
            "level": logging.INFO,
            "format": "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
        }
        self._root_logger: Optional[logging.Logger] = None
    
    def configure(
        self,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console: bool = True,
    ) -> None:
        """
        Configure logging settings.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            console: Whether to log to console
        """
        self._config["level"] = level
        
        # Create root logger
        root = logging.getLogger("jarvis")
        root.setLevel(level)
        root.handlers.clear()
        
        # Format
        fmt = logging.Formatter(
            self._config["format"],
            datefmt=self._config["date_format"],
        )
        
        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(fmt)
            root.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(fmt)
            root.addHandler(file_handler)
        
        self._root_logger = root
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific module.
        
        Args:
            name: Logger name (e.g., "jarvis.core.agent")
            
        Returns:
            Configured logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    def set_level(self, level: int) -> None:
        """Set logging level for all JARVIS loggers."""
        self._config["level"] = level
        if self._root_logger:
            self._root_logger.setLevel(level)
        for logger in self._loggers.values():
            logger.setLevel(level)
    
    @property
    def root_logger(self) -> logging.Logger:
        """Get the root JARVIS logger."""
        if not self._root_logger:
            self.configure()
        return self._root_logger or logging.getLogger("jarvis")


# Global logger instance
_logger_instance: Optional[JarvisLogger] = None


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        name: Module name (e.g., "agent", "voice.audio")
        
    Returns:
        Configured logger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = JarvisLogger()
        _logger_instance.configure()
    
    full_name = f"jarvis.{name}" if not name.startswith("jarvis") else name
    return _logger_instance.get_logger(full_name)


def configure_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    **kwargs,
) -> None:
    """
    Configure global logging.
    
    Args:
        level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        **kwargs: Additional configuration options
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = JarvisLogger()
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    _logger_instance.configure(
        level=level_map.get(level.upper(), logging.INFO),
        log_file=log_file,
        **kwargs,
    )


# Convenience function for easy import
def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    filename: str = "jarvis.log",
) -> None:
    """
    Setup logging with sensible defaults.
    
    Args:
        level: Log level
        log_dir: Directory for log files
        filename: Log filename
    """
    log_file = None
    if log_dir:
        log_file = log_dir / filename
    
    configure_logging(level=level, log_file=log_file)
