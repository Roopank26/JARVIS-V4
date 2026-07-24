"""
JARVIS Token Tracker

Tracks token usage across providers with SQLite persistence.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".jarvis" / "token_usage.db"


class TokenTracker:
    """Tracks token usage across providers."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    day TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_token_usage_provider_day
                ON token_usage (provider, day)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_token_usage_model_day
                ON token_usage (model, day)
                """
            )
            conn.commit()

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record token usage for a provider/model pair."""
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        total_tokens = input_tokens + output_tokens
        with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO token_usage (provider, model, input_tokens, output_tokens, total_tokens, day)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (provider, model, input_tokens, output_tokens, total_tokens, day),
                )
                conn.commit()
        logger.debug(
            "Token usage recorded: provider=%s model=%s input=%d output=%d total=%d day=%s",
            provider,
            model,
            input_tokens,
            output_tokens,
            total_tokens,
            day,
        )

    def get_stats(self, provider: str | None = None) -> dict[str, Any]:
        """Return aggregated token stats, optionally filtered by provider."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if provider:
                rows = conn.execute(
                    """
                    SELECT provider, model, SUM(input_tokens) as total_input, SUM(output_tokens) as total_output, SUM(total_tokens) as total_tokens, COUNT(*) as request_count
                    FROM token_usage
                    WHERE provider = ?
                    GROUP BY provider, model
                    """,
                    (provider,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT provider, SUM(input_tokens) as total_input, SUM(output_tokens) as total_output, SUM(total_tokens) as total_tokens, COUNT(*) as request_count
                    FROM token_usage
                    GROUP BY provider
                    """
                ).fetchall()

        result: dict[str, Any] = {"entries": []}
        total_input = 0
        total_output = 0
        total_requests = 0
        for row in rows:
            entry = dict(row)
            if provider:
                entry["provider"] = provider
            result["entries"].append(entry)
            total_input += entry.get("total_input", 0) or 0
            total_output += entry.get("total_output", 0) or 0
            total_requests += entry.get("request_count", 0) or 0
        result["total_input"] = total_input
        result["total_output"] = total_output
        result["total_tokens"] = total_input + total_output
        result["total_requests"] = total_requests
        return result

    def get_total_stats(self) -> dict[str, Any]:
        """Return total token usage stats across all providers."""
        return self.get_stats(provider=None)

    def persist(self) -> None:
        """Persist any in-memory state (SQLite is immediate, so this is a no-op)."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.commit()

    def load(self) -> None:
        """Load persisted data (no-op for SQLite-backed tracker)."""
        self._ensure_tables()


# Global singleton
_token_tracker: TokenTracker | None = None


def get_token_tracker() -> TokenTracker:
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker()
    return _token_tracker
