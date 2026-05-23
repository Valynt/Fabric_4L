import uuid

import pytest

TEST_ORG_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def make_truth_payload():
    return {
        "claim": "Cross-tenant isolation test claim",
        "claim_type": "metric",
        "confidence": 0.95,
        "organization_id": str(TEST_ORG_ID),
    }


def make_source_payload():
    return {
        "url": "https://example.com/source",
        "source_type": "document",
        "excerpt": "Test excerpt for cross-tenant isolation",
    }


@pytest.mark.asyncio
async def test_truth_object_cross_tenant_read_write_denied(tenant_aware_client):
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create = await tenant_aware_client.post(
        "/api/v1/truths",
        json=make_truth_payload(),
        headers={"X-Test-Tenant": tenant_a},
    )
    assert create.status_code == 201
    truth_id = create.json()["id"]

    get_other = await tenant_aware_client.get(
        f"/api/v1/truths/{truth_id}",
        headers={"X-Test-Tenant": tenant_b},
    )
    assert get_other.status_code == 404

    mutate_other = await tenant_aware_client.post(
        f"/api/v1/truths/{truth_id}/sources",
        json=make_source_payload(),
        headers={"X-Test-Tenant": tenant_b},
    )
    assert mutate_other.status_code == 404


@pytest.mark.asyncio
async def test_model_registry_cross_tenant_read_write_denied(tenant_aware_client):
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())
    payload = {
        "name": "gpt-4o-mini",
        "provider": "openai",
        "version": "2025-01",
        "model_identifier": "gpt-4o-mini",
        "capabilities": ["json_mode"],
    }

    create = await tenant_aware_client.post(
        "/api/v1/models",
        json=payload,
        headers={"X-Test-Tenant": tenant_a},
    )
    assert create.status_code == 201
    model_id = create.json()["id"]

    get_other = await tenant_aware_client.get(
        f"/api/v1/models/{model_id}",
        headers={"X-Test-Tenant": tenant_b},
    )
    assert get_other.status_code == 404

    deprecate_other = await tenant_aware_client.post(
        f"/api/v1/models/{model_id}/deprecate",
        headers={"X-Test-Tenant": tenant_b},
    )
    assert deprecate_other.status_code == 404
