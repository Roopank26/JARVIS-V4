"""Persistent browser configuration for JARVIS."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BrowserConfig:
    """Configuration for the persistent browser manager."""

    headless: bool = True
    browser: str = "chromium"
    timeout: int = 30
    window_size: tuple[int, int] = (1920, 1080)
    idle_timeout: int = 1800
    storage_path: Path = field(default_factory=lambda: Path.home() / ".jarvis" / "browser")
    state_file: str = "state.json"
    user_data_dir: Path | None = None
