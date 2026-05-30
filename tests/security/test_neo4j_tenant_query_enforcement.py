"""Security tests for Neo4j tenant query enforcement (Sprint 5).

Validates that Cypher queries in Layer 3 include tenant_id filtering
when tenant context is available. This prevents cross-tenant data leaks.
"""

import uuid
from unittest.mock import MagicMock, AsyncMock, patch, ANY

import pytest


class TestNeo4jTenantQueryEnforcement:
    """Verify tenant_id is included in Cypher queries when context available."""

    @pytest.mark.asyncio
    async def test_entity_detail_query_includes_tenant_id(self, mock_neo4j_driver):
        """P0: Entity detail query must include tenant_id when context available."""
        # Import here to handle optional dependencies
        try:
            from src.api.main import (
                get_entity_detail,
                NEO4J_TENANT_AVAILABLE,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        # Arrange: Create mock request with tenant context
        tenant_id = str(uuid.uuid4())
        entity_id = "test-entity-123"
        
        mock_context = MagicMock()
        mock_context.tenant_id = tenant_id
        
        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context
        
        # Use fixture for mock driver
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        mock_result.single.return_value = None  # Entity not found is fine
        
        # Act: Call the endpoint
        with pytest.raises(Exception):  # Will raise 404, but query should be captured
            await get_entity_detail(
                entity_id=entity_id,
                neo4j_driver=mock_driver,
                request=mock_request,
            )
        
        # Assert: Verify query was called with tenant_id
        mock_session.run.assert_called()
        call_args = mock_session.run.call_args
        query = call_args[0][0] if call_args[0] else call_args[1].get("query", "")
        params = call_args[1] if len(call_args) > 1 and isinstance(call_args[1], dict) else call_args[0][1] if len(call_args[0]) > 1 else {}
        
        # Verify tenant_id appears in query
        assert "tenant_id" in query, f"Query missing tenant_id: {query}"
        assert "$tenant_id" in query, f"Query missing tenant_id parameter: {query}"

    @pytest.mark.asyncio
    async def test_batch_operations_pass_tenant_id_to_helpers(self, mock_neo4j_driver):
        """P0: Batch operations must pass tenant_id to helper functions."""
        try:
            from src.api.main import (
                batch_entity_operations,
                NEO4J_TENANT_AVAILABLE,
                BatchEntityRequest,
                BatchEntityOperation,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        # Arrange
        tenant_id = str(uuid.uuid4())
        entity_id = "test-entity-456"
        
        mock_context = MagicMock()
        mock_context.tenant_id = tenant_id
        
        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context
        
        # Create batch request with update operation
        batch_request = BatchEntityRequest(
            operations=[
                BatchEntityOperation(
                    operation="update",
                    entity_id=entity_id,
                    properties={"name": "Updated Name"}
                )
            ],
            atomic=False
        )
        
        # Use fixture for mock driver
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        mock_result.single.return_value = {"entity_id": entity_id}
        
        # Act
        response = await batch_entity_operations(
            request=batch_request,
            neo4j_driver=mock_driver,
            fastapi_request=mock_request,
        )
        
        # Assert: Verify update query included tenant_id
        mock_session.run.assert_called()
        
        # Find the update call (second call typically)
        found_tenant_filter = False
        for call in mock_session.run.call_args_list:
            query = call[0][0] if call[0] else ""
            if "tenant_id" in query and "$tenant_id" in query:
                found_tenant_filter = True
                break
        
        assert found_tenant_filter, "Update query missing tenant_id filter"

    def test_cypher_query_patterns_include_tenant_filtering(self):
        """Verify source code contains tenant_id filtering in MATCH patterns."""
        from pathlib import Path
        # Count tenant_id occurrences in MATCH patterns
        import re

        candidate_roots = [
            Path("value_fabric/layer3"),
            Path("services/layer3-knowledge/src"),
        ]
        source_parts: list[str] = []
        for root in candidate_roots:
            if root.exists():
                for path in root.rglob("*.py"):
                    if "__pycache__" not in path.parts:
                        source_parts.append(path.read_text(encoding="utf-8"))

        if not source_parts:
            pytest.skip("Layer 3 source not available")

        source = "\n".join(source_parts)
        tenant_patterns = re.findall(r"MATCH.*?tenant_id.*?\$tenant_id", source, re.DOTALL)
        
        # Sprint 5 should have at least 10 tenant-scoped query patterns
        assert len(tenant_patterns) >= 10, (
            f"Expected >= 10 tenant-scoped MATCH patterns, found {len(tenant_patterns)}. "
            f"Source may be missing tenant_id filtering."
        )

    @pytest.mark.asyncio
    async def test_fallback_query_used_when_no_tenant_context(self, mock_neo4j_driver):
        """Query without tenant_id should be used when no context available."""
        try:
            from src.api.main import (
                get_entity_detail,
                NEO4J_TENANT_AVAILABLE,
            )
        except ImportError:
            pytest.skip("Layer 3 not available")

        if not NEO4J_TENANT_AVAILABLE:
            pytest.skip("Neo4j tenant support not available")

        # Arrange: No tenant context (backward compatibility)
        entity_id = "test-entity-789"
        
        # Use fixture for mock driver
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        mock_result.single.return_value = None
        
        # Act: Call with no request (or request without context)
        with pytest.raises(Exception):
            await get_entity_detail(
                entity_id=entity_id,
                neo4j_driver=mock_driver,
                request=None,
            )
        
        # Assert: Verify fallback query used (no tenant_id)
        mock_session.run.assert_called()
        call_args = mock_session.run.call_args
        query = call_args[0][0] if call_args[0] else ""
        
        # Should use fallback query without tenant_id
        assert "$tenant_id" not in query, (
            f"Fallback query should not have tenant_id: {query}"
        )


class TestTenantIdParameterValidation:
    """Verify tenant_id parameter is correctly formatted in queries."""

    def test_tenant_id_converted_to_string_in_params(self):
        """tenant_id should be string in query parameters."""
        try:
            from src.api.main import _extract_tenant_id
        except ImportError:
            pytest.skip("Layer 3 not available")
        
        # Arrange: UUID tenant_id
        tenant_uuid = uuid.uuid4()
        mock_context = MagicMock()
        mock_context.tenant_id = tenant_uuid
        
        mock_request = MagicMock()
        mock_request.state.governance_context = mock_context
        
        # Act
        result = _extract_tenant_id(mock_request)
        
        # Assert
        assert isinstance(result, str)
        assert result == str(tenant_uuid)
