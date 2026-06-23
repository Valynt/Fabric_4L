from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)

"""Tenant admin dashboard API routes.

Provides tenant administrators with:
- Usage metrics and daily breakdown
- Audit log access
- Tenant settings management (name, branding)
- Tier usage summary (current vs. limits)
- Top endpoint analytics

All endpoints require tenant_admin role and enforce tenant isolation
via RequestContext — a tenant admin can only see their own tenant's data.
Super admins can access any tenant by passing a different tenant_id.

Routes:
    GET  /v1/tenants/{tenant_id}/dashboard/usage       — Usage summary
    GET  /v1/tenants/{tenant_id}/dashboard/daily-usage  — Daily breakdown
    GET  /v1/tenants/{tenant_id}/dashboard/audit-log    — Audit log
    GET  /v1/tenants/{tenant_id}/dashboard/tier-usage   — Tier limits vs. current
    GET  /v1/tenants/{tenant_id}/dashboard/top-endpoints — Top API endpoints
    GET  /v1/tenants/{tenant_id}/settings               — Get settings
    PATCH /v1/tenants/{tenant_id}/settings              — Update settings
"""


import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin
from value_fabric.shared.models.typed_dict import TypedDictModel

from ....database import get_db_from_context
from ...tier_enforcement import TierEnforcement
from ...usage_tracking import UsageTrackingService


class get_tenant_usageResult(TypedDictModel):
    agent_executions: dict[str, Any]
    api_calls: dict[str, Any]
    llm_usage: dict[str, Any]
    period: dict[str, Any]
    tenant_id: Any
    users: dict[str, Any]

class get_daily_usageResult(TypedDictModel):
    data: Any
    days: Any
    tenant_id: Any

class get_tier_usageResult(TypedDictModel):
    """Response for tier usage endpoint."""
    tier_id: str
    limits: dict[str, Any]
    current: dict[str, Any]
    utilization: dict[str, Any]

class get_top_endpointsResult(TypedDictModel):
    days: Any
    endpoints: Any
    tenant_id: Any

class get_tenant_audit_logResult(TypedDictModel):
    events: Any
    limit: Any
    offset: Any
    tenant_id: Any
    total: Any

class get_tenant_settingsResult(TypedDictModel):
    created_at: Any
    id: Any
    name: Any
    settings: dict[str, Any]
    slug: Any
    status: Any
    tier_id: Any
    updated_at: Any

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tenant Admin Dashboard"])


# ── Request / Response Models ───────────────────────────────────────


class TenantSettingsUpdate(BaseModel):
    """Request body for updating tenant settings."""

    name: str | None = Field(None, description="Tenant display name")
    branding: dict[str, Any] | None = Field(
        None,
        description="Branding settings (logo_url, primary_color, etc.)",
    )
    notification_preferences: dict[str, Any] | None = Field(
        None,
        description="Notification preferences",
    )


# ── Authorization Helper ────────────────────────────────────────────


def _authorize_tenant_access(
    context: RequestContext,
    tenant_id: UUID,
) -> None:
    """Ensure the caller has access to the requested tenant.

    Tenant admins can only access their own tenant.
    Super admins can access any tenant.
    """
    caller_tenant = context.tenant_id
    is_super = getattr(context, "is_super_admin", lambda: False)
    if callable(is_super):
        is_super = is_super()

    if str(caller_tenant) != str(tenant_id) and not is_super:
        raise AuthorizationError(message = "Request failed", details = {
                "error": "access_denied",
                "message": "You can only access your own tenant's dashboard.",
            })


# ── Dashboard Endpoints ─────────────────────────────────────────────


@router.get("/{tenant_id}/dashboard/usage", response_model=get_tenant_usageResult)
async def get_tenant_usage(
    tenant_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to aggregate"),
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get aggregated usage metrics for the tenant.

    Returns API call counts, agent execution stats, LLM token usage,
    and active user count for the specified time window.
    """
    _authorize_tenant_access(context, tenant_id)

    service = UsageTrackingService(db)
    summary = await service.get_usage_summary(tenant_id, days)

    return get_tenant_usageResult.model_validate({
        "tenant_id": str(tenant_id),
        "period": {
            "start": summary.period_start.isoformat(),
            "end": summary.period_end.isoformat(),
            "days": days,
        },
        "api_calls": {
            "total": summary.api_calls_total,
            "by_endpoint": summary.api_calls_by_endpoint,
        },
        "agent_executions": {
            "total": summary.agent_executions,
            "total_time_ms": summary.agent_execution_time_ms,
            "by_type": summary.agent_executions_by_type,
        },
        "llm_usage": {
            "tokens_input": summary.llm_tokens_input,
            "tokens_output": summary.llm_tokens_output,
            "requests": summary.llm_requests,
            "cost_estimate_usd": round(summary.llm_cost_estimate_usd, 4),
        },
        "users": {
            "active": summary.active_users,
        },
    })


@router.get("/{tenant_id}/dashboard/daily-usage", response_model=get_daily_usageResult)
async def get_daily_usage(
    tenant_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get daily usage breakdown for charting.

    Returns one entry per day with api_calls, agent_executions,
    and llm_tokens.
    """
    _authorize_tenant_access(context, tenant_id)

    service = UsageTrackingService(db)
    daily = await service.get_daily_usage(tenant_id, days)

    return get_daily_usageResult.model_validate({
        "tenant_id": str(tenant_id),
        "days": days,
        "data": [
            {
                "date": d.date,
                "api_calls": d.api_calls,
                "agent_executions": d.agent_executions,
                "llm_tokens": d.llm_tokens,
            }
            for d in daily
        ],
    })


@router.get("/{tenant_id}/dashboard/tier-usage", response_model=get_tier_usageResult)
async def get_tier_usage(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get current resource usage vs. tier limits.

    Shows how close the tenant is to each limit, useful for
    upgrade prompts in the UI.
    """
    _authorize_tenant_access(context, tenant_id)

    # Get tenant's tier_id from the tenants table
    result = await db.execute(
        text("SELECT tier_id FROM tenants WHERE id = :id"),
        {"id": str(tenant_id)},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundError(message = "Tenant not found")

    tier_id = row[0] or "free"

    enforcer = TierEnforcement(db)
    usage_summary = await enforcer.get_usage_summary(tenant_id, tier_id)

    # Add monthly usage from tracking service
    tracker = UsageTrackingService(db)
    monthly_api_calls = await tracker.get_current_month_api_calls(tenant_id)
    monthly_llm_tokens = await tracker.get_current_month_llm_tokens(tenant_id)

    usage_summary["limits"]["monthly_api_calls"]["current"] = monthly_api_calls
    usage_summary["limits"]["monthly_llm_tokens"]["current"] = monthly_llm_tokens

    return usage_summary


@router.get("/{tenant_id}/dashboard/top-endpoints", response_model=get_top_endpointsResult)
async def get_top_endpoints(
    tenant_id: UUID,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get the most-called API endpoints for the tenant.

    Useful for understanding usage patterns and optimizing.
    """
    _authorize_tenant_access(context, tenant_id)

    service = UsageTrackingService(db)
    endpoints = await service.get_top_endpoints(tenant_id, days, limit)

    return get_top_endpointsResult.model_validate({
        "tenant_id": str(tenant_id),
        "days": days,
        "endpoints": endpoints,
    })


@router.get("/{tenant_id}/dashboard/audit-log", response_model=get_tenant_audit_logResult)
async def get_tenant_audit_log(
    tenant_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    action_filter: str | None = Query(None, description="Filter by action type"),
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get audit log entries for the tenant.

    Supports pagination and optional action type filtering.
    """
    _authorize_tenant_access(context, tenant_id)

    # Build query with optional filter
    params: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "limit": limit,
        "offset": offset,
    }

    where_clause = "WHERE tenant_id = :tenant_id"
    if action_filter:
        where_clause += " AND action = :action_filter"
        params["action_filter"] = action_filter

    query = text(f"""
        SELECT id, timestamp, action, outcome, actor_id,
               resource_type, resource_id, details
        FROM audit_events
        {where_clause}
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """)

    count_query = text(f"""
        SELECT COUNT(*)
        FROM audit_events
        {where_clause}
    """)

    try:
        result = await db.execute(query, params)
        rows = result.fetchall()

        count_result = await db.execute(count_query, params)
        total = count_result.scalar_one_or_none() or 0

        events = [
            {
                "id": str(row[0]),
                "timestamp": str(row[1]),
                "action": row[2],
                "outcome": row[3],
                "actor_id": str(row[4]) if row[4] else None,
                "resource_type": row[5],
                "resource_id": row[6],
                "details": row[7],
            }
            for row in rows
        ]
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning(
            "Failed to query audit log — table may not exist",
            exc_info=True,
        )
        events = []
        total = 0

    return get_tenant_audit_logResult.model_validate({
        "tenant_id": str(tenant_id),
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


# ── Settings Endpoints ──────────────────────────────────────────────


@router.get("/{tenant_id}/settings", response_model=get_tenant_settingsResult)
async def get_tenant_settings(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Get tenant settings and configuration."""
    _authorize_tenant_access(context, tenant_id)

    result = await db.execute(
        text("""
            SELECT id, name, slug, status, tier_id, settings,
                   created_at, updated_at
            FROM tenants
            WHERE id = :id
        """),
        {"id": str(tenant_id)},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundError(message = "Tenant not found")

    return get_tenant_settingsResult.model_validate({
        "id": str(row[0]),
        "name": row[1],
        "slug": row[2],
        "status": row[3],
        "tier_id": row[4],
        "settings": row[5] or {},
        "created_at": str(row[6]),
        "updated_at": str(row[7]),
    })


@router.patch("/{tenant_id}/settings", response_model=get_tenant_settingsResult)
async def update_tenant_settings(
    tenant_id: UUID,
    update: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Update tenant settings (tenant_admin only).

    Supports partial updates — only provided fields are changed.
    Branding changes require the custom_branding feature to be enabled.
    """
    _authorize_tenant_access(context, tenant_id)

    # Get current tenant
    result = await db.execute(
        text("SELECT tier_id, settings FROM tenants WHERE id = :id"),
        {"id": str(tenant_id)},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundError(message = "Tenant not found")

    tier_id = row[0] or "free"
    current_settings = row[1] or {}

    # Check branding feature if branding update requested
    if update.branding is not None:
        enforcer = TierEnforcement(db)
        enforcer.require_feature(tier_id, "custom_branding")

    # Build update
    updates: dict[str, Any] = {}
    if update.name is not None:
        updates["name"] = update.name
    if update.branding is not None:
        current_settings["branding"] = update.branding
        updates["settings"] = current_settings
    if update.notification_preferences is not None:
        current_settings["notifications"] = update.notification_preferences
        updates["settings"] = current_settings

    if not updates:
        raise ValidationError(message = "No fields to update")

    _allowed_tenant_update_fields = {"name", "settings"}

    # Build SET clause from allow-listed fields with bound parameters.
    set_parts = []
    params: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in _allowed_tenant_update_fields:
            raise HTTPException(status_code=400, detail=f"Cannot update field: {key}")
        if key == "settings":
            set_parts.append("settings = :settings::jsonb")
            params["settings"] = json.dumps(value)
        else:
            set_parts.append(f"{key} = :{key}")
            params[key] = value

    if not set_parts:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    params["id"] = str(tenant_id)
    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    await db.execute(
        text(f"UPDATE tenants SET {set_clause} WHERE id = :id"),
        params,
    )

    # Return updated tenant
    return await get_tenant_settings(tenant_id, db, context)
