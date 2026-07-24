"""
Human Approval Layer for JARVIS.

Before performing sensitive actions, request confirmation:
- Deleting files
- Sending emails
- Executing shell commands
- Changing system settings
- Financial operations

Support configurable permission policies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from jarvis.security.privacy import AuditLog, AuditRecord

logger = logging.getLogger(__name__)


class ApprovalPolicy(StrEnum):
    ALWAYS = "always"
    NEVER = "never"
    POLICY_BASED = "policy_based"
    HIGH_RISK = "high_risk"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    request_id: str
    action: str
    target: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    requested_by: str = "system"
    requested_at: float = field(default_factory=time.time)
    status: str = "pending"
    response: str | None = None
    responded_at: float | None = None


class ApprovalLayer:
    """
    Approval gate for sensitive actions.
    """

    def __init__(self, policy: ApprovalPolicy = ApprovalPolicy.HIGH_RISK, audit: AuditLog | None = None) -> None:
        self._policy = policy
        self._audit = audit or AuditLog()
        self._requests: dict[str, ApprovalRequest] = {}
        self._high_risk_actions: set[str] = {
            "delete_file", "delete_project", "send_email", "send_message",
            "execute_shell", "change_settings", "financial_transfer",
            "install_software", "modify_registry", "remove_plugin",
        }
        self._medium_risk_actions: set[str] = {
            "launch_app", "open_url", "modify_file", "run_tests",
            "run_linter", "update_dependencies",
        }

    def should_approve(self, action: str, target: str, details: dict[str, Any] | None = None) -> ApprovalRequest | None:
        if self._policy == ApprovalPolicy.NEVER:
            return None
        risk = self._assess_risk(action, target, details)
        if self._policy == ApprovalPolicy.ALWAYS or risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            request = ApprovalRequest(
                request_id=generate_id(),
                action=action,
                target=target,
                risk_level=risk,
                reason=self._risk_reason(action, risk),
                details=details or {},
            )
            self._requests[request.request_id] = request
            self._audit.record(AuditRecord(
                actor="system",
                action=f"approval_request:{action}",
                target=target,
                result="pending",
                details={"request_id": request.request_id, "risk": risk.value},
            ))
            return request
        return None

    def approve(self, request_id: str, response: str = "approved") -> bool:
        request = self._requests.get(request_id)
        if request is None:
            return False
        request.status = "approved"
        request.response = response
        request.responded_at = time.time()
        self._audit.record(AuditRecord(
            actor="human",
            action=f"approval_response:{request.action}",
            target=request.target,
            result="approved",
            details={"request_id": request_id, "response": response},
        ))
        return True

    def deny(self, request_id: str, reason: str = "") -> bool:
        request = self._requests.get(request_id)
        if request is None:
            return False
        request.status = "denied"
        request.response = reason or "denied"
        request.responded_at = time.time()
        self._audit.record(AuditRecord(
            actor="human",
            action=f"approval_response:{request.action}",
            target=request.target,
            result="denied",
            details={"request_id": request_id, "reason": reason},
        ))
        return True

    def get_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == "pending"]

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def set_policy(self, policy: ApprovalPolicy) -> None:
        self._policy = policy

    def add_high_risk_action(self, action: str) -> None:
        self._high_risk_actions.add(action)

    def _assess_risk(self, action: str, target: str, details: dict[str, Any] | None) -> RiskLevel:
        if action in self._high_risk_actions:
            return RiskLevel.HIGH
        if action in self._medium_risk_actions:
            return RiskLevel.MEDIUM
        details_str = str(details or {}).lower()
        if any(k in details_str for k in ["delete", "remove", "drop", "erase", "destroy"]):
            return RiskLevel.HIGH
        if any(k in details_str for k in ["financial", "money", "transfer", "payment"]):
            return RiskLevel.CRITICAL
        return RiskLevel.LOW

    def _risk_reason(self, action: str, risk: RiskLevel) -> str:
        reasons = {
            RiskLevel.CRITICAL: "This action could have irreversible or significant consequences. Approval required.",
            RiskLevel.HIGH: "This action modifies system state significantly. Approval required.",
            RiskLevel.MEDIUM: "This action interacts with the system. Approval recommended.",
            RiskLevel.LOW: "This action is low-risk.",
        }
        return reasons.get(risk, "Unknown risk.")

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": True,
            "policy": self._policy.value,
            "pending_requests": len(self.get_pending()),
        }


_approval_layer: ApprovalLayer | None = None


def get_approval_layer() -> ApprovalLayer:
    global _approval_layer
    if _approval_layer is None:
        _approval_layer = ApprovalLayer()
    return _approval_layer


def reset_approval_layer() -> None:
    global _approval_layer
    _approval_layer = None


def generate_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]
