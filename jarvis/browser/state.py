"""Persistent browser state persistence."""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any


class BrowserState:
    """Manages persistent browser daemon state on disk."""

    def __init__(self, storage_path: Path, state_file: str = "state.json"):
        self.storage_path = storage_path
        self.state_file = state_file
        self.state_path = storage_path / state_file
        self.state: dict[str, Any] = {}
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        if self.state_path.exists():
            try:
                self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.state = {}

    def load(self) -> dict[str, Any]:
        return dict(self.state)

    def save(self) -> None:
        tmp_path = self.state_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(self.state, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        import os

        os.replace(str(tmp_path), str(self.state_path))
        with suppress(OSError):
            os.chmod(str(self.state_path), 0o600)

    def update(self, **kwargs: Any) -> None:
        self.state.update(kwargs)
        self.save()

    def clear(self) -> None:
        self.state = {}
        if self.state_path.exists():
            self.state_path.unlink(missing_ok=True)
