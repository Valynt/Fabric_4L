"""Integration tests for admin audit journey.

Tests critical user journey: privileged action → audit event emission →
audit log pagination → export audit trail to CSV/JSON.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Request

from value_fabric.shared.audit.models import AuditAction, AuditOutcome, PrivilegedAccessDetails
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_privileged_access

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def super_admin_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        roles=["super_admin"],
        permissions=["all"],
        request_id="test-request-123",
    )


@pytest.fixture
def regular_user_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        roles=["user"],
        permissions=["read"],
        request_id="test-request-456",
    )


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.headers = {"X-Privileged-Reason": "Audit test"}
    request.url.path = "/v1/admin/tenant-overview"
    request.client.host = "127.0.0.1"
    return request


class TestAdminAuditJourney:
    """End-to-end admin audit assertions."""

    async def test_tenant_overview_returns_paginated_response(self):
        """GET /tenant-overview returns paginated TenantOverviewResponse."""
        from layer4_agents.tenants.api.routes.admin_console import (
            TenantOverviewResponse,
            get_tenant_overview,
        )

        mock_db = AsyncMock()
        # Mock set_config query (first execute)
        mock_set_config_result = MagicMock()
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one_or_none.return_value = 2
        # Mock rows query
        mock_rows_result = MagicMock()
        mock_rows_result.fetchall.return_value = [
            ("t1", "Tenant One", "tenant-one", "active", "free", "2024-01-01", 5, 2),
            ("t2", "Tenant Two", "tenant-two", "active", "growth", "2024-02-01", 12, 8),
        ]
        mock_db.execute.side_effect = [mock_set_config_result, mock_count_result, mock_rows_result]

        mock_context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            roles=["super_admin"],
            permissions=["all"],
            request_id="req-123",
        )

        response = await get_tenant_overview(limit=10, offset=0, db=mock_db, _context=mock_context)

        assert isinstance(response, TenantOverviewResponse)
        assert response.total == 2
        assert response.limit == 10
        assert response.offset == 0
        assert len(response.items) == 2
        assert response.items[0].slug == "tenant-one"
        assert response.items[1].tier_id == "growth"

    async def test_privileged_action_emits_cross_tenant_access_audit(self, mock_request, super_admin_context):
        """require_privileged_access emits CROSS_TENANT_ACCESS audit event."""
        dependency = require_privileged_access()

        with patch(
            "value_fabric.shared.identity.dependencies.emit_audit_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await dependency(request=mock_request, context=super_admin_context)

        assert result == super_admin_context
        audit_calls = [
            c for c in mock_emit.call_args_list
            if c.kwargs.get("action") == AuditAction.CROSS_TENANT_ACCESS
        ]
        assert len(audit_calls) >= 1
        assert audit_calls[0].kwargs["outcome"] == AuditOutcome.SUCCESS

    async def test_audit_details_serialize_to_json(self):
        """PrivilegedAccessDetails can be serialized to JSON for export."""
        details = PrivilegedAccessDetails(
            accessed_tenant_ids={"tenant-a", "tenant-b"},
            resource_types=["cross_tenant_query"],
            session_duration_seconds=45.0,
            reason="Compliance review",
            approval_ticket="JIRA-SEC-42",
            query_count=2,
        )
        data = details.model_dump()
        assert data["reason"] == "Compliance review"
        assert data["approval_ticket"] == "JIRA-SEC-42"
        assert data["query_count"] == 2
        assert len(data["accessed_tenant_ids"]) == 2

    async def test_audit_details_serialize_to_csv_row(self):
        """PrivilegedAccessDetails can be flattened to a CSV-ready row."""
        details = PrivilegedAccessDetails(
            accessed_tenant_ids={"tenant-a"},
            resource_types=["cross_tenant_query"],
            session_duration_seconds=30.0,
            reason="Routine check",
            approval_ticket="TICKET-1",
            query_count=1,
        )
        data = details.model_dump()
        csv_row = {
            "reason": data["reason"],
            "ticket": data["approval_ticket"],
            "duration_sec": data["session_duration_seconds"],
            "tenants": "|".join(sorted(data["accessed_tenant_ids"])),
            "query_count": data["query_count"],
        }
        assert csv_row["tenants"] == "tenant-a"
        assert csv_row["query_count"] == 1

    async def test_non_super_admin_blocked(self, mock_request, regular_user_context):
        """Non-super-admin users are blocked from privileged access."""
        from fastapi import HTTPException

        dependency = require_privileged_access()

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, context=regular_user_context)

        assert exc_info.value.status_code == 403
