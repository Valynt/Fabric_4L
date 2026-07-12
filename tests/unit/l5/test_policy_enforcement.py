"""Unit tests for Layer 5 policy enforcement (P0-004)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from layer5_ground_truth.services.policy_enforcement import (
    ArtifactAccessRequest,
    ArtifactStatus,
    enforce_formula_benchmark_runtime_policy,
)
from value_fabric.shared.error_handling.exceptions import AuthorizationError

pytestmark = [pytest.mark.unit]


def _make_request(
    *,
    scopes: set[str] = {"formula:read"},
    required: str = "formula:read",
    status: ArtifactStatus = ArtifactStatus.APPROVED,
) -> ArtifactAccessRequest:
    return ArtifactAccessRequest(
        tenant_id=uuid4(),
        actor_id="user-1",
        request_id="req-1",
        policy_id="policy-1",
        artifact_id="art-1",
        artifact_kind="formula",
        artifact_status=status,
        actor_scopes=scopes,
        required_scope=required,
    )


class TestPolicyEnforcement:
    """Runtime policy enforcement for formula and benchmark artifacts."""

    def test_allows_approved_artifact_with_scope(self) -> None:
        req = _make_request()
        enforce_formula_benchmark_runtime_policy(req)  # should not raise

    def test_rejects_missing_scope(self) -> None:
        req = _make_request(scopes={"other:read"})
        with pytest.raises(AuthorizationError) as exc_info:
            enforce_formula_benchmark_runtime_policy(req)
        assert "Insufficient permission" in str(exc_info.value)

    def test_rejects_draft_status(self) -> None:
        req = _make_request(status=ArtifactStatus.DRAFT)
        with pytest.raises(AuthorizationError) as exc_info:
            enforce_formula_benchmark_runtime_policy(req)
        assert "must be approved" in str(exc_info.value)

    def test_rejects_deprecated_status(self) -> None:
        req = _make_request(status=ArtifactStatus.DEPRECATED)
        with pytest.raises(AuthorizationError) as exc_info:
            enforce_formula_benchmark_runtime_policy(req)
        assert "must be approved" in str(exc_info.value)

    def test_rejects_archived_status(self) -> None:
        req = _make_request(status=ArtifactStatus.ARCHIVED)
        with pytest.raises(AuthorizationError) as exc_info:
            enforce_formula_benchmark_runtime_policy(req)
        assert "must be approved" in str(exc_info.value)

    def test_rejects_published_status(self) -> None:
        """Published is not in approved set — only APPROVED passes."""
        req = _make_request(status=ArtifactStatus.PUBLISHED)
        with pytest.raises(AuthorizationError) as exc_info:
            enforce_formula_benchmark_runtime_policy(req)
        assert "must be approved" in str(exc_info.value)

    def test_exact_match_scope_required(self) -> None:
        req = _make_request(scopes={"formula:read", "formula:write"}, required="formula:write")
        enforce_formula_benchmark_runtime_policy(req)

    def test_empty_scopes_rejected(self) -> None:
        req = _make_request(scopes=set())
        with pytest.raises(AuthorizationError):
            enforce_formula_benchmark_runtime_policy(req)

    def test_request_fields_preserved(self) -> None:
        req = _make_request()
        assert req.tenant_id is not None
        assert req.actor_id == "user-1"
        assert req.artifact_kind == "formula"
