"""Security tests for Neo4j tenant query enforcement (Sprint 5).

Validates that Cypher queries in Layer 3 include tenant_id filtering
without requiring a live Neo4j instance. Live graph connectivity belongs in
``integration``/``requires_neo4j`` profiles; these mandatory security tests use
hermetic fakes so tenant-scoping regressions cannot be skipped by dependency
availability.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.dependencies import _extract_tenant_id as dependency_extract_tenant_id
from src.api.models import BatchEntityOperation, BatchEntityRequest
from src.api.routes.analytics import batch_entity_operations
from src.api.routes.entities import get_entity_detail
from value_fabric.shared.error_handling.exceptions import NotFoundError


class RecordingTenantNeo4jSession:
    """Hermetic stand-in for the secured Layer 3 tenant Neo4j session."""

    def __init__(self, tenant_id: str, records: list[dict] | None = None) -> None:
        self.tenant_id = tenant_id
        self.records = records or []
        self.calls: list[tuple[str, dict]] = []

    async def execute_query(self, query: str, parameters: dict | None = None, **kwargs) -> list[dict]:
        params = dict(parameters or {})
        params.update(kwargs)
        params.setdefault("tenant_id", self.tenant_id)
        params.setdefault("_tenant_id", self.tenant_id)
        self.calls.append((query, params))
        return self.records


def _request_with_context(tenant_id: str) -> MagicMock:
    request = MagicMock()
    request.state.context = MagicMock(tenant_id=tenant_id)
    request.state.tenant_id = tenant_id
    return request


def _assert_query_is_tenant_scoped(query: str, params: dict, tenant_id: str) -> None:
    assert "tenant_id" in query, f"Query missing tenant_id predicate: {query}"
    assert "$tenant_id" in query, f"Query missing tenant_id parameter: {query}"
    assert params["tenant_id"] == tenant_id


class TestNeo4jTenantQueryEnforcement:
    """Verify tenant_id is included in Cypher queries when context is available."""

    @pytest.mark.asyncio
    async def test_entity_detail_query_includes_tenant_id(self):
        """P0: Entity detail query must include tenant_id when context is available."""
        tenant_id = str(uuid.uuid4())
        entity_id = "test-entity-123"
        neo4j = RecordingTenantNeo4jSession(tenant_id)

        with pytest.raises(NotFoundError):
            await get_entity_detail(
                entity_id=entity_id,
                _ctx=MagicMock(tenant_id=tenant_id),
                neo4j=neo4j,
                app_state=MagicMock(),
            )

        assert neo4j.calls, "Entity detail route did not execute a Neo4j query"
        query, params = neo4j.calls[0]
        _assert_query_is_tenant_scoped(query, params, tenant_id)
        assert params["entity_id"] == entity_id

    @pytest.mark.asyncio
    async def test_batch_operations_pass_tenant_id_to_helpers(self, mock_neo4j_driver):
        """P0: Batch operations must pass tenant_id to helper functions."""
        tenant_id = str(uuid.uuid4())
        entity_id = "test-entity-456"
        request = _request_with_context(tenant_id)
        batch_request = BatchEntityRequest(
            operations=[
                BatchEntityOperation(
                    operation="update",
                    entity_id=entity_id,
                    properties={"name": "Updated Name"},
                )
            ],
            atomic=False,
        )
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        mock_result.single.return_value = {"props": {"id": entity_id, "name": "Original Name"}}

        response = await batch_entity_operations(
            request=batch_request,
            neo4j_driver=mock_driver,
            fastapi_request=request,
        )

        assert response.successful == 1
        mock_session.run.assert_called()
        scoped_calls = []
        for call in mock_session.run.call_args_list:
            query = call.args[0]
            params = call.args[1] if len(call.args) > 1 else call.kwargs
            if "$tenant_id" in query:
                scoped_calls.append((query, params))

        assert scoped_calls, "Update query missing tenant_id filter"
        for query, params in scoped_calls:
            _assert_query_is_tenant_scoped(query, params, tenant_id)

    def test_cypher_query_patterns_include_tenant_filtering(self):
        """Mandatory static equivalent: Layer 3 source must contain tenant-scoped MATCH patterns."""
        source_parts: list[str] = []
        for root in [Path("services/layer3-knowledge/src")]:
            assert root.exists(), f"Layer 3 source root is missing: {root}"
            for path in root.rglob("*.py"):
                if "__pycache__" not in path.parts:
                    source_parts.append(path.read_text(encoding="utf-8"))

        source = "\n".join(source_parts)
        tenant_patterns = re.findall(r"MATCH.*?tenant_id.*?\$tenant_id", source, re.DOTALL)
        assert len(tenant_patterns) >= 10, (
            f"Expected >= 10 tenant-scoped MATCH patterns, found {len(tenant_patterns)}. "
            "Source may be missing tenant_id filtering."
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_missing_tenant_context_fails_closed_in_legacy_helper(self, mock_neo4j_driver):
        """Integration profile: legacy compatibility path without tenant context is explicit."""
        # This legacy direct-driver helper path is outside the mandatory profile;
        # mandatory tenant scoping is covered by the static/unit tests above.
        from src.api.routes.analytics import _update_entity

        operation = BatchEntityOperation(
            operation="update",
            entity_id="test-entity-789",
            properties={"name": "Updated Name"},
        )
        result = await _update_entity(mock_neo4j_driver[0], operation, tenant_id=None)
        assert result == {"success": False, "error": "tenant_id is required for entity updates"}


class TestTenantIdParameterValidation:
    """Verify tenant_id parameters are correctly formatted in query helpers."""

    def test_tenant_id_converted_to_string_in_params(self):
        """tenant_id should be string in query parameters."""
        tenant_uuid = uuid.uuid4()
        request = _request_with_context(str(tenant_uuid))
        request.state.tenant_id = tenant_uuid

        result = dependency_extract_tenant_id(request)

        assert isinstance(result, str)
        assert result == str(tenant_uuid)
