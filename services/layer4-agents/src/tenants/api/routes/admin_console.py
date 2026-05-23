"""Super admin cross-tenant console API routes.

Provides platform administrators with a read-only, paginated view across
all tenants including user and active workflow counts.

All endpoints require ``require_privileged_access`` which enforces:
- super_admin role
- X-Privileged-Reason header for audit trail
- automatic CROSS_TENANT_ACCESS audit event emission
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_privileged_access

from ....database import get_db_from_context

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Console"])


# ── Response Models ─────────────────────────────────────────────────


class TenantOverviewItem(BaseModel):
    """Single tenant entry in the cross-tenant overview."""

    id: str
    name: str
    slug: str
    status: str
    tier_id: str = Field(default="free")
    created_at: str
    user_count: int = Field(default=0, description="Total non-deleted users")
    active_workflow_count: int = Field(
        default=0, description="Harness runs in non-terminal status",
    )


class TenantOverviewResponse(BaseModel):
    """Paginated cross-tenant overview response."""

    items: list[TenantOverviewItem]
    total: int
    limit: int
    offset: int


# ── Endpoint ────────────────────────────────────────────────────────


@router.get("/tenant-overview", response_model=TenantOverviewResponse)
async def get_tenant_overview(
    limit: int = Query(100, ge=1, le=500, description="Number of tenants to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_from_context),
    _context: RequestContext = Depends(require_privileged_access()),
) -> TenantOverviewResponse:
    """Get a paginated cross-tenant overview.

    Returns tenant metadata along with user counts and active workflow
    counts per tenant. Requires ``super_admin`` role and an
    ``X-Privileged-Reason`` header.
    """
    # Explicitly clear the transaction-local tenant context so that
    # cross-tenant aggregation queries can operate across all tenant
    # rows (bypass is gated by the ``require_privileged_access``
    # dependency above and audit event emission).
    await db.execute(text("SELECT set_config('app.tenant_id', '', true)"))

    # Total count (unpaginated)
    count_result = await db.execute(text("SELECT COUNT(*) FROM tenants"))
    total = count_result.scalar_one_or_none() or 0

    # Main overview query with subqueries for user and workflow counts
    query = text("""
        SELECT
            t.id,
            t.name,
            t.slug,
            t.status,
            COALESCE(t.settings->>'tier_id', 'free') AS tier_id,
            t.created_at,
            COALESCE(u.user_count, 0) AS user_count,
            COALESCE(w.workflow_count, 0) AS active_workflow_count
        FROM tenants t
        LEFT JOIN (
            SELECT tenant_id::text AS tenant_id, COUNT(*) AS user_count
            FROM users
            WHERE status != 'deleted'
            GROUP BY tenant_id
        ) u ON u.tenant_id = t.id::text
        LEFT JOIN (
            SELECT tenant_id, COUNT(*) AS workflow_count
            FROM harness_runs
            WHERE status IN ('queued', 'running', 'waiting_for_human')
            GROUP BY tenant_id
        ) w ON w.tenant_id = t.id::text
        ORDER BY t.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    try:
        result = await db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()
    except Exception:
        logger.warning(
            "Failed to query tenant overview — tables may not exist",
            exc_info=True,
        )
        return TenantOverviewResponse(
            items=[], total=total, limit=limit, offset=offset,
        )

    items = [
        TenantOverviewItem(
            id=str(row[0]),
            name=row[1],
            slug=row[2],
            status=row[3],
            tier_id=row[4] or "free",
            created_at=str(row[5]),
            user_count=row[6] or 0,
            active_workflow_count=row[7] or 0,
        )
        for row in rows
    ]

    return TenantOverviewResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
