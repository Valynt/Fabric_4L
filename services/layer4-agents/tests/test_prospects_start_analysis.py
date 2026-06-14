from __future__ import annotations

"""Tests for prospects start-analysis endpoint.

Validates:
- Tenant context validation (fails closed)
- Prospect creation/persistence
- Workflow trigger integration
- Explicit status reporting (no hardcoded data)
- Degraded mode handling when services unavailable
"""


from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from layer4_agents.api.routes import prospects
from layer4_agents.models.account import Account


@pytest.fixture
def prospects_app() -> FastAPI:
    """Build FastAPI app with prospects routes."""
    app = FastAPI()
    app.include_router(prospects.router, prefix="/v1")
    return app


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


class FakeExecutor:
    """Minimal executor stub for workflow tests."""

    def __init__(self, workflow_id: str = "wf-test-123", should_fail: bool = False):
        self.workflow_id = workflow_id
        self.should_fail = should_fail
        self.execute_calls: list[dict[str, Any]] = []

    async def execute_workflow(self, **kwargs: Any) -> Any:
        self.execute_calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("Workflow execution failed")
        return SimpleNamespace(
            workflow_id=self.workflow_id,
            status=SimpleNamespace(value="running"),
        )


# =============================================================================
# Tenant Context Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_missing_tenant_fails_closed(prospects_app: FastAPI) -> None:
    """Missing tenant context should return 401 (fail closed)."""
    # Override auth to return empty tenant
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: None
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: AsyncMock(spec=AsyncSession)
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "John Doe",
                    "contact_title": "VP Sales",
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    detail = data.get("detail", "")
    if isinstance(detail, str):
        assert "tenant" in detail.lower()
    else:
        # detail might be a dict or other structure
        assert "tenant" in str(data).lower()


@pytest.mark.asyncio
async def test_start_analysis_valid_tenant_creates_prospect(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Valid tenant should allow prospect creation."""
    test_tenant = str(uuid4())
    test_user = "user-123"

    # Setup mocks
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No existing account
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor(workflow_id="wf-123")
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id=test_user)
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Acme Corp",
                    "contact_name": "Jane Smith",
                    "contact_title": "VP Operations",
                    "primary_objective": "improve_efficiency",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "prospect_id" in data
    assert data["status"] == "started"
    assert data["workflow_id"] == "wf-123"


# =============================================================================
# Prospect Persistence Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_creates_new_prospect(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should create new Account record with stage='prospect'."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "New Company",
                    "contact_name": "New Contact",
                    "contact_title": "Director",
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify db.add was called with an Account
    calls = mock_db_session.add.call_args_list
    assert len(calls) == 1
    added_account = calls[0][0][0]
    assert added_account.provider == "value_fabric"
    assert added_account.stage == "prospect"
    assert added_account.name == "New Company"
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_start_analysis_updates_existing_prospect(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should update existing prospect with new setup data."""
    test_tenant = str(uuid4())
    existing_id = uuid4()

    # Create existing account
    existing_account = Account(
        id=existing_id,
        provider="value_fabric",
        provider_record_id="old-record-id",
        name="Old Company Name",
        stage="prospect",
        contacts=[],
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_account
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{existing_id}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Updated Company Name",
                    "contact_name": "Updated Contact",
                    "contact_title": "CEO",
                    "primary_objective": "increase_revenue",
                    "buyer_role_confirmed": True,
                    "company_confirmed": True,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    assert existing_account.name == "Updated Company Name"
    assert len(existing_account.contacts) == 1
    assert existing_account.contacts[0]["name"] == "Updated Contact"
    assert existing_account.contacts[0]["is_primary"] is True


# =============================================================================
# Workflow Trigger Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_triggers_workflow(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should trigger workflow with correct parameters."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor(workflow_id="wf-prospect-456")
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": "VP Sales",
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                },
                "workflow_type": "prospect_analysis",
                "priority": "HIGH",
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["workflow_id"] == "wf-prospect-456"

    # Verify workflow executor was called with correct params
    assert len(fake_executor.execute_calls) == 1
    call = fake_executor.execute_calls[0]
    assert call["workflow_type"] == "prospect_analysis"
    assert call["tenant_id"] == test_tenant
    assert call["input_data"]["company_name"] == "Test Corp"


# =============================================================================
# No Hardcoded Data Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_no_hardcoded_company_data(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should never return hardcoded employee count or revenue."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": "VP",
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Should not contain hardcoded demo values
    assert "12K employees" not in str(data)
    assert "$4.2B revenue" not in str(data)
    assert "MAC-2026" not in str(data)  # No hardcoded CRM ID

    # Should report unavailable/pending status
    assert data["enrichment_status"] in ["unavailable", "pending", "queued"]


@pytest.mark.asyncio
async def test_start_analysis_no_hardcoded_crm_match(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should never return hardcoded CRM opportunity ID."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": None,
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # CRM should be unavailable, not hardcoded match
    assert data["crm_match"]["status"] in ["unavailable", "not_found"]
    assert data["crm_match"]["opportunity_id"] is None
    assert "MAC-2026" not in str(data)


# =============================================================================
# Degraded Mode Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_degraded_when_workflow_fails(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should return degraded status when workflow trigger fails."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor(should_fail=True)
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": None,
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    # Should still succeed (201) with degraded status
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "degraded"
    assert "workflow trigger failed" in data["message"].lower()
    assert data["prospect_id"] is not None  # Prospect still created


@pytest.mark.asyncio
async def test_start_analysis_degraded_when_executor_unavailable(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should return degraded status when executor is None."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": None,
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "degraded"
    assert "executor unavailable" in data["message"].lower()


# =============================================================================
# Buyer Role Inference Tests
# =============================================================================


@pytest.mark.asyncio
async def test_start_analysis_buyer_role_from_executive_title(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should infer buyer role from executive title with pending status."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": "VP Manufacturing Operations",  # Executive pattern
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Should infer Economic Buyer but mark as pending (needs confirmation)
    assert data["buyer_role_inference"]["role"] == "Economic Buyer"
    assert data["buyer_role_inference"]["status"] == "pending"
    assert data["buyer_role_inference"]["confidence"] == 0.6  # Low confidence heuristic
    assert data["buyer_role_inference"]["source"] == "title_heuristic"


@pytest.mark.asyncio
async def test_start_analysis_no_buyer_role_for_non_executive(
    prospects_app: FastAPI,
    mock_db_session: AsyncMock,
) -> None:
    """Should not infer role for non-executive titles."""
    test_tenant = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    fake_executor = FakeExecutor()
    prospects_app.dependency_overrides[prospects.get_db_from_context] = lambda: mock_db_session
    prospects_app.dependency_overrides[prospects.get_verified_tenant_id] = lambda: test_tenant
    prospects_app.dependency_overrides[prospects.require_authenticated] = lambda: MagicMock(user_id="user-1")
    prospects_app.dependency_overrides[prospects.get_executor] = lambda: fake_executor

    async with AsyncClient(transport=ASGITransport(app=prospects_app), base_url="http://test") as client:
        response = await client.post(
            f"/v1/prospects/{uuid4()}/start-analysis",
            json={
                "setup_data": {
                    "company_name": "Test Corp",
                    "contact_name": "Test Contact",
                    "contact_title": "Engineer",  # Non-executive
                    "primary_objective": "reduce_costs",
                    "buyer_role_confirmed": False,
                    "company_confirmed": False,
                    "crm_reviewed": False,
                }
            },
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Should not infer role for non-executive title
    assert data["buyer_role_inference"]["role"] is None
    assert data["buyer_role_inference"]["status"] == "pending"
    assert data["buyer_role_inference"]["source"] == "title_not_executive_pattern"
