from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_ORG_ID, make_source_payload, make_truth_payload


@pytest.mark.asyncio
async def test_truth_object_cross_tenant_read_write_denied(tenant_aware_client: AsyncClient) -> None:
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
async def test_model_registry_cross_tenant_read_write_denied(tenant_aware_client: AsyncClient) -> None:
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


@pytest.mark.asyncio
async def test_truth_list_filter_cross_tenant_enumeration_blocked(tenant_aware_client: AsyncClient) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create = await tenant_aware_client.post("/api/v1/truths", json=make_truth_payload(), headers={"X-Test-Tenant": tenant_a})
    assert create.status_code == 201

    list_other = await tenant_aware_client.get("/api/v1/truths?limit=10&offset=0", headers={"X-Test-Tenant": tenant_b})
    assert list_other.status_code == 200
    assert list_other.json()["total"] == 0


@pytest.mark.asyncio
async def test_truth_state_transition_cross_tenant_denied(tenant_aware_client: AsyncClient) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create = await tenant_aware_client.post("/api/v1/truths", json=make_truth_payload(), headers={"X-Test-Tenant": tenant_a})
    assert create.status_code == 201
    truth_id = create.json()["id"]

    other_transition = await tenant_aware_client.post(
        f"/api/v1/truths/{truth_id}/validate",
        json={"action": "dispute", "actor": "attacker", "dispute_reason": "other"},
        headers={"X-Test-Tenant": tenant_b},
    )
    assert other_transition.status_code == 404


@pytest.mark.asyncio
async def test_truth_sync_cross_tenant_does_not_process_other_tenant_data(tenant_aware_client: AsyncClient) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create = await tenant_aware_client.post("/api/v1/truths", json=make_truth_payload(), headers={"X-Test-Tenant": tenant_a})
    assert create.status_code == 201

    sync_other = await tenant_aware_client.post("/api/v1/truths/sync-kg", headers={"X-Test-Tenant": tenant_b})
    assert sync_other.status_code == 200
    assert sync_other.json()["total_pending"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,method,body",
    [
        ("/api/v1/truths/{id}/audit", "get", None),
        ("/api/v1/truths/{id}", "delete", None),
        ("/api/v1/models/{id}/set-default", "post", None),
        ("/api/v1/models/{id}/promote", "post", {"environment": "staging"}),
        ("/api/v1/models/{id}/deployments", "get", None),
        ("/api/v1/models/{id}/evaluations", "get", None),
    ],
)
async def test_id_scoped_endpoints_cross_tenant_denied(
    tenant_aware_client: AsyncClient, endpoint: str, method: str, body: dict | None
) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create = await tenant_aware_client.post(
        "/api/v1/models",
        json={"name": "gpt-4o-mini", "provider": "openai", "version": "2025-01", "model_identifier": "gpt-4o-mini", "capabilities": ["json_mode"]},
        headers={"X-Test-Tenant": tenant_a},
    )
    assert create.status_code == 201
    model_id = create.json()["id"]

    create_truth = await tenant_aware_client.post("/api/v1/truths", json=make_truth_payload(), headers={"X-Test-Tenant": tenant_a})
    assert create_truth.status_code == 201
    truth_id = create_truth.json()["id"]

    target_id = truth_id if endpoint.startswith("/api/v1/truths") else model_id
    path = endpoint.format(id=target_id)
    fn = getattr(tenant_aware_client, method)
    resp = await fn(path, json=body, headers={"X-Test-Tenant": tenant_b}) if body else await fn(path, headers={"X-Test-Tenant": tenant_b})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_endpoints_cross_tenant_enumeration_blocked(tenant_aware_client: AsyncClient) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())

    create_model = await tenant_aware_client.post(
        "/api/v1/models",
        json={"name": "gpt-4o-mini", "provider": "openai", "version": "2025-01", "model_identifier": "gpt-4o-mini", "capabilities": ["json_mode"]},
        headers={"X-Test-Tenant": tenant_a},
    )
    assert create_model.status_code == 201
    model_id = create_model.json()["id"]

    create_eval = await tenant_aware_client.post(
        "/api/v1/evaluations",
        json={"model_version_id": model_id, "test_dataset": "tenant-test", "overall_score": 0.9},
        headers={"X-Test-Tenant": tenant_a},
    )
    assert create_eval.status_code == 201

    for endpoint in ("/api/v1/models", "/api/v1/deployments", "/api/v1/evaluations", "/api/v1/truths/stale", "/api/v1/truths/freshness-summary"):
        resp = await tenant_aware_client.get(endpoint, headers={"X-Test-Tenant": tenant_b})
        assert resp.status_code == 200

    assert (await tenant_aware_client.get("/api/v1/models", headers={"X-Test-Tenant": tenant_b})).json()["total"] == 0
    assert (await tenant_aware_client.get("/api/v1/evaluations", headers={"X-Test-Tenant": tenant_b})).json()["total"] == 0


@pytest.mark.asyncio
async def test_truth_check_stale_cross_tenant_does_not_process_other_tenant_data(tenant_aware_client: AsyncClient) -> None:
    tenant_a = str(TEST_ORG_ID)
    tenant_b = str(uuid.uuid4())
    create = await tenant_aware_client.post("/api/v1/truths", json=make_truth_payload(), headers={"X-Test-Tenant": tenant_a})
    assert create.status_code == 201

    check_other = await tenant_aware_client.post("/api/v1/truths/check-stale", headers={"X-Test-Tenant": tenant_b})
    assert check_other.status_code == 200
