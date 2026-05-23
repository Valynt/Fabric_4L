from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from layer5_ground_truth.api.auth import TokenClaims
from layer5_ground_truth.api.router import TruthObjectCreate, create_truth, delete_truth

TEST_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def make_truth_payload(**overrides) -> dict:
    payload = {
        "claim": "Manual invoice reconciliation costs 20 hours per month",
        "claim_type": "efficiency_gain",
        "confidence": 0.85,
        "value": {"amount": 20, "unit": "hours", "period": "month"},
        "applies_to": {"opportunity_id": "opp-test-001"},
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_truth_create_rejected_without_scope() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await create_truth(
            request=None,
            payload=TruthObjectCreate(**make_truth_payload()),
            caller=TokenClaims(tenant_id=TEST_ORG_ID, user_id="viewer", roles=["read_only"]),
            db=None,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "INSUFFICIENT_SCOPE"


@pytest.mark.asyncio
async def test_truth_create_allowed_with_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    truth_id = uuid.uuid4()
    truth_obj = SimpleNamespace(
        id=truth_id,
        tenant_id=TEST_ORG_ID,
        claim=make_truth_payload()["claim"],
        claim_type=make_truth_payload()["claim_type"],
        value=make_truth_payload()["value"],
        confidence=make_truth_payload()["confidence"],
        status="proposed",
        maturity_level=1,
        validated_by=None,
        validated_at=None,
        validation_notes=None,
        rejected_by=None,
        rejected_at=None,
        rejection_reason=None,
        superseded_by_id=None,
        superseded_at=None,
        freshness=now,
        expires_at=None,
        is_stale=False,
        applies_to=make_truth_payload()["applies_to"],
        dispute_reason=None,
        dispute_notes=None,
        disputed_by=None,
        disputed_at=None,
        kg_node_id=None,
        kg_synced_at=None,
        extraction_job_id=None,
        extraction_model=None,
        created_at=now,
        updated_at=now,
        sources=[],
        validation_events=[],
        maturity_history=[],
    )
    async def _create_truth_object(**kwargs):
        return truth_obj
    async def _get_truth_object(*args, **kwargs):
        return truth_obj
    monkeypatch.setattr("layer5_ground_truth.api.router.create_truth_object", _create_truth_object)
    monkeypatch.setattr("layer5_ground_truth.api.router.get_truth_object", _get_truth_object)

    created = await create_truth(
        request=None,
        payload=TruthObjectCreate(**make_truth_payload()),
        caller=TokenClaims(tenant_id=TEST_ORG_ID, user_id="editor", roles=["content_admin"]),
        db=None,
    )

    assert created.claim == make_truth_payload()["claim"]


@pytest.mark.asyncio
async def test_cross_tenant_delete_with_insufficient_scope_is_deterministically_forbidden() -> None:
    other_tenant = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await delete_truth(
            uuid.uuid4(),
            caller=TokenClaims(tenant_id=other_tenant, user_id="viewer", roles=["read_only"]),
            db=None,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "INSUFFICIENT_SCOPE"
