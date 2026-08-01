"""Hostile tests for analytics endpoint authentication.

Verifies that all analytics endpoints require authentication and reject
unauthenticated requests with 401 Unauthorized.

Fixes: SI-NEW-001, SI-NEW-002
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.fixture
def client():
    """Create test client without authentication."""
    from src.api.main import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver to prevent actual database calls."""
    with patch("src.api.dependencies.get_neo4j_driver") as mock:
        mock.return_value = Mock()
        yield mock


class TestAnalyticsAuthenticationRequired:
    """Verify all analytics endpoints reject unauthenticated requests."""

    def test_detect_communities_requires_authentication(self, client, mock_neo4j):
        """POST /v1/analytics/communities must return 401 without auth."""
        response = client.post(
            "/v1/analytics/communities",
            json={
                "algorithm": "louvain",
                "entity_types": ["Person"],
                "min_community_size": 5,
            },
        )
        assert response.status_code == 401, "Must require authentication"
        mock_neo4j.return_value.execute_query.assert_not_called()

    def test_calculate_centrality_requires_authentication(self, client, mock_neo4j):
        """POST /v1/analytics/centrality must return 401 without auth."""
        response = client.post(
            "/v1/analytics/centrality",
            json={
                "algorithm": "pagerank",
                "entity_types": ["Person"],
                "iterations": 10,
                "damping_factor": 0.85,
            },
        )
        assert response.status_code == 401, "Must require authentication"
        mock_neo4j.return_value.execute_query.assert_not_called()

    def test_find_similar_entities_requires_authentication(self, client, mock_neo4j):
        """POST /v1/analytics/similarity must return 401 without auth."""
        response = client.post(
            "/v1/analytics/similarity",
            json={
                "source_entity_id": "entity-123",
                "algorithm": "cosine",
                "top_k": 10,
            },
        )
        assert response.status_code == 401, "Must require authentication"
        mock_neo4j.return_value.execute_query.assert_not_called()

    def test_detect_drift_requires_authentication(self, client, mock_neo4j):
        """POST /v1/analytics/drift must return 401 without auth."""
        response = client.post(
            "/v1/analytics/drift",
            json={
                "baseline_snapshot_id": "snap-1",
                "current_snapshot_id": "snap-2",
            },
        )
        assert response.status_code == 401, "Must require authentication"
        mock_neo4j.return_value.execute_query.assert_not_called()

    def test_batch_analytics_requires_authentication(self, client, mock_neo4j):
        """POST /v1/batch/analytics must return 401 without auth."""
        response = client.post(
            "/v1/batch/analytics",
            json={
                "entity_ids": ["entity-1", "entity-2"],
                "operations": ["centrality", "similarity"],
            },
        )
        assert response.status_code == 401, "Must require authentication"
        mock_neo4j.return_value.execute_query.assert_not_called()


class TestAnalyticsTenantIsolation:
    """Verify analytics endpoints extract tenant_id from authenticated context."""

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

    def test_detect_communities_uses_authenticated_tenant(self, authenticated_client, mock_neo4j):
        """Communities endpoint must use tenant_id from auth context."""
        client, mock_context = authenticated_client

        # Mock successful response
        mock_neo4j.return_value.execute_query.return_value = [
            {"community_id": "comm-1", "member_count": 10}
        ]

        response = client.post(
            "/v1/analytics/communities",
            json={
                "algorithm": "louvain",
                "entity_types": ["Person"],
                "min_community_size": 5,
            },
        )

        # Verify request succeeded
        assert response.status_code == 200

        # Verify Neo4j query included tenant_id filter
        call_args = mock_neo4j.return_value.execute_query.call_args
        query = call_args[0][0] if call_args[0] else ""
        assert "tenant_id" in query.lower() or "$tenant_id" in query, \
            "Query must filter by tenant_id"

    def test_calculate_centrality_uses_authenticated_tenant(self, authenticated_client, mock_neo4j):
        """Centrality endpoint must use tenant_id from auth context."""
        client, mock_context = authenticated_client

        # Mock successful response
        mock_neo4j.return_value.execute_query.return_value = [
            {"entity_id": "entity-1", "centrality_score": 0.85}
        ]

        response = client.post(
            "/v1/analytics/centrality",
            json={
                "entity_ids": ["entity-1", "entity-2"],
                "algorithm": "pagerank",
            },
        )

        assert response.status_code == 200

        # Verify Neo4j query included tenant_id filter
        call_args = mock_neo4j.return_value.execute_query.call_args
        query = call_args[0][0] if call_args[0] else ""
        assert "tenant_id" in query.lower() or "$tenant_id" in query, \
            "Query must filter by tenant_id"

    def test_find_similar_entities_uses_authenticated_tenant(self, authenticated_client, mock_neo4j):
        """Similarity endpoint must use tenant_id from auth context."""
        client, mock_context = authenticated_client

        # Mock successful response
        mock_neo4j.return_value.execute_query.return_value = [
            {"entity_id": "entity-2", "similarity_score": 0.92}
        ]

        response = client.post(
            "/v1/analytics/similarity",
            json={
                "source_entity_id": "entity-1",
                "algorithm": "cosine",
                "top_k": 10,
            },
        )

        assert response.status_code == 200

        # Verify Neo4j query included tenant_id filter
        call_args = mock_neo4j.return_value.execute_query.call_args
        query = call_args[0][0] if call_args[0] else ""
        assert "tenant_id" in query.lower() or "$tenant_id" in query, \
            "Query must filter by tenant_id"

    def test_detect_drift_uses_authenticated_tenant(self, authenticated_client, mock_neo4j):
        """Drift endpoint must use tenant_id from auth context."""
        client, mock_context = authenticated_client

        # Mock successful response
        mock_neo4j.return_value.execute_query.return_value = [
            {"entity_id": "entity-1", "drift_score": 0.15}
        ]

        response = client.post(
            "/v1/analytics/drift",
            json={
                "baseline_snapshot_id": "snap-1",
                "current_snapshot_id": "snap-2",
            },
        )

        assert response.status_code == 200

        # Verify Neo4j query included tenant_id filter
        call_args = mock_neo4j.return_value.execute_query.call_args
        query = call_args[0][0] if call_args[0] else ""
        assert "tenant_id" in query.lower() or "$tenant_id" in query, \
            "Query must filter by tenant_id"

    def test_batch_analytics_uses_authenticated_tenant(self, authenticated_client, mock_neo4j):
        """Batch analytics endpoint must use tenant_id from auth context."""
        client, mock_context = authenticated_client

        # Mock successful response
        mock_neo4j.return_value.execute_query.return_value = [
            {"entity_id": "entity-1", "results": []}
        ]

        response = client.post(
            "/v1/batch/analytics",
            json={
                "entity_ids": ["entity-1", "entity-2"],
                "operations": ["centrality", "similarity"],
            },
        )

        assert response.status_code == 200

        # Verify Neo4j query included tenant_id filter
        call_args = mock_neo4j.return_value.execute_query.call_args
        query = call_args[0][0] if call_args[0] else ""
        assert "tenant_id" in query.lower() or "$tenant_id" in query, \
            "Query must filter by tenant_id"
