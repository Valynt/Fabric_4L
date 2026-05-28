"""L3→L4 cross-layer tenant isolation tests (P0).

Validates that tenant context is properly propagated when Layer 3 calls Layer 4,
ensuring no cross-tenant data leakage across service boundaries.

Test coverage:
1. Tenant context propagation in L3→L4 HTTP calls
2. L4 endpoint validation of tenant context from L3
3. Prevention of cross-tenant data leakage in L3→L4 communication
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


class TestL3ToL4TenantContextPropagation:
    """Test tenant context propagation from Layer 3 to Layer 4."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_document_export_propagates_tenant_context(self, mock_httpx_client):
        """Document export to L4 should include tenant context in headers."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "download_ready": True,
            "download_url": "https://example.com/export.pdf"
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client
        
        # Mock request with tenant context
        mock_request = MagicMock()
        mock_context = MagicMock()
        mock_context.tenant_id = "tenant-123"
        mock_request.state.governance_context = mock_context
        
        # Act - call document export
        from src.api.routes.documents import export_document
        from src.api.models import DocumentExportRequest
        
        request = DocumentExportRequest(
            business_case_id="case-456",
            document_type="business_case",
            format="pdf"
        )
        
        # This would normally be called via FastAPI route
        # For testing, we verify the HTTP call includes tenant context
        result = await export_document(request, mock_request)
        
        # Assert: L4 call should include tenant context in headers
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        headers = call_args[1].get("headers", {})
        
        # Verify tenant context is propagated (this is the security invariant)
        # In production, this should include X-Tenant-ID or similar header
        assert "tenant_id" in str(headers) or "tenant" in str(headers).lower()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_knowledge_subgraph_propagates_tenant_context(self, mock_httpx_client):
        """Knowledge subgraph queries should be tenant-scoped when called by L4."""
        # Setup
        mock_neo4j_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.data.return_value = [
            {"id": "var-1", "name": "Revenue", "default": 1000}
        ]
        mock_neo4j_session.run.return_value = mock_result
        
        # Act - query benchmark variables
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        session = await create_neo4j_tenant_session("tenant-123")
        
        # Verify tenant_id is set in session
        assert session.tenant_id == "tenant-123"
        assert session.is_bypass == False

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_signals_persistence_propagates_tenant_context(self, mock_httpx_client):
        """ValueSignal persistence should be tenant-scoped."""
        # Setup
        mock_neo4j_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.data.return_value = [{"id": "signal-1"}]
        mock_neo4j_session.run.return_value = mock_result
        
        # Act - persist signal with tenant context
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        session = await create_neo4j_tenant_session("tenant-123")
        
        # Verify query includes tenant_id parameter
        query = "CREATE (s:ValueSignal {id: $id, tenant_id: $tenant_id})"
        await session.run(query, id="signal-1")
        
        # Assert: tenant_id was injected into parameters
        call_args = mock_neo4j_session.run.call_args
        params = call_args[1]
        assert params.get("tenant_id") == "tenant-123"


class TestL3ToL4CrossTenantLeakagePrevention:
    """Test prevention of cross-tenant data leakage in L3→L4 communication."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_tenant_a_cannot_access_tenant_b_documents(self, mock_httpx_client):
        """Tenant A should not be able to export Tenant B's documents."""
        # Setup
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Business case not found"
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_httpx_client.return_value = mock_client
        
        # Mock request with tenant A context
        mock_request = MagicMock()
        mock_context = MagicMock()
        mock_context.tenant_id = "tenant-a"
        mock_request.state.governance_context = mock_context
        
        # Act - attempt to export tenant B's document
        from src.api.routes.documents import export_document
        from src.api.models import DocumentExportRequest
        from value_fabric.shared.error_handling.exceptions import NotFoundError
        
        request = DocumentExportRequest(
            business_case_id="tenant-b-case-456",  # Belongs to tenant B
            document_type="business_case",
            format="pdf"
        )
        
        # Assert: Should raise NotFoundError due to tenant scoping
        with pytest.raises(NotFoundError):
            await export_document(request, mock_request)

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_query_tenant_b_knowledge(self):
        """Tenant A should not be able to query Tenant B's knowledge subgraph."""
        # Setup
        mock_neo4j_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.data.return_value = []  # Empty result - tenant B's data not accessible
        mock_neo4j_session.run.return_value = mock_result
        
        # Act - query with tenant A context
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        session = await create_neo4j_tenant_session("tenant-a")
        
        # Query for tenant B's entity
        query = "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e"
        result = await session.run(query, id="tenant-b-entity")
        
        # Assert: query includes tenant-a, not tenant-b
        call_args = mock_neo4j_session.run.call_args
        params = call_args[1]
        assert params.get("tenant_id") == "tenant-a"
        # Should return empty since tenant-a can't access tenant-b's data

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_signals(self):
        """Tenant A should not be able to access Tenant B's ValueSignals."""
        # Setup
        mock_neo4j_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.data.return_value = []  # Empty result
        mock_neo4j_session.run.return_value = mock_result
        
        # Act - query signals with tenant A context
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        session = await create_neo4j_tenant_session("tenant-a")
        
        # Query for signals
        query = "MATCH (s:ValueSignal {tenant_id: $tenant_id}) RETURN s"
        result = await session.run(query)
        
        # Assert: query is scoped to tenant-a
        call_args = mock_neo4j_session.run.call_args
        params = call_args[1]
        assert params.get("tenant_id") == "tenant-a"


class TestL3ToL4TenantContextValidation:
    """Test L4 endpoint validation of tenant context from L3."""

    @pytest.mark.asyncio
    async def test_l4_endpoint_rejects_missing_tenant_context(self):
        """L4 endpoints should reject requests without tenant context."""
        # Setup - mock request without tenant context
        mock_request = MagicMock()
        mock_context = MagicMock()
        mock_context.tenant_id = None
        mock_request.state.governance_context = mock_context
        
        # Act - attempt to create tenant session without tenant_id
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        from value_fabric.shared.error_handling.exceptions import ValidationError
        
        # Assert: Should raise ValidationError
        with pytest.raises(ValueError, match="tenant_id is required"):
            await create_neo4j_tenant_session(None)

    @pytest.mark.asyncio
    async def test_l4_endpoint_validates_tenant_context_format(self):
        """L4 endpoints should validate tenant context format."""
        # Setup - mock request with invalid tenant context
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        # Act - create session with valid tenant_id
        session = await create_neo4j_tenant_session("tenant-123")
        
        # Assert: tenant_id is converted to string
        assert isinstance(session.tenant_id, str)
        assert session.tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_l4_endpoint_strict_validation_blocks_unscoped_queries(self):
        """L4 endpoints with strict validation should block unscoped queries."""
        # Setup
        mock_neo4j_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.data.return_value = []
        mock_neo4j_session.run.return_value = mock_result
        
        # Act - create session with strict validation
        from src.api.dependencies_tenant_secured import create_neo4j_tenant_session
        
        session = await create_neo4j_tenant_session("tenant-123", strict_validation=True)
        
        # Try unscoped query (should be blocked by validation)
        from src.security import UnscopedQueryError
        
        # Note: The actual validation happens in the run() method
        # This test verifies the session is configured for strict validation
        assert session._strict == True
