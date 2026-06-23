"""API route tests for ValueClaim endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from layer5_ground_truth.models.value_evidence_graph_enums import (
    ClaimStatus,
    ClaimType,
    Confidence,
)


@pytest.mark.asyncio
async def test_create_value_claim(client: AsyncClient):
    account_id = uuid.uuid4()
    payload = {
        "account_id": str(account_id),
        "statement": "Reduce onboarding time by 20%",
        "claim_type": ClaimType.PRODUCTIVITY_GAIN.value,
        "value_unit": "USD/year",
        "conservative_value": "100000",
        "expected_value": "250000",
        "aggressive_value": "500000",
        "confidence": Confidence.HIGH.value,
    }
    response = await client.post("/api/v1/value-claims", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["statement"] == payload["statement"]
    assert data["status"] == ClaimStatus.DRAFT.value
    assert data["tenant_id"] == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_create_value_claim_rejects_invalid_value_order(
    client: AsyncClient,
):
    account_id = uuid.uuid4()
    payload = {
        "account_id": str(account_id),
        "statement": "x",
        "claim_type": ClaimType.COST_SAVINGS.value,
        "value_unit": "USD",
        "conservative_value": "300",
        "expected_value": "200",
        "aggressive_value": "100",
        "confidence": Confidence.LOW.value,
    }
    response = await client.post("/api/v1/value-claims", json=payload)
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error"]["code"] == "CLAIM_VALIDATION_ERROR"
    assert body["error"]["details"]["domain_code"] == "VALUE_NOT_ORDERED"


@pytest.mark.asyncio
async def test_list_value_claims(client: AsyncClient):
    account_id = uuid.uuid4()
    base = {
        "account_id": str(account_id),
        "claim_type": ClaimType.COST_SAVINGS.value,
        "value_unit": "USD",
        "conservative_value": "1",
        "expected_value": "2",
        "aggressive_value": "3",
        "confidence": Confidence.LOW.value,
    }
    await client.post(
        "/api/v1/value-claims",
        json={**base, "statement": "draft claim", "status": ClaimStatus.DRAFT.value},
    )
    await client.post(
        "/api/v1/value-claims",
        json={
            **base,
            "statement": "supported claim",
            "status": ClaimStatus.SUPPORTED.value,
        },
    )

    response = await client.get(
        f"/api/v1/value-claims?account_id={account_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2

    filtered = await client.get(
        f"/api/v1/value-claims?account_id={account_id}&status={ClaimStatus.SUPPORTED.value}"
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_value_claim(client: AsyncClient):
    account_id = uuid.uuid4()
    payload = {
        "account_id": str(account_id),
        "statement": "Get me",
        "claim_type": ClaimType.REVENUE_GROWTH.value,
        "value_unit": "USD",
        "conservative_value": "1",
        "expected_value": "2",
        "aggressive_value": "3",
        "confidence": Confidence.MEDIUM.value,
    }
    create_resp = await client.post("/api/v1/value-claims", json=payload)
    claim_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/value-claims/{claim_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == claim_id


@pytest.mark.asyncio
async def test_get_value_claim_404_for_other_tenant(
    tenant_aware_client: AsyncClient,
):
    account_id = uuid.uuid4()
    payload = {
        "account_id": str(account_id),
        "statement": "Tenant isolation",
        "claim_type": ClaimType.COST_SAVINGS.value,
        "value_unit": "USD",
        "conservative_value": "1",
        "expected_value": "2",
        "aggressive_value": "3",
        "confidence": Confidence.LOW.value,
    }
    create_resp = await tenant_aware_client.post(
        "/api/v1/value-claims", json=payload
    )
    claim_id = create_resp.json()["id"]

    other_tenant = uuid.uuid4()
    response = await tenant_aware_client.get(
        f"/api/v1/value-claims/{claim_id}",
        headers={"X-Test-Tenant": str(other_tenant)},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transition_value_claim_status(client: AsyncClient):
    account_id = uuid.uuid4()
    payload = {
        "account_id": str(account_id),
        "statement": "Transition me",
        "claim_type": ClaimType.CYCLE_TIME_REDUCTION.value,
        "value_unit": "hours",
        "conservative_value": "10",
        "expected_value": "20",
        "aggressive_value": "30",
        "confidence": Confidence.MEDIUM.value,
    }
    create_resp = await client.post("/api/v1/value-claims", json=payload)
    claim_id = create_resp.json()["id"]

    transition = await client.post(
        f"/api/v1/value-claims/{claim_id}/status",
        json={"status": ClaimStatus.SUPPORTED.value},
    )
    assert transition.status_code == 200
    assert transition.json()["status"] == ClaimStatus.SUPPORTED.value

    invalid = await client.post(
        f"/api/v1/value-claims/{claim_id}/status",
        json={"status": ClaimStatus.VALIDATED.value},
    )
    assert invalid.status_code == 400
    body = invalid.json()
    assert body["error"]["code"] == "CLAIM_VALIDATION_ERROR"
    assert body["error"]["details"]["domain_code"] == "INVALID_TRANSITION"
