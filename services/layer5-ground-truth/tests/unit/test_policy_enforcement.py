from uuid import uuid4

import pytest
from fastapi import HTTPException

from layer5_ground_truth.services.policy_enforcement import (
    ArtifactAccessRequest,
    ArtifactStatus,
    enforce_formula_benchmark_runtime_policy,
)


def _req(**overrides):
    return ArtifactAccessRequest(
        tenant_id=uuid4(),
        actor_id="actor-1",
        request_id="req-1",
        policy_id="policy-l5-runtime-artifact",
        artifact_id="formula-1",
        artifact_kind="formula",
        artifact_status=ArtifactStatus.APPROVED,
        actor_scopes={"layer5.artifacts.resolve"},
        required_scope="layer5.artifacts.resolve",
        **overrides,
    )


def test_policy_allows_approved_artifact_with_required_scope(monkeypatch):
    seen = {}

    def _emit(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(
        "layer5_ground_truth.services.policy_enforcement.emit_audit_event", _emit
    )

    enforce_formula_benchmark_runtime_policy(_req())

    assert seen["details"]["decision"] == "allow"
    assert seen["details"]["policy_id"] == "policy-l5-runtime-artifact"


@pytest.mark.parametrize("status", [ArtifactStatus.DRAFT, ArtifactStatus.DEPRECATED, ArtifactStatus.ARCHIVED])
def test_policy_denies_unpublished_deprecated_archived(status, monkeypatch):
    seen = {}

    def _emit(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(
        "layer5_ground_truth.services.policy_enforcement.emit_audit_event", _emit
    )

    with pytest.raises(HTTPException):
        enforce_formula_benchmark_runtime_policy(_req(artifact_status=status))

    assert seen["details"]["decision"] == "deny"
    assert seen["details"]["artifact_status"] == status.value


def test_policy_denies_missing_scope(monkeypatch):
    seen = {}

    def _emit(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(
        "layer5_ground_truth.services.policy_enforcement.emit_audit_event", _emit
    )

    with pytest.raises(HTTPException):
        enforce_formula_benchmark_runtime_policy(_req(actor_scopes=set()))

    assert seen["details"]["reason"] == "missing_scope"
