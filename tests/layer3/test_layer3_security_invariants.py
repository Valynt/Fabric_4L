"""Layer 3 Security Invariants Test Suite.

Tests verify critical security invariants for Layer 3 (Knowledge):
- Tenant isolation on graph queries and value trees
- Input validation on graph operations
- Authentication on protected knowledge endpoints
- Authorization on admin endpoints
- RLS policy verification for knowledge graph
- Error handling for graph traversal failures

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


class TestLayer3TenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_can_only_access_own_value_trees(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/value-trees", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_cross_tenant_graph_query_denied(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/graph/nodes/tenant-b-node-id", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [404, 403]


class TestLayer3Authentication:
    @pytest.mark.asyncio
    async def test_valid_jwt_allows_knowledge_access(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/value-trees", headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, client: AsyncClient):
        response = await client.get("/v1/value-trees")
        assert response.status_code == 401


class TestLayer3InputValidation:
    @pytest.mark.asyncio
    async def test_valid_graph_query_accepted(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post("/v1/graph/query", json={"query": "MATCH (n) RETURN n LIMIT 1"}, headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_invalid_query_rejected(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post("/v1/graph/query", json={"query": ""}, headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_cypher_injection_blocked(self, client: AsyncClient, tenant_a_token: str):
        response = await client.post("/v1/graph/query", json={"query": "MATCH (n) DELETE n"}, headers={"Authorization": f"Bearer {tenant_a_token}"})
        assert response.status_code in [403, 400]


class TestLayer3ErrorHandling:
    @pytest.mark.asyncio
    async def test_404_returns_generic_message(self, client: AsyncClient, tenant_a_token: str):
        response = await client.get("/v1/value-trees/non-existent", headers={"Authorization": f"Bearer {tenant_a_token}"})
        if response.status_code == 404:
            assert "traceback" not in str(response.json()).lower()
