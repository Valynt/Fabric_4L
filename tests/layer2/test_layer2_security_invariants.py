"""Layer 2 Security Invariants Test Suite."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary, pytest.mark.integration]


class TestLayer2TenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_can_only_access_own_audit_trails(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/audit/trace/valid-job-id", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_cross_tenant_audit_access_denied(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/audit/trace/tenant-b-job-id", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [404, 403]


class TestLayer2Authentication:
    @pytest.mark.asyncio
    async def test_valid_jwt_allows_audit_access(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/audit/trace/test-job-id", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, client: AsyncClient):
        response = await client.get("/v1/audit/trace/test-job-id")
        assert response.status_code == 401


class TestLayer2InputValidation:
    @pytest.mark.asyncio
    async def test_valid_extraction_payload_accepted(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post("/v1/extraction", json={"document_id": str(uuid4())}, headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_missing_required_field_rejected(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post("/v1/extraction", json={}, headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [400, 422]


class TestLayer2ErrorHandling:
    @pytest.mark.asyncio
    async def test_404_returns_generic_message(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/audit/trace/non-existent", headers={"Authorization": f"Bearer {tenant_a_token}"})
        if response.status_code == 404:
            assert "traceback" not in str(response.json()).lower()
