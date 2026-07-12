"""Hostile tests for Layer 5 runtime artifact policy bypass attempts."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from layer5_ground_truth.services.policy_enforcement import (
    ArtifactAccessRequest,
    ArtifactStatus,
    enforce_formula_benchmark_runtime_policy,
)
from value_fabric.shared.error_handling.exceptions import AuthorizationError


@pytest.mark.security
@pytest.mark.tenant_boundary
def test_hostile_attempt_with_scope_but_not_approved_is_denied(monkeypatch):
    emitted = {}

    def _emit(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(
        "layer5_ground_truth.services.policy_enforcement.emit_audit_event", _emit
    )

    req = ArtifactAccessRequest(
        tenant_id=uuid4(),
        actor_id="attacker",
        request_id="req-hostile-1",
        policy_id="policy-l5-runtime-artifact",
        artifact_id="benchmark-777",
        artifact_kind="benchmark",
        artifact_status=ArtifactStatus.DRAFT,
        actor_scopes={"layer5.artifacts.resolve"},
        required_scope="layer5.artifacts.resolve",
    )

    with pytest.raises((HTTPException, AuthorizationError)):
        enforce_formula_benchmark_runtime_policy(req)

    assert emitted["outcome"] == "denied"
    assert emitted["details"]["decision"] == "deny"


@pytest.mark.security
@pytest.mark.tenant_boundary
def test_hostile_attempt_without_scope_is_denied_and_audited(monkeypatch):
    emitted = {}

    def _emit(**kwargs):
        emitted.update(kwargs)

    monkeypatch.setattr(
        "layer5_ground_truth.services.policy_enforcement.emit_audit_event", _emit
    )

    req = ArtifactAccessRequest(
        tenant_id=uuid4(),
        actor_id="attacker",
        request_id="req-hostile-2",
        policy_id="policy-l5-runtime-artifact",
        artifact_id="formula-abc",
        artifact_kind="formula",
        artifact_status=ArtifactStatus.APPROVED,
        actor_scopes=set(),
        required_scope="layer5.artifacts.resolve",
    )

    with pytest.raises((HTTPException, AuthorizationError)):
        enforce_formula_benchmark_runtime_policy(req)

    assert emitted["details"]["reason"] == "missing_scope"
    assert emitted["request_id"] == "req-hostile-2"
