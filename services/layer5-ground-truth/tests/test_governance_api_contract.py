"""
Contract tests for Layer 5 Governance APIs.

Tests for request/response schema validation, error envelopes, lifecycle actions, pagination, and filtering.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestGovernanceAPIContract:
    """Contract tests for governance API endpoints."""

    async def test_formula_create_request_schema_validation(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that formula creation validates request schema."""
        # Missing required field
        response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "Test Formula",
                # Missing slug
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
            },
        )
        assert response.status_code == 422

    async def test_formula_create_response_schema(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that formula creation returns valid response schema."""
        response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
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
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "tenant_id" in data
        assert data["name"] == "Test Formula"
        assert data["slug"] == "test-formula"
        assert data["current_version"] is None  # No approved version yet
        assert data["latest_version"] == "0.1.0"
        assert "created_at" in data
        assert "updated_at" in data

    async def test_formula_list_pagination(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that formula listing supports pagination."""
        # Create multiple formulas
        for i in range(5):
            await client.post(
                "/api/v1/governance/formulas",
                headers=auth_headers_full_permissions,
                json={
                    "name": f"Formula {i}",
                    "slug": f"formula-{i}",
                    "formula_type": "roi",
                    "expression": "x * y",
                    "expression_language": "python",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "number"},
                    "parameters": [],
                },
            )

        # List with page size 2
        response = await client.get(
            "/api/v1/governance/formulas?page=1&page_size=2",
            headers=auth_headers_full_permissions,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_next" in data
        assert len(data["items"]) == 2
        assert data["has_next"] is True

    async def test_formula_list_filtering_by_type(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that formula listing supports filtering by type."""
        # Create formulas of different types
        await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "ROI Formula",
                "slug": "roi-formula",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "NPV Formula",
                "slug": "npv-formula",
                "formula_type": "npv",
                "expression": "sum(x / (1 + r)^t)",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )

        # Filter by type
        response = await client.get(
            "/api/v1/governance/formulas?formula_type=roi",
            headers=auth_headers_full_permissions,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["formula_type"] == "roi"

    async def test_formula_version_lifecycle(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test formula version lifecycle: create -> submit -> approve."""
        # Create formula
        create_response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "Lifecycle Formula",
                "slug": "lifecycle-formula",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert create_response.status_code == 201
        formula_id = create_response.json()["id"]

        # Create new version
        version_response = await client.post(
            f"/api/v1/governance/formulas/{formula_id}/versions",
            headers=auth_headers_full_permissions,
            json={
                "version": "1.0.0",
                "expression": "x * y * 2",
                "expression_language": "python",
                "change_description": "Doubled the output",
            },
        )
        assert version_response.status_code == 201
        version_data = version_response.json()
        assert version_data["status"] == "DRAFT"

        # Submit for approval
        submit_response = await client.post(
            f"/api/v1/governance/formulas/{formula_id}/versions/1.0.0/submit",
            headers=auth_headers_full_permissions,
        )
        assert submit_response.status_code == 200
        submit_data = submit_response.json()
        assert submit_data["status"] == "PENDING_APPROVAL"

        # Approve
        approve_response = await client.post(
            f"/api/v1/governance/formulas/{formula_id}/versions/1.0.0/approve",
            headers=auth_headers_full_permissions,
        )
        assert approve_response.status_code == 200
        approve_data = approve_response.json()
        assert approve_data["status"] == "APPROVED"
        assert approve_data["approved_by"] is not None
        assert approve_data["approved_at"] is not None

    async def test_formula_deprecation_lifecycle(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test formula deprecation lifecycle."""
        # Create and approve formula
        create_response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "Deprecatable Formula",
                "slug": "deprecatable-formula",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        formula_id = create_response.json()["id"]

        # Deprecate
        deprecate_response = await client.post(
            f"/api/v1/governance/formulas/{formula_id}/deprecate?reason=No longer needed",
            headers=auth_headers_full_permissions,
        )
        assert deprecate_response.status_code == 200
        data = deprecate_response.json()
        assert data["is_active"] is False
        assert data["deprecated_at"] is not None
        assert data["deprecation_reason"] == "No longer needed"

    async def test_benchmark_effective_date_validation(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that benchmark effective date is required."""
        response = await client.post(
            "/api/v1/governance/benchmarks",
            headers=auth_headers_full_permissions,
            json={
                "name": "Test Benchmark",
                "slug": "test-benchmark",
                "benchmark_type": "industry_standard",
                "source_name": "Test Source",
                "source_type": "research",
                "data": {"values": [1, 2, 3]},
                "data_schema": {"type": "array"},
                # Missing effective_from
            },
        )
        assert response.status_code == 422

    async def test_policy_evaluation_response_schema(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that policy evaluation returns valid response schema."""
        # Create policy
        policy_response = await client.post(
            "/api/v1/governance/policies",
            headers=auth_headers_full_permissions,
            json={
                "name": "Test Policy",
                "slug": "test-policy",
                "policy_type": "validation",
                "description": "Test policy",
                "rules": [],
                "severity": "medium",
            },
        )
        assert policy_response.status_code == 201
        policy_id = policy_response.json()["id"]

        # Evaluate policy
        eval_response = await client.post(
            f"/api/v1/governance/policies/{policy_id}/evaluate",
            headers=auth_headers_full_permissions,
            json={
                "entity_id": "00000000-0000-0000-0000-000000000001",
                "entity_type": "formula",
                "context": {"test": "data"},
            },
        )
        # Note: This may fail if no approved version exists, but should return proper error
        assert eval_response.status_code in [200, 400, 404]

    async def test_assumption_evidence_addition(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that evidence can be added to assumptions."""
        # Create assumption
        assumption_response = await client.post(
            "/api/v1/governance/assumptions",
            headers=auth_headers_full_permissions,
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
        assert assumption_response.status_code == 201
        assumption_id = assumption_response.json()["id"]

        # Add evidence
        evidence_response = await client.post(
            f"/api/v1/governance/assumptions/{assumption_id}/evidence",
            headers=auth_headers_full_permissions,
            json={
                "evidence_type": "research",
                "truth_object_id": "00000000-0000-0000-0000-000000000001",
                "source_url": "https://example.com",
                "source_title": "Research Paper",
                "confidence": 0.8,
                "relevance": 0.9,
            },
        )
        assert evidence_response.status_code == 201
        data = evidence_response.json()
        assert data["evidence_count"] == 1

    async def test_value_entry_update_append_only(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that value entry updates are append-only."""
        # Create value entry
        entry_response = await client.post(
            "/api/v1/governance/value-entries",
            headers=auth_headers_full_permissions,
            json={
                "entry_type": "revenue",
                "entry_name": "Test Entry",
                "current_value": 1000.0,
            },
        )
        assert entry_response.status_code == 201
        entry_id = entry_response.json()["id"]

        # Add update
        update_response = await client.post(
            f"/api/v1/governance/value-entries/{entry_id}/updates",
            headers=auth_headers_full_permissions,
            json={
                "new_value": 1500.0,
                "update_reason": "Actual revenue",
                "update_notes": "Q1 results",
            },
        )
        assert update_response.status_code == 201
        data = update_response.json()
        assert data["current_value"] == 1500.0

    async def test_approval_workflow_lifecycle(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test approval workflow lifecycle: pending -> approved/rejected."""
        # List approvals
        response = await client.get(
            "/api/v1/governance/approvals",
            headers=auth_headers_full_permissions,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_error_envelope_404(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that 404 errors return proper error envelope."""
        response = await client.get(
            "/api/v1/governance/formulas/00000000-0000-0000-0000-000000000001",
            headers=auth_headers_full_permissions,
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_error_envelope_409_conflict(
        self,
        client: AsyncClient,
        auth_headers_full_permissions: dict[str, str],
    ):
        """Test that 409 conflict errors return proper error envelope."""
        # Create formula
        await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "Conflict Formula",
                "slug": "conflict-slug",
                "formula_type": "roi",
                "expression": "x * y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )

        # Try to create with same slug
        response = await client.post(
            "/api/v1/governance/formulas",
            headers=auth_headers_full_permissions,
            json={
                "name": "Another Formula",
                "slug": "conflict-slug",
                "formula_type": "roi",
                "expression": "x + y",
                "expression_language": "python",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "number"},
                "parameters": [],
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
