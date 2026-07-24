"""
Tests for JARVIS Phase 4 — Approval Layer.
"""


def test_approval_layer_singleton():
    from jarvis.security.approval import get_approval_layer, reset_approval_layer
    layer = get_approval_layer()
    assert layer is get_approval_layer()
    reset_approval_layer()


def test_approval_never_policy():
    from jarvis.security.approval import ApprovalLayer, ApprovalPolicy
    layer = ApprovalLayer(policy=ApprovalPolicy.NEVER)
    req = layer.should_approve("delete_file", "/tmp/test")
    assert req is None


def test_approval_always_policy():
    from jarvis.security.approval import ApprovalLayer, ApprovalPolicy
    layer = ApprovalLayer(policy=ApprovalPolicy.ALWAYS)
    req = layer.should_approve("open_app", "firefox")
    assert req is not None
    assert req.risk_level.value == "low"


def test_approval_high_risk_policy():
    from jarvis.security.approval import ApprovalLayer, ApprovalPolicy
    layer = ApprovalLayer(policy=ApprovalPolicy.HIGH_RISK)
    req = layer.should_approve("delete_file", "/tmp/test")
    assert req is not None
    layer.approve(req.request_id)
    assert req.status == "approved"


def test_approval_deny():
    from jarvis.security.approval import ApprovalLayer, ApprovalPolicy
    layer = ApprovalLayer(policy=ApprovalPolicy.ALWAYS)
    req = layer.should_approve("send_email", "test@example.com")
    assert req is not None
    layer.deny(req.request_id)
    assert req.status == "denied"
