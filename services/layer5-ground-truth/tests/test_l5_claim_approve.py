"""Behavior tests for the L5 ``claim.approve`` authorization guard."""

from __future__ import annotations

import logging
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from layer5_ground_truth.models.value_evidence_graph_enums import (
    ClaimStatus,
    ClaimType,
    Confidence,
)

pytestmark = pytest.mark.asyncio


ASSET_STEM = {
    "account_id": str(uuid.uuid4()),
    "statement": "Increase deal close rate by 15%",
    "claim_type": ClaimType.REVENUE_GROWTH.value,
    "value_unit": "USD",
    "conservative_value": "100000",
    "expected_value": "250000",
    "aggressive_value": "500000",
    "confidence": Confidence.HIGH.value,
}


async def _create_claim(
    client: AsyncClient,
    status: ClaimStatus = ClaimStatus.MODELED,
    *,
    actor: str = "author",
    **overrides: Any,
) -> str:
    """Create a claim with JSON-safe values and return its serialized ID."""
    payload = {**ASSET_STEM, "status": status.value, **overrides}
    response = await client.post(
        "/api/v1/value-claims",
        json=payload,
        headers={"X-Test-Actor": actor},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _inject_facts(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> None:
    """Inject authoritative server-side facts without adding request fields."""
    facts = {
        "author_id": "author",
        "validation_complete": True,
        "has_open_dispute": False,
        "impact_amount": 250_000.0,
        "approval_ceiling": 1_000_000.0,
        "revision": "1",
        "per_claim_binding": False,
        "review_pool_binding": True,
        "same_tenant": True,
    }
    facts.update(overrides)

    async def resolve(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "attributes": {
                key: facts[key]
                for key in (
                    "author_id",
                    "validation_complete",
                    "has_open_dispute",
                    "impact_amount",
                    "approval_ceiling",
                    "revision",
                )
            },
            "relationships": {
                key: facts[key]
                for key in (
                    "per_claim_binding",
                    "review_pool_binding",
                    "same_tenant",
                )
            },
        }

    monkeypatch.setattr(
        "layer5_ground_truth.api.value_claim_routes.resolve_claim_approval_facts",
        resolve,
    )


async def _approve(client: AsyncClient, claim_id: str, *, actor: str = "approver"):
    return await client.post(
        f"/api/v1/value-claims/{claim_id}/status",
        json={"status": ClaimStatus.APPROVED.value},
        headers={"X-Test-Actor": actor},
    )


async def test_l5_claim_approve_success(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch)
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == ClaimStatus.APPROVED.value


async def test_l5_claim_approve_self_approval_denied(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch, author_id="approver")
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "SELF_APPROVAL_FORBIDDEN"


async def test_l5_claim_approve_missing_relationship_denied(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(
        monkeypatch,
        per_claim_binding=False,
        review_pool_binding=False,
    )
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "RELATIONSHIP_MISSING"


async def test_l5_claim_approve_ceiling_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch, impact_amount=5_000_000.0)
    claim_id = await _create_claim(
        tenant_aware_client,
        expected_value="5000000",
        aggressive_value="6000000",
    )

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "APPROVAL_CEILING_EXCEEDED"


async def test_l5_claim_approve_open_dispute_denied(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch, has_open_dispute=True)
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "DISPUTE_OPEN"


async def test_l5_claim_approve_validation_incomplete_denied(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch, validation_complete=False)
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "VALIDATION_INCOMPLETE"


async def test_l5_claim_approve_tenant_mismatch_is_not_enumerable(
    tenant_aware_client: AsyncClient,
) -> None:
    claim_id = await _create_claim(tenant_aware_client)

    response = await tenant_aware_client.post(
        f"/api/v1/value-claims/{claim_id}/status",
        json={"status": ClaimStatus.APPROVED.value},
        headers={
            "X-Test-Actor": "approver",
            "X-Test-Tenant": "00000000-0000-0000-0000-000000000002",
        },
    )

    assert response.status_code == 404, response.text


async def test_l5_claim_approve_agent_forbidden(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch)
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id, actor="agent:planner")

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "AGENT_ACTION_FORBIDDEN"


async def test_l5_claim_approve_invalid_transition_400(
    tenant_aware_client: AsyncClient,
) -> None:
    claim_id = await _create_claim(tenant_aware_client, ClaimStatus.DRAFT)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "CLAIM_VALIDATION_ERROR"


async def test_build_principal_preserves_absent_identity_as_none() -> None:
    from layer5_ground_truth.api.authz_enforcement import build_principal

    principal = await build_principal(
        SimpleNamespace(tenant_id=None, user_id=None, roles=[]),
        db=None,
    )

    assert principal.tenant_id is None
    assert principal.user_id is None
    assert principal.bound_tenant_ids == frozenset()


async def test_l5_claim_approve_revision_mismatch_denied(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch, revision="2")
    claim_id = await _create_claim(tenant_aware_client)

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "RESOURCE_REVISION_CHANGED"


async def test_l5_claim_approve_pdp_outage_503(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
) -> None:
    _inject_facts(monkeypatch)
    claim_id = await _create_claim(tenant_aware_client)

    async def unavailable_guard(**_kwargs: Any) -> None:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "authorization_unavailable"},
        )

    monkeypatch.setattr(
        "layer5_ground_truth.api.value_claim_routes.guard_protected_command",
        unavailable_guard,
    )

    response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 503, response.text


async def test_l5_claim_approve_audit_correlation_logs_action(
    monkeypatch: pytest.MonkeyPatch,
    tenant_aware_client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _inject_facts(monkeypatch)
    claim_id = await _create_claim(tenant_aware_client)

    with caplog.at_level(
        logging.INFO,
        logger="layer5_ground_truth.api.authz_enforcement",
    ):
        response = await _approve(tenant_aware_client, claim_id)

    assert response.status_code == 200, response.text
    assert "action=claim.approve" in caplog.text


async def test_l5_claim_approve_not_found(
    tenant_aware_client: AsyncClient,
) -> None:
    response = await _approve(tenant_aware_client, str(uuid.uuid4()))

    assert response.status_code == 404, response.text


async def test_resolve_claim_approval_facts_accepts_no_overrides() -> None:
    from layer5_ground_truth.api.authz_enforcement import resolve_claim_approval_facts

    claim = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status=ClaimStatus.MODELED.value,
        created_by_user_id="author",
        expected_value="250000",
        version=1,
    )
    caller = SimpleNamespace(user_id="approver", tenant_id=claim.tenant_id)

    facts = await resolve_claim_approval_facts(claim, caller, db=None)

    assert facts["attributes"]["validation_complete"] is True
    assert facts["relationships"]["review_pool_binding"] is True


async def test_test_approval_ceiling_is_disabled_outside_test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from layer5_ground_truth.api.authz_enforcement import _resolve_approval_ceiling

    class UnavailableDatabase:
        async def execute(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("unavailable")

    monkeypatch.setenv("ENVIRONMENT", "production")
    caller = SimpleNamespace(user_id="approver", tenant_id=uuid.uuid4())

    assert await _resolve_approval_ceiling(caller, UnavailableDatabase()) is None
