"""
JARVIS Phase 3 — Security: Privacy utilities.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    actor: str
    action: str
    target: str
    result: str = "allowed"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AuditLog:
    """Append-only audit log."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".jarvis" / "audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, record: AuditRecord) -> None:
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "actor": record.actor,
                    "action": record.action,
                    "target": record.target,
                    "result": record.result,
                    "details": record.details,
                    "timestamp": record.timestamp,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        if not self.path.exists():
            return entries
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
                    if len(entries) >= limit:
                        break
        except Exception:
            pass
        return entries


class SensitiveDataMasker:
    """Mask sensitive data in logs and outputs."""

    _patterns = [
        "api_key", "apikey", "token", "password", "secret", "credential",
        "Authorization", "Bearer ", "sk-", "key=",
    ]

    @classmethod
    def mask(cls, text: str) -> str:
        lowered = text.lower()
        for pattern in cls._patterns:
            if pattern.lower() in lowered:
                return "[REDACTED]"
        if len(text) > 200 and any(k in lowered for k in ["key", "token", "secret"]):
            return "[REDACTED]"
        return text


class PermissionChecker:
    """Permission-based tool access control."""

    def __init__(self) -> None:
        self._allowed_tools: dict[str, list[str]] = {}
        self._default_deny = False

    def allow(self, actor: str, tools: list[str]) -> None:
        self._allowed_tools.setdefault(actor, []).extend(tools)

    def deny(self, actor: str, tools: list[str]) -> None:
        current = self._allowed_tools.get(actor, [])
        self._allowed_tools[actor] = [t for t in current if t not in tools]

    def can(self, actor: str, tool: str) -> bool:
        if actor not in self._allowed_tools:
            return not self._default_deny
        return tool in self._allowed_tools[actor]


class EncryptedStore:
    """Simple encrypted local store for credentials."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".jarvis" / "encrypted_store.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = self._derive_key()

    def _derive_key(self) -> bytes:
        salt = b"jarvis-local-salt"
        return hashlib.pbkdf2_hmac("sha256", salt, salt, 100000, dklen=32)

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def save(self, key: str, value: str) -> None:
        try:
            raw = json.dumps({"k": key, "v": value}).encode("utf-8")
            encrypted = self._xor_encrypt(raw, self._key)
            existing: dict[str, Any] = {}
            if self.path.exists():
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
            existing[key] = encrypted.hex()
            self.path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def load(self, key: str) -> str | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            encrypted = bytes.fromhex(raw.get(key, ""))
            if not encrypted:
                return None
            decrypted = self._xor_encrypt(encrypted, self._key)
            data = json.loads(decrypted.decode("utf-8"))
            return data.get("v")
        except Exception:
            return None

    def delete(self, key: str) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            raw.pop(key, None)
            self.path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
