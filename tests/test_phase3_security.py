"""
Phase 3 Security Tests
"""

import tempfile
from pathlib import Path

from jarvis.security.encryption import (
    AuditLog,
    AuditRecord,
    EncryptedStore,
    PermissionChecker,
    SensitiveDataMasker,
)


def test_mask_sensitive_text():
    assert "[REDACTED]" in SensitiveDataMasker.mask("api_key = secret123")


def test_mask_clean_text():
    text = "Hello, how are you today?"
    assert SensitiveDataMasker.mask(text) == text


def test_permission_checker_allow():
    pc = PermissionChecker()
    pc.allow("user1", ["tool_a", "tool_b"])
    assert pc.can("user1", "tool_a") is True
    assert pc.can("user1", "tool_c") is False


def test_permission_checker_deny():
    pc = PermissionChecker()
    pc.allow("user1", ["tool_a"])
    pc.deny("user1", ["tool_a"])
    assert pc.can("user1", "tool_a") is False


def test_audit_log_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = AuditLog(Path(tmpdir) / "audit.jsonl")
        record = AuditRecord(actor="test", action="run", target="tool_x", result="allowed")
        log.record(record)
        entries = log.recent(limit=10)
        assert len(entries) == 1
        assert entries[0]["actor"] == "test"


def test_encrypted_store_save_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EncryptedStore(Path(tmpdir) / "store.json")
        store.save("cred", "my_secret_value")
        value = store.load("cred")
        assert value == "my_secret_value"


def test_encrypted_store_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EncryptedStore(Path(tmpdir) / "store.json")
        store.save("cred", "secret")
        store.delete("cred")
        assert store.load("cred") is None
