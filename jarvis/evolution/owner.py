"""
JARVIS-V7 Evolution — Owner Model & Authority System.

Defines the permanent owner identity and administrative permissions.
No other user has administrator privileges unless explicitly authorized by the owner.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OWNER = "Roopank Battu"
DEFAULT_CONFIG_DIR = Path.home() / ".jarvis" / "evolution"
DEFAULT_OWNER_FILE = "owner.json"


class Permission(StrEnum):
    APPROVE_PROMOTION = "approve_promotion"
    DELETE_MEMORY = "delete_memory"
    MODIFY_LEARNING_RULES = "modify_learning_rules"
    CONTROL_AUTONOMOUS_BEHAVIOR = "control_autonomous_behavior"
    GRANT_REVOKE_PERMISSIONS = "grant_revoke_permissions"
    ENABLE_DISABLE_RESEARCH = "enable_disable_research"
    ENABLE_DISABLE_TRAINING = "enable_disable_training"
    EXPORT_ALL_KNOWLEDGE = "export_all_knowledge"
    ROLLBACK_MODEL = "rollback_model"
    RESTORE_CHECKPOINT = "restore_checkpoint"


ALL_PERMISSIONS = [p.value for p in Permission]


@dataclass
class AuthorizedUser:
    user_id: str
    name: str
    permissions: list[str] = field(default_factory=list)
    granted_by: str = DEFAULT_OWNER
    granted_at: float = field(default_factory=time.time)
    revoked_at: float | None = None

    def is_active(self) -> bool:
        return self.revoked_at is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "permissions": self.permissions,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at,
            "revoked_at": self.revoked_at,
        }


@dataclass
class OwnerRecord:
    name: str
    authority_level: str = "full_admin"
    permissions: list[str] = field(default_factory=lambda: list(ALL_PERMISSIONS))
    preferences: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "authority_level": self.authority_level,
            "permissions": self.permissions,
            "preferences": self.preferences,
            "created_at": self.created_at,
        }


class OwnerModel:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.config_dir / DEFAULT_OWNER_FILE
        self._owner: OwnerRecord | None = None
        self._authorized: dict[str, AuthorizedUser] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._owner = OwnerRecord(name=DEFAULT_OWNER)
            self._save()
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self._owner = OwnerRecord(**data.get("owner", {}))
            for u in data.get("authorized_users", []):
                user = AuthorizedUser(**u)
                self._authorized[user.user_id] = user
        except Exception as exc:
            logger.debug("Owner model load failed: %s", exc)
            self._owner = OwnerRecord(name=DEFAULT_OWNER)

    def _save(self) -> None:
        try:
            from jarvis.evolution import atomic_write_json
            atomic_write_json(
                self.path,
                {
                    "owner": self._owner.to_dict() if self._owner else OwnerRecord(name=DEFAULT_OWNER).to_dict(),
                    "authorized_users": [u.to_dict() for u in self._authorized.values()],
                },
            )
        except Exception:
            logger.debug("Owner model save failed", exc_info=True)

    def get_owner(self) -> OwnerRecord:
        return self._owner or OwnerRecord(name=DEFAULT_OWNER)

    def is_owner(self, user_id: str) -> bool:
        owner = self.get_owner()
        return user_id == owner.name or user_id == owner.name.lower().replace(" ", "_")

    def has_permission(self, user_id: str, permission: str | Permission) -> bool:
        if self.is_owner(user_id):
            return True
        user = self._authorized.get(user_id)
        if user and user.is_active():
            return permission.value if isinstance(permission, Permission) else permission in user.permissions
        return False

    def check_permission(self, user_id: str, permission: str | Permission) -> None:
        if not self.has_permission(user_id, permission):
            perm_str = permission.value if isinstance(permission, Permission) else permission
            raise PermissionError(f"User '{user_id}' does not have permission: {perm_str}")

    def grant_permission(self, grantor_id: str, target_user_id: str, permissions: list[str]) -> None:
        self.check_permission(grantor_id, Permission.GRANT_REVOKE_PERMISSIONS)
        user = self._authorized.get(target_user_id)
        if user is None:
            user = AuthorizedUser(
                user_id=target_user_id,
                name=target_user_id,
            )
            self._authorized[target_user_id] = user
        user.permissions = list(set(user.permissions + permissions))
        user.granted_by = grantor_id
        user.granted_at = time.time()
        user.revoked_at = None
        self._save()
        logger.info("Granted permissions %s to %s by %s", permissions, target_user_id, grantor_id)

    def revoke_permission(self, revoker_id: str, target_user_id: str) -> None:
        self.check_permission(revoker_id, Permission.GRANT_REVOKE_PERMISSIONS)
        user = self._authorized.get(target_user_id)
        if user:
            user.revoked_at = time.time()
            self._save()
            logger.info("Revoked permissions for %s by %s", target_user_id, revoker_id)

    def set_preference(self, key: str, value: Any) -> None:
        owner = self.get_owner()
        owner.preferences[key] = value
        self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        owner = self.get_owner()
        return owner.preferences.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.get_owner().to_dict(),
            "authorized_users": [u.to_dict() for u in self._authorized.values()],
        }


_owner_model_instance: OwnerModel | None = None


def get_owner_model() -> OwnerModel:
    global _owner_model_instance
    if _owner_model_instance is None:
        _owner_model_instance = OwnerModel()
    return _owner_model_instance


def reset_owner_model() -> None:
    global _owner_model_instance
    _owner_model_instance = None
