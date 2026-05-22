"""Audit logs API routes backed by persisted audit events.

This endpoint exposes tenant-scoped audit records from the ``audit_events``
table. Provenance-only logs are intentionally not synthesized here; callers
receive an explicit 501 when requesting a source that has no production
integration in this service.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin

from ...database import get_db_from_context

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogEntry(BaseModel):
    """Single audit log entry."""

    id: str
    timestamp: str
    source: Literal["provenance", "access_log"]
    event_type: str
    entity_id: str | None = None
    entity_type: str | None = None
    action: str
    agent: str
    details: dict[str, Any]


class AuditLogResponse(BaseModel):
    """Audit log query response."""

    entries: list[AuditLogEntry]
    total: int
    page: int
    per_page: int


def _parse_iso_datetime(value: str | None, field_name: str) -> datetime | None:
    """Parse a query datetime value and return a helpful 400 on invalid input."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be an ISO-8601 datetime",
        ) from exc


def _coerce_details(raw_details: Any) -> dict[str, Any]:
    """Normalize JSON/JSONB audit details into the response model shape."""
    if raw_details is None:
        return {}
    if isinstance(raw_details, dict):
        return raw_details
    if isinstance(raw_details, str):
        try:
            parsed = json.loads(raw_details)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"value": raw_details}
    return {"value": raw_details}


def _actor_from_row(row: Any) -> str:
    """Return the principal identifier for an audit row without inventing one."""
    return str(row.user_id or row.api_key_id or "system")


@router.get("/logs", response_model=AuditLogResponse)
async def list_audit_logs(
    source: Literal["provenance", "access", "all"] | None = Query(None, description="Filter by log source"),
    from_date: str | None = Query(None, description="Start date (ISO format)"),
    to_date: str | None = Query(None, description="End date (ISO format)"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    event_type: str | None = Query(None, description="Filter by event type"),
    agent: str | None = Query(None, description="Filter by agent/user"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> AuditLogResponse:
    """Query tenant-scoped system audit events from durable storage.

    The route no longer returns a development-only empty stub. It queries the
    persisted ``audit_events`` table for the authenticated tenant, applies the
    documented filters, and maps the canonical audit fields to the existing
    response contract. Provenance graph audit retrieval is not available from
    this service, so explicit provenance-only requests fail closed with 501
    instead of returning incomplete or mock data.
    """
    if source == "provenance":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Provenance audit log retrieval is not implemented in Layer 4; query the provenance service directly.",
        )

    start = _parse_iso_datetime(from_date, "from_date")
    end = _parse_iso_datetime(to_date, "to_date")
    if start and end and start > end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="from_date must be before to_date")

    # WHERE clauses are composed from a fixed allowlist of (column_sql,
    # bind_name) pairs only — all caller-supplied values flow through
    # bind parameters, never string interpolation, so the composed
    # ``where_sql`` cannot carry attacker payload.
    _ALLOWED_CLAUSES: frozenset[str] = frozenset({
        "tenant_id = :tenant_id",
        "timestamp >= :from_date",
        "timestamp <= :to_date",
        "resource_type = :entity_type",
        "action = :event_type",
        "(user_id = :agent OR api_key_id = :agent)",
    })

    clauses: list[str] = ["tenant_id = :tenant_id"]
    params: dict[str, Any] = {
        "tenant_id": context.tenant_id,
        "limit": per_page,
        "offset": (page - 1) * per_page,
    }

    if start is not None:
        clauses.append("timestamp >= :from_date")
        params["from_date"] = start
    if end is not None:
        clauses.append("timestamp <= :to_date")
        params["to_date"] = end
    if entity_type:
        clauses.append("resource_type = :entity_type")
        params["entity_type"] = entity_type
    if event_type:
        clauses.append("action = :event_type")
        params["event_type"] = event_type
    if agent:
        clauses.append("(user_id = :agent OR api_key_id = :agent)")
        params["agent"] = agent

    # Defense in depth: assert every composed clause came from the allowlist
    # so a future edit cannot accidentally introduce an interpolated value.
    for clause in clauses:
        if clause not in _ALLOWED_CLAUSES:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error composing audit query",
            )

    where_sql = " AND ".join(clauses)
    total_result = await db.execute(
        text(f"SELECT COUNT(*) FROM audit_events WHERE {where_sql}"),
        params,
    )
    total = int(total_result.scalar() or 0)

    rows_result = await db.execute(
        text(
            f"""
            SELECT id, timestamp, action, resource_id, resource_type,
                   user_id, api_key_id, details
            FROM audit_events
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )

    entries = [
        AuditLogEntry(
            id=str(row.id),
            timestamp=row.timestamp.isoformat() if row.timestamp else "",
            source="access_log",
            event_type=str(row.action),
            entity_id=str(row.resource_id) if row.resource_id is not None else None,
            entity_type=str(row.resource_type) if row.resource_type is not None else None,
            action=str(row.action),
            agent=_actor_from_row(row),
            details=_coerce_details(row.details),
        )
        for row in rows_result.mappings().all()
    ]

    return AuditLogResponse(entries=entries, total=total, page=page, per_page=per_page)
