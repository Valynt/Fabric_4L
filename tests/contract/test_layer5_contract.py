"""
Contract Tests for Layer 5 Ground Truth API

Validates that the implementation matches the OpenAPI specification.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

# ============================================================================
# Core TruthObject Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_create_truth_endpoint_exists(client: AsyncClient):
    """Verify POST /api/v1/truths is implemented."""
    response = await client.post(
        "/api/v1/truths",
        json={
            "claim": "Test claim",
            "claim_type": "efficiency_gain",
            "confidence": 0.85,
        }
    )
    assert response.status_code != 404, "Create truth endpoint should exist"
    assert response.status_code in [201, 400, 422], \
        f"Expected 201, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_list_truths_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/truths is implemented."""
    response = await client.get("/api/v1/truths")
    assert response.status_code != 404, "List truths endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_truth_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/truths/{id} is implemented."""
    test_id = str(uuid4())
    response = await client.get(f"/api/v1/truths/{test_id}")
    assert response.status_code != 404, "Get truth endpoint should exist (may return 404 for missing ID)"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_delete_truth_endpoint_exists(client: AsyncClient):
    """Verify DELETE /api/v1/truths/{id} is implemented."""
    test_id = str(uuid4())
    response = await client.delete(f"/api/v1/truths/{test_id}")
    assert response.status_code != 404, "Delete truth endpoint should exist"
    assert response.status_code in [204, 400, 404, 422], \
        f"Expected 204, 400, 404, or 422, got {response.status_code}"


# ============================================================================
# Validation & State Machine Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_validate_truth_endpoint_exists(client: AsyncClient):
    """Verify POST /api/v1/truths/{id}/validate is implemented."""
    test_id = str(uuid4())
    response = await client.post(
        f"/api/v1/truths/{test_id}/validate",
        json={"action": "advance_supported", "actor": "test-user"}
    )
    assert response.status_code != 404, "Validate truth endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_add_source_endpoint_exists(client: AsyncClient):
    """Verify POST /api/v1/truths/{id}/sources is implemented."""
    test_id = str(uuid4())
    response = await client.post(
        f"/api/v1/truths/{test_id}/sources",
        json={"source_type": "document", "source_url": "https://example.com"}
    )
    assert response.status_code != 404, "Add source endpoint should exist"
    assert response.status_code in [201, 400, 404, 422], \
        f"Expected 201, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_audit_trail_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/truths/{id}/audit is implemented."""
    test_id = str(uuid4())
    response = await client.get(f"/api/v1/truths/{test_id}/audit")
    assert response.status_code != 404, "Audit trail endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


# ============================================================================
# Knowledge Graph Sync Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_sync_kg_endpoint_exists(client: AsyncClient):
    """Verify POST /api/v1/truths/sync-kg is implemented."""
    response = await client.post("/api/v1/truths/sync-kg")
    assert response.status_code != 404, "Sync KG endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Maturity & Reference Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_maturity_ladder_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/maturity-ladder is implemented."""
    response = await client.get("/api/v1/maturity-ladder")
    assert response.status_code == 200, \
        f"Maturity ladder endpoint should return 200, got {response.status_code}"


# ============================================================================
# Freshness Monitoring Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_check_stale_endpoint_exists(client: AsyncClient):
    """Verify POST /api/v1/truths/check-stale is implemented."""
    response = await client.post(
        "/api/v1/truths/check-stale",
        params={"dry_run": True}
    )
    assert response.status_code != 404, "Check stale endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_list_stale_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/truths/stale is implemented."""
    response = await client.get("/api/v1/truths/stale")
    assert response.status_code != 404, "List stale endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_freshness_summary_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/truths/freshness-summary is implemented."""
    response = await client.get("/api/v1/truths/freshness-summary")
    assert response.status_code != 404, "Freshness summary endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Health Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_health_endpoint_exists(client: AsyncClient):
    """Verify GET /api/v1/health is implemented."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200, \
        f"Health endpoint should return 200, got {response.status_code}"


@pytest.mark.asyncio
async def test_assumption_create_endpoint_exists(client: AsyncClient):
    response = await client.post(
        "/api/v1/assumptions",
        json={"name": "Gross margin assumption", "impact_value": 250000.0},
    )
    assert response.status_code != 404
    assert response.status_code in [201, 400, 401, 403, 422]


@pytest.mark.asyncio
async def test_policy_rule_create_endpoint_exists(client: AsyncClient):
    response = await client.post(
        "/api/v1/policy-rules",
        json={
            "name": "Revenue reviewer policy",
            "min_impact_threshold": 100000.0,
            "required_reviewer_role": "finance_reviewer",
        },
    )
    assert response.status_code != 404
    assert response.status_code in [201, 400, 401, 403, 422]
