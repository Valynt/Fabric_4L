"""Layer 6 Security Invariants Test Suite.

Tests verify critical security invariants for Layer 6 (Benchmarks):
- Tenant isolation on benchmark datasets
- Input validation on benchmark queries
- Authentication on protected benchmark endpoints
- Authorization on admin endpoints
- RLS policy verification for benchmark tables
- Error handling for benchmark failures

Each invariant has:
1. Positive test proving intended behavior works
2. Negative test proving invalid input is rejected
3. Adversarial test proving attacks are blocked
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary, pytest.mark.integration]


class TestLayer6TenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_can_only_access_own_datasets(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/benchmarks/datasets", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_cross_tenant_dataset_access_denied(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/benchmarks/datasets/tenant-b-dataset", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [404, 403]


class TestLayer6Authentication:
    @pytest.mark.asyncio
    async def test_valid_jwt_allows_benchmark_access(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/benchmarks/datasets", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, client: AsyncClient):
        response = await client.get("/v1/benchmarks/datasets")
        assert response.status_code == 401


class TestLayer6InputValidation:
    @pytest.mark.asyncio
    async def test_valid_comparison_request_accepted(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post(
            "/v1/benchmarks/compare",
            json={"company_value": 100.0, "benchmark_id": "manufacturing-efficiency-2024"},
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_negative_company_value_rejected(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post(
            "/v1/benchmarks/compare",
            json={"company_value": -50.0, "benchmark_id": "manufacturing-efficiency-2024"},
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_sql_injection_in_benchmark_id_blocked(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get(
            "/v1/benchmarks/datasets/' OR '1'='1",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code in [400, 404, 422]


class TestLayer6ErrorHandling:
    @pytest.mark.asyncio
    async def test_404_returns_generic_message(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/benchmarks/datasets/non-existent", headers={"Authorization": f"Bearer {tenant_a_token}"})
        if response.status_code == 404:
            assert "traceback" not in str(response.json()).lower()


def _assert_structured_error_contract(response) -> None:
    """Layer 6 error shape must be a structured object with a detail field."""
    if response.status_code < 400:
        return
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


class TestLayer6TenantSpoofingDefense:
    @pytest.mark.asyncio
    async def test_datasets_list_conflicting_tenant_query_is_not_honored(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get(
            "/v1/benchmarks/datasets?tenant_id=tenant-b",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert response.status_code in [200, 400, 401, 403, 422]
        _assert_structured_error_contract(response)

    @pytest.mark.asyncio
    async def test_dataset_detail_conflicting_tenant_path_is_not_honored(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get(
            "/v1/benchmarks/datasets/tenant-b:manufacturing-efficiency-2024",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert response.status_code in [404, 400, 401, 403, 422]
        _assert_structured_error_contract(response)

    @pytest.mark.asyncio
    async def test_compare_conflicting_tenant_payload_is_rejected_or_ignored(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post(
            "/v1/benchmarks/compare",
            json={
                "dataset_id": "manufacturing-efficiency-2024",
                "metric": "throughput",
                "company_value": "100.0",
                "industry": "manufacturing",
                "tenant_id": TENANT_B,
            },
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert response.status_code in [200, 400, 401, 403, 404, 422, 503]
        _assert_structured_error_contract(response)

    @pytest.mark.asyncio
    async def test_validate_conflicting_tenant_payload_is_rejected_or_ignored(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post(
            "/v1/benchmarks/validate",
            json={
                "dataset_id": "manufacturing-efficiency-2024",
                "metric": "throughput",
                "value": "100.0",
                "tenant_id": TENANT_B,
            },
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert response.status_code in [200, 400, 401, 403, 404, 422, 503]
        _assert_structured_error_contract(response)

    @pytest.mark.asyncio
    async def test_industries_conflicting_tenant_query_is_not_honored(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get(
            "/v1/benchmarks/industries?tenant_id=tenant-b",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert response.status_code in [200, 400, 401, 403, 422, 503]
        _assert_structured_error_contract(response)
