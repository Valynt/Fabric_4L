"""
Security tests for Layer 5 Governance APIs.

Tests for authorization, permission enforcement, and tenant isolation.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestGovernanceAPISecurity:
    """Security tests for governance API endpoints."""

    async def test_formula_create_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that formula creation requires layer5.governance.formulas.create permission."""
        response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_no_permission,
            json={
                "name": "Test Formula",
                "slug": "test-formula",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response.status_code == 403

    async def test_formula_list_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that formula listing requires layer5.governance.formulas.list permission."""
        response = await client.get(
            "/api/v1/governance/formulas",
            headers=auth_headers_no_permission,
        )
        assert response.status_code == 403

    async def test_benchmark_create_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that benchmark creation requires layer5.governance.benchmarks.create permission."""
        response = await client.post(
            "/api/v1/governance/benchmarks",
            headers=auth_headers_no_permission,
            json={
                "name": "Test Benchmark",
                "slug": "test-benchmark",
                "benchmark_type": "industry_standard",
                "source_name": "Test Source",
                "source_type": "research",
                "data": {"values": [1, 2, 3]},
                "data_schema": {"type": "array"},
                "effective_from": "2024-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 403

    async def test_policy_create_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that policy creation requires layer5.governance.policies.create permission."""
        response = await client.post(
            "/api/v1/governance/policies",
            headers=auth_headers_no_permission,
            json={
                "name": "Test Policy",
                "slug": "test-policy",
                "policy_type": "validation",
                "description": "Test policy",
                "rules": [],
                "severity": "medium",
            },
        )
        assert response.status_code == 403

    async def test_assumption_create_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that assumption creation requires layer5.governance.assumptions.create permission."""
        response = await client.post(
            "/api/v1/governance/assumptions",
            headers=auth_headers_no_permission,
            json={
                "name": "Test Assumption",
                "slug": "test-assumption",
                "assumption_type": "market_growth",
                "description": "Test assumption",
                "value": 0.1,
                "value_type": "percentage",
                "impact_level": "medium",
            },
        )
        assert response.status_code == 403

    async def test_value_entry_create_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that value entry creation requires layer5.governance.value_entries.create permission."""
        response = await client.post(
            "/api/v1/governance/value-entries",
            headers=auth_headers_no_permission,
            json={
                "entry_type": "revenue",
                "entry_name": "Test Entry",
                "current_value": 1000.0,
            },
        )
        assert response.status_code == 403

    async def test_approval_approve_requires_permission(
        self,
        client: AsyncClient,
        auth_headers_no_permission: dict[str, str],
    ):
        """Test that approval requires layer5.governance.approvals.approve permission."""
        response = await client.post(
            "/api/v1/governance/approvals/00000000-0000-0000-0000-000000000001/approve",
            headers=auth_headers_no_permission,
        )
        assert response.status_code == 403

    async def test_tenant_isolation_formula(
        self,
        client: AsyncClient,
        auth_headers_tenant_a: dict[str, str],
        auth_headers_tenant_b: dict[str, str],
        db: AsyncSession,
    ):
        """Test that formulas are isolated by tenant."""
        # Create formula in tenant A
        response_a = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_tenant_a,
            json={
                "name": "Tenant A Formula",
                "slug": "tenant-a-formula",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response_a.status_code == 201
        formula_id = response_a.json()["id"]

        # Try to access from tenant B
        response_b = await client.get(
            f"/api/v1/governance/formulas/{formula_id}",
            headers=auth_headers_tenant_b,
        )
        assert response_b.status_code == 404

    async def test_tenant_isolation_benchmark(
        self,
        client: AsyncClient,
        auth_headers_tenant_a: dict[str, str],
        auth_headers_tenant_b: dict[str, str],
    ):
        """Test that benchmarks are isolated by tenant."""
        # Create benchmark in tenant A
        response_a = await client.post(
            "/api/v1/governance/benchmarks",
            headers=auth_headers_tenant_a,
            json={
                "name": "Tenant A Benchmark",
                "slug": "tenant-a-benchmark",
                "benchmark_type": "industry_standard",
                "source_name": "Test Source",
                "source_type": "research",
                "data": {"values": [1, 2, 3]},
                "data_schema": {"type": "array"},
                "effective_from": "2024-01-01T00:00:00Z",
            },
        )
        assert response_a.status_code == 201
        benchmark_id = response_a.json()["id"]

        # Try to access from tenant B
        response_b = await client.get(
            f"/api/v1/governance/benchmarks/{benchmark_id}",
            headers=auth_headers_tenant_b,
        )
        assert response_b.status_code == 404

    async def test_formula_slug_conflict_within_tenant(
        self,
        client: AsyncClient,
        auth_headers_tenant_a: dict[str, str],
    ):
        """Test that slug conflicts are detected within a tenant."""
        # Create first formula
        response1 = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_tenant_a,
            json={
                "name": "Formula 1",
                "slug": "duplicate-slug",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response1.status_code == 201

        # Try to create second formula with same slug
        response2 = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_tenant_a,
            json={
                "name": "Formula 2",
                "slug": "duplicate-slug",
                "formula_type": "roi",
                "expression": "x + y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response2.status_code == 409

    async def test_formula_slug_different_tenants_allowed(
        self,
        client: AsyncClient,
        auth_headers_tenant_a: dict[str, str],
        auth_headers_tenant_b: dict[str, str],
    ):
        """Test that same slug is allowed across different tenants."""
        # Create formula in tenant A
        response_a = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_tenant_a,
            json={
                "name": "Tenant A Formula",
                "slug": "shared-slug",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response_a.status_code == 201

        # Create formula with same slug in tenant B (should succeed)
        response_b = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_tenant_b,
            json={
                "name": "Tenant B Formula",
                "slug": "shared-slug",
                "formula_type": "roi",
                "expression": "x + y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response_b.status_code == 201
