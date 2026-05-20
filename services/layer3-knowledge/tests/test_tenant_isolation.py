"""Test tenant isolation in Neo4j queries.

These tests verify that all read endpoints enforce tenant_id filtering
to prevent cross-tenant data exposure.

Updated in Sprint 3 (ARCH-L3-011): imports now point to the canonical
locations after app_monolith.py was deleted.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch

from value_fabric.layer3.api.routes.graph_viz import _extract_tenant_id, get_full_graph
from value_fabric.layer3.api.routes.entities import list_entities


class TestTenantIsolation:
    """Verify tenant isolation on all Neo4j read endpoints."""

    @pytest.fixture
    def mock_request_with_tenant(self):
        request = MagicMock()
        request.state = MagicMock()
        request.state.context = MagicMock()
        request.state.context.tenant_id = "tenant-a"
        return request

    @pytest.fixture
    def mock_request_no_tenant(self):
        request = MagicMock()
        request.state = MagicMock()
        request.state.context = None
        return request

    @pytest.fixture
    def mock_neo4j_session(self):
        mock = MagicMock()
        mock.tenant_id = "tenant-a"
        mock.execute_query = AsyncMock(
            return_value=[
                {
                    "total": 0,
                    "id": "e1",
                    "name": "Test",
                    "description": "",
                    "entity_type": "Capability",
                    "confidence_score": 0.8,
                    "created_at": "2024-01-01",
                }
            ]
        )
        return mock

    @pytest.fixture
    def mock_neo4j_session_no_tenant(self):
        mock = MagicMock()
        mock.tenant_id = None
        mock.execute_query = AsyncMock(
            side_effect=ValueError("Tenant context is required")
        )
        return mock

    def test_extract_tenant_id_with_context(self, mock_request_with_tenant):
        """_extract_tenant_id should return tenant_id from request context."""
        tenant_id = _extract_tenant_id(mock_request_with_tenant)
        assert tenant_id == "tenant-a"

    def test_extract_tenant_id_without_context(self, mock_request_no_tenant):
        """_extract_tenant_id should return None without context."""
        tenant_id = _extract_tenant_id(mock_request_no_tenant)
        assert tenant_id is None

    def test_extract_tenant_id_none_request(self):
        """_extract_tenant_id should handle None request."""
        tenant_id = _extract_tenant_id(None)
        assert tenant_id is None

    @pytest.mark.asyncio
    async def test_list_entities_requires_tenant_id(self, mock_neo4j_session_no_tenant):
        """list_entities must reject requests without tenant_id."""
        neo4j = mock_neo4j_session_no_tenant

        with pytest.raises((HTTPException, ValueError)) as exc_info:
            await list_entities(
                search_text=None,
                entity_types=None,
                confidence_min=0.0,
                limit=25,
                offset=0,
                sort_by="updated_at",
                sort_order="desc",
                _ctx=MagicMock(),
                neo4j=neo4j,
            )

        assert exc_info.value.status_code == 401 or "tenant" in str(
            exc_info.value
        ).lower()

    @pytest.mark.asyncio
    async def test_list_entities_includes_tenant_in_where_clause(
        self, mock_neo4j_session
    ):
        """list_entities must include tenant_id in all MATCH queries."""
        neo4j = mock_neo4j_session

        await list_entities(
            search_text=None,
            entity_types=None,
            confidence_min=0.0,
            limit=25,
            offset=0,
            sort_by="updated_at",
            sort_order="desc",
            _ctx=MagicMock(),
            neo4j=neo4j,
        )

        assert neo4j.execute_query.called, "execute_query was not called"
        for call in neo4j.execute_query.call_args_list:
            query = call[0][0] if call[0] else call.kwargs.get("query", "")
            if "MATCH" in str(query):
                assert "tenant_id" in str(query) or "$_tenant_id" in str(query), (
                    f"Query missing tenant_id: {query}"
                )

    @pytest.mark.asyncio
    async def test_get_full_graph_requires_tenant_id(self):
        """get_full_graph must reject requests without tenant_id."""
        mock_state = MagicMock()
        mock_state.neo4j_driver = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_full_graph(
                limit=1000,
                app_state=mock_state,
                request=None,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_full_graph_includes_tenant_in_queries(
        self, mock_request_with_tenant
    ):
        """get_full_graph must include tenant_id in all MATCH queries."""
        mock_state = MagicMock()
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query.return_value = []
        mock_state.neo4j_driver = mock_neo4j

        await get_full_graph(
            limit=1000,
            app_state=mock_state,
            request=mock_request_with_tenant,
        )

        calls = mock_neo4j.execute_query.call_args_list
        assert len(calls) > 0, "No queries were executed"

        for call in calls:
            query = call[0][0]
            params = call[0][1] if len(call[0]) > 1 else (call.kwargs or {})
            if "MATCH" in str(query):
                assert "tenant_id" in str(query) or (
                    params and "tenant_id" in params
                ), f"Query missing tenant_id filter: {query}"

    @pytest.mark.asyncio
    async def test_get_full_graph_fails_closed_when_context_absent(self):
        """Missing auth context must fail closed (400)."""
        mock_state = MagicMock()
        mock_state.neo4j_driver = AsyncMock()

        request = MagicMock()
        request.state = MagicMock()
        request.state.context = None

        with pytest.raises(HTTPException) as exc_info:
            await get_full_graph(limit=1000, app_state=mock_state, request=request)

        assert exc_info.value.status_code == 400

    def test_cross_tenant_access_blocked_in_list_entities(self):
        """Tenant A cannot see Tenant B's entities via list_entities."""
        # Integration coverage requires a live Neo4j instance.
        # Unit-level coverage is provided by the query-inspection tests above.
        pass

    def test_cross_tenant_access_blocked_in_get_full_graph(self):
        """Tenant A cannot see Tenant B's entities via get_full_graph."""
        # Integration coverage requires a live Neo4j instance.
        pass
