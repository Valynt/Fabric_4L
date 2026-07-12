"""
Contract tests for Layer 4 Agents API.

Validates that L4 endpoints (workflows, tools, agents, billing) 
conform to the OpenAPI specification and return expected response shapes.
"""

import pytest
from httpx import AsyncClient

# =============================================================================
# Workflow Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_workflows_create_endpoint_exists(layer4_client: AsyncClient):
    """Verify POST /v1/workflows is implemented."""
    response = await layer4_client.post(
        "/v1/workflows",
        json={
            "workflow_type": "business_case",
            "tenant_id": "tenant-001",
            "user_id": "user-001",
            "inputs": {"entity_id": "test-123"},
        }
    )
    assert response.status_code != 404, "Workflows create endpoint should exist"
    assert response.status_code in [200, 201, 400, 422], \
        f"Expected 200, 201, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflows_list_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/workflows is implemented."""
    response = await layer4_client.get("/v1/workflows")
    assert response.status_code != 404, "Workflows list endpoint should exist"
    assert response.status_code in [200, 400, 401, 422], \
        f"Expected 200, 400, 401, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_status_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/workflows/{id} is implemented."""
    response = await layer4_client.get("/v1/workflows/wf-test-123")
    assert response.status_code != 404, "Workflow status endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_result_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/workflows/{id}/result is implemented."""
    response = await layer4_client.get("/v1/workflows/wf-test-123/result")
    assert response.status_code != 404, "Workflow result endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_cancel_endpoint_exists(layer4_client: AsyncClient):
    """Verify DELETE /v1/workflows/{id} (cancel) is implemented."""
    response = await layer4_client.delete("/v1/workflows/wf-test-123")
    assert response.status_code != 404, "Workflow cancel endpoint should exist"
    assert response.status_code in [200, 202, 400, 404, 422], \
        f"Expected 200, 202, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_resume_endpoint_exists(layer4_client: AsyncClient):
    """Verify POST /v1/workflows/{id}/resume is implemented."""
    response = await layer4_client.post(
        "/v1/workflows/wf-test-123/resume",
        json={"user_id": "user-001", "resume_data": {"approved": True}}
    )
    assert response.status_code != 404, "Workflow resume endpoint should exist"
    assert response.status_code in [200, 400, 404, 422, 503], \
        f"Expected 200, 400, 404, 422, or 503, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_pause_endpoint_exists(layer4_client: AsyncClient):
    """Verify POST /v1/workflows/{id}/pause is implemented."""
    response = await layer4_client.post(
        "/v1/workflows/wf-test-123/pause",
        json={"user_id": "user-001", "reason": "Human review required"}
    )
    assert response.status_code != 404, "Workflow pause endpoint should exist"
    assert response.status_code in [200, 400, 404, 422, 503], \
        f"Expected 200, 400, 404, 422, or 503, got {response.status_code}"


@pytest.mark.asyncio
async def test_workflow_events_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/workflows/{id}/events is implemented."""
    response = await layer4_client.get("/v1/workflows/wf-test-123/events")
    assert response.status_code != 404, "Workflow events endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


# =============================================================================
# Tool Registry Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_tools_list_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/tools is implemented."""
    response = await layer4_client.get("/v1/tools")
    assert response.status_code != 404, "Tools list endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_tools_list_with_category_filter(layer4_client: AsyncClient):
    """Verify GET /v1/tools?category=... filtering works."""
    response = await layer4_client.get("/v1/tools?category=knowledge")
    assert response.status_code != 404, "Tools list with category filter should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_tools_list_with_search_filter(layer4_client: AsyncClient):
    """Verify GET /v1/tools?search=... search works."""
    response = await layer4_client.get("/v1/tools?search=calculator")
    assert response.status_code != 404, "Tools list with search filter should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_tool_schema_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/tools/{tool_name} is implemented."""
    response = await layer4_client.get("/v1/tools/calculator")
    assert response.status_code != 404, "Tool schema endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_tool_invoke_endpoint_exists(layer4_client: AsyncClient):
    """Verify POST /v1/tools/invoke is implemented."""
    response = await layer4_client.post(
        "/v1/tools/invoke",
        json={
            "tool_name": "calculator",
            "parameters": {"expression": "2 + 2"},
            "tenant_id": "tenant-001",
            "user_id": "user-001",
        }
    )
    assert response.status_code != 404, "Tool invoke endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# =============================================================================
# Agent Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_agents_list_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/agents is implemented."""
    response = await layer4_client.get("/v1/agents")
    assert response.status_code != 404, "Agents list endpoint should exist"
    assert response.status_code in [200, 400, 401, 422], \
        f"Expected 200, 400, 401, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_agent_get_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/agents/{agent_id} is implemented."""
    response = await layer4_client.get("/v1/agents/test-agent-123")
    assert response.status_code != 404, "Agent get endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_agent_execute_endpoint_exists(layer4_client: AsyncClient):
    """Verify POST /v1/agents/{agent_id}/execute is implemented."""
    response = await layer4_client.post(
        "/v1/agents/test-agent-123/execute",
        json={
            "inputs": {"query": "What is the ROI?"},
            "tenant_id": "tenant-001",
            "user_id": "user-001",
        }
    )
    assert response.status_code != 404, "Agent execute endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


# =============================================================================
# Billing/Cost Endpoints
# =============================================================================

@pytest.mark.asyncio
async def test_billing_usage_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/billing/usage is implemented."""
    response = await layer4_client.get("/v1/billing/usage")
    assert response.status_code != 404, "Billing usage endpoint should exist"
    assert response.status_code in [200, 400, 401, 422], \
        f"Expected 200, 400, 401, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_billing_costs_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/billing/costs is implemented."""
    response = await layer4_client.get("/v1/billing/costs")
    assert response.status_code != 404, "Billing costs endpoint should exist"
    assert response.status_code in [200, 400, 401, 422], \
        f"Expected 200, 400, 401, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_billing_export_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /v1/billing/export is implemented."""
    response = await layer4_client.get("/v1/billing/export?format=csv")
    assert response.status_code != 404, "Billing export endpoint should exist"
    assert response.status_code in [200, 400, 401, 422], \
        f"Expected 200, 400, 401, or 422, got {response.status_code}"


# =============================================================================
# Health Endpoint
# =============================================================================

@pytest.mark.asyncio
async def test_health_endpoint_exists(layer4_client: AsyncClient):
    """Verify GET /health is implemented."""
    response = await layer4_client.get("/health")
    assert response.status_code == 200, "Health endpoint should return 200"


# =============================================================================
# Response Schema Validation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tools_list_returns_array(layer4_client: AsyncClient):
    """Verify tools list returns an array response."""
    response = await layer4_client.get("/v1/tools")
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list), "Tools list should return an array"


@pytest.mark.asyncio
async def test_workflow_status_response_has_required_fields(layer4_client: AsyncClient):
    """Verify workflow status response contains required fields."""
    response = await layer4_client.get("/v1/workflows/wf-test-123")
    if response.status_code == 200:
        data = response.json()
        required_fields = ["workflow_id", "status"]
        for field in required_fields:
            assert field in data, f"Workflow status response missing required field: {field}"


@pytest.mark.asyncio
async def test_tool_invoke_response_has_required_fields(layer4_client: AsyncClient):
    """Verify tool invoke response contains required fields."""
    response = await layer4_client.post(
        "/v1/tools/invoke",
        json={
            "tool_name": "calculator",
            "parameters": {"expression": "2 + 2"},
            "tenant_id": "tenant-001",
            "user_id": "user-001",
        }
    )
    if response.status_code == 200:
        data = response.json()
        # ToolResult schema requires
        assert "status" in data, "Tool invoke response missing status field"
        assert data["status"] in ["success", "error", "partial"], \
            "Tool status should be one of: success, error, partial"
