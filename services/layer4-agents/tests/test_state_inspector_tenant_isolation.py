"""Hostile tests for state inspector tenant isolation.

Verifies that all state inspector endpoints verify workflow ownership
and reject cross-tenant access attempts with 403 Forbidden.

Fixes: SI-NEW-003
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch


@pytest.fixture
def mock_workflow_state():
    """Mock workflow state data."""
    return {
        "workflow_id": "workflow-123",
        "tenant_id": "tenant-abc",
        "status": "running",
        "current_node": "node-1",
        "state_data": {"key": "value"},
    }


@pytest.fixture
def mock_different_tenant_workflow():
    """Mock workflow belonging to a different tenant."""
    return {
        "workflow_id": "workflow-456",
        "tenant_id": "tenant-xyz",
        "status": "running",
        "current_node": "node-1",
        "state_data": {"sensitive": "data"},
    }


class TestStateInspectorAuthenticationRequired:
    """Verify all state inspector endpoints reject unauthenticated requests."""

    @pytest.fixture
    def client(self):
        """Create test client without authentication."""
        from src.api.main import create_app
        app = create_app()
        return TestClient(app)

    def test_get_state_schema_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/schema must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/schema")
        assert response.status_code == 401, "Must require authentication"

    def test_get_state_values_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/values must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/values")
        assert response.status_code == 401, "Must require authentication"

    def test_get_state_outputs_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/outputs must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/outputs")
        assert response.status_code == 401, "Must require authentication"

    def test_get_state_errors_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/errors must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/errors")
        assert response.status_code == 401, "Must require authentication"

    def test_get_state_performance_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/performance must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/performance")
        assert response.status_code == 401, "Must require authentication"

    def test_get_state_history_requires_authentication(self, client):
        """GET /v1/workflows/{id}/state/history must return 401 without auth."""
        response = client.get("/v1/workflows/workflow-123/state/history")
        assert response.status_code == 401, "Must require authentication"


class TestStateInspectorTenantIsolation:
    """Verify state inspector endpoints enforce tenant ownership."""

    @pytest.fixture
    def authenticated_client(self):
        """Create test client with mock authentication."""
        from src.api.main import create_app
        from value_fabric.shared.identity import RequestContext

        app = create_app()

        # Mock RequestContext with tenant_id
        mock_context = Mock(spec=RequestContext)
        mock_context.tenant_id = "tenant-abc"
        mock_context.user_id = "user-123"

        # Override dependency
        app.dependency_overrides[
            "value_fabric.shared.identity.dependencies.require_authenticated"
        ] = lambda: mock_context

        return TestClient(app), mock_context

    def test_get_state_schema_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State schema endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/schema")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_schema_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State schema endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/schema")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()

    def test_get_state_values_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State values endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/values")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_values_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State values endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/values")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()

    def test_get_state_outputs_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State outputs endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/outputs")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_outputs_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State outputs endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/outputs")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()

    def test_get_state_errors_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State errors endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/errors")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_errors_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State errors endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/errors")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()

    def test_get_state_performance_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State performance endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/performance")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_performance_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State performance endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/performance")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()

    def test_get_state_history_verifies_tenant_ownership(
        self, authenticated_client, mock_workflow_state
    ):
        """State history endpoint must verify workflow belongs to authenticated tenant."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            response = client.get("/v1/workflows/workflow-123/state/history")

            assert response.status_code == 200
            mock_load.assert_called_once_with("workflow-123")

    def test_get_state_history_blocks_cross_tenant_access(
        self, authenticated_client, mock_different_tenant_workflow
    ):
        """State history endpoint must block access to workflows owned by other tenants."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_different_tenant_workflow

            response = client.get("/v1/workflows/workflow-456/state/history")

            assert response.status_code == 403, "Must block cross-tenant access"
            assert "tenant" in response.json()["detail"].lower()


class TestStateInspectorTenantContextExtraction:
    """Verify state inspector endpoints extract tenant_id from authenticated context."""

    @pytest.fixture
    def authenticated_client(self):
        """Create test client with mock authentication."""
        from src.api.main import create_app
        from value_fabric.shared.identity import RequestContext

        app = create_app()

        # Mock RequestContext with tenant_id
        mock_context = Mock(spec=RequestContext)
        mock_context.tenant_id = "tenant-abc"
        mock_context.user_id = "user-123"

        # Override dependency
        app.dependency_overrides[
            "value_fabric.shared.identity.dependencies.require_authenticated"
        ] = lambda: mock_context

        return TestClient(app), mock_context

    def test_endpoints_use_authenticated_tenant_id(self, authenticated_client, mock_workflow_state):
        """All endpoints must use tenant_id from authenticated context, not request body."""
        client, mock_context = authenticated_client

        with patch(
            "src.api.routes.state_inspector.load_workflow_state",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = mock_workflow_state

            with patch(
                "src.api.routes.state_inspector._require_workflow_tenant_access",
                new_callable=AsyncMock,
            ) as mock_verify:
                # Make request
                response = client.get("/v1/workflows/workflow-123/state/schema")

                assert response.status_code == 200

                # Verify _require_workflow_tenant_access was called with correct tenant_id
                mock_verify.assert_called_once()
                call_args = mock_verify.call_args
                assert call_args[1]["workflow_id"] == "workflow-123"
                assert call_args[1]["tenant_id"] == "tenant-abc"
