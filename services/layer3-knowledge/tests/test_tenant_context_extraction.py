"""Tests for tenant context extraction helper (Sprint 5).

Validates that _extract_tenant_id() correctly extracts tenant context
from FastAPI request objects for multi-tenant security.

Updated in Sprint 3 (ARCH-L3-011): imports now point to the canonical
location in api/routes/graph_viz after app_monolith.py was deleted.
"""

import uuid
from unittest.mock import MagicMock

import pytest

# _extract_tenant_id is a module-private helper replicated in each domain
# router that needs it. The graph_viz router is the canonical reference for
# the full-graph / subgraph endpoints that were previously in app_monolith.
from value_fabric.layer3.api.routes.graph_viz import _extract_tenant_id


class TestExtractTenantId:
    """Test suite for _extract_tenant_id() helper function."""

    def test_extracts_tenant_id_from_request_context(self):
        """Should extract tenant_id from request.state.context when available."""
        mock_context = MagicMock()
        mock_context.tenant_id = uuid.uuid4()

        mock_request = MagicMock()
        mock_request.state.context = mock_context

        result = _extract_tenant_id(mock_request)

        assert result is not None
        assert result == str(mock_context.tenant_id)

    def test_returns_none_when_no_tenant_context(self):
        """Should return None when request context has no tenant_id."""
        mock_request = MagicMock()
        mock_request.state.context = MagicMock()
        mock_request.state.context.tenant_id = None

        result = _extract_tenant_id(mock_request)

        assert result is None

    def test_returns_none_when_no_context_attribute(self):
        """Should return None when request.state has no context."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.context = None

        result = _extract_tenant_id(mock_request)

        assert result is None

    def test_returns_none_when_request_is_none(self):
        """Should return None when request parameter is None."""
        result = _extract_tenant_id(None)
        assert result is None

    def test_converts_tenant_id_to_string(self):
        """Should convert UUID tenant_id to string."""
        tenant_uuid = uuid.uuid4()
        mock_context = MagicMock()
        mock_context.tenant_id = tenant_uuid

        mock_request = MagicMock()
        mock_request.state.context = mock_context

        result = _extract_tenant_id(mock_request)

        assert isinstance(result, str)
        assert result == str(tenant_uuid)

    def test_handles_string_tenant_id(self):
        """Should handle string tenant_id without conversion issues."""
        mock_context = MagicMock()
        mock_context.tenant_id = "tenant-123-abc"

        mock_request = MagicMock()
        mock_request.state.context = mock_context

        result = _extract_tenant_id(mock_request)

        assert result == "tenant-123-abc"

    def test_integration_with_real_request_context(self):
        """Integration test with actual RequestContext from shared.identity."""
        try:
            from value_fabric.shared.identity.context import RequestContext

            tenant_id = uuid.uuid4()
            ctx = RequestContext(
                tenant_id=tenant_id,
                user_id=uuid.uuid4(),
                request_id="test-req-123",
            )

            mock_request = MagicMock()
            mock_request.state.context = ctx

            result = _extract_tenant_id(mock_request)

            assert result == str(tenant_id)
        except ImportError:
            pytest.skip("shared.identity.context not available")


class TestExtractTenantIdDeterminism:
    """Verify deterministic behaviour across multiple calls."""

    def test_returns_consistent_result_on_repeated_calls(self):
        """Should return same result for same input (deterministic)."""
        tenant_uuid = uuid.uuid4()
        mock_context = MagicMock()
        mock_context.tenant_id = tenant_uuid

        mock_request = MagicMock()
        mock_request.state.context = mock_context

        results = [_extract_tenant_id(mock_request) for _ in range(5)]

        assert all(r == results[0] for r in results)
        assert results[0] == str(tenant_uuid)
