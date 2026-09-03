"""Usage ingestion and query billing routes (Phase 1 extract from Layer 4).

Canonical implementation lives in Layer 7. Layer 4 now forwards to
these endpoints via thin HTTP client stubs.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ServiceUnavailableError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ... import repository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Billing — Usage"])


class UsageEventRequest(BaseModel):
    """Request body for ingesting a single usage event."""

    event_id: str = Field(..., min_length=1, max_length=128, description="Idempotency key")
    customer_id: str = Field(..., min_length=1, max_length=64, description="Customer identifier")
    event_name: str = Field(..., min_length=1, max_length=128, description="Logical event name")
    metric_name: str = Field(..., min_length=1, max_length=64, description="Metered metric name")
    quantity: float = Field(..., ge=0, description="Quantity to record")
    unit: str | None = Field(default=None, max_length=32, description="Unit of measure")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")


class UsageBatchRequest(BaseModel):
    """Request body for batch ingestion of usage events."""

    events: list[UsageEventRequest] = Field(
        ..., min_length=1, max_length=1000, description="Events to ingest"
    )


class UsageEventResponse(BaseModel):
    id: str
    event_id: str
    event_name: str
    metric_name: str
    quantity: float
    unit: str
    timestamp: str
    status: str
    metadata: dict[str, Any] | None = None


class UsageSummaryResponse(BaseModel):
    customer_id: str
    metric_name: str
    total_quantity: float
    event_count: int
    period_start: str | None = None
    period_end: str | None = None


class UsageSyncResponse(BaseModel):
    synced: int
    failed: int
    error: str | None = None


@router.post("/events")
async def ingest_usage_event(
    request: UsageEventRequest,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Ingest a single usage event for billing."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    event_dict = {
        "event_id": request.event_id,
        "metric": request.metric_name,
        "quantity": request.quantity,
        "source": request.event_name,
        "timestamp": request.timestamp.isoformat(),
        "request_id": request.event_id,
    }
    is_new = await repository.insert_usage_event(db, str(ctx.tenant_id), event_dict)
    if is_new:
        await repository.increment_aggregate(db, str(ctx.tenant_id), request.metric_name, request.quantity)

    status = "accepted" if is_new else "duplicate"
    logger.info(
        "ingest_usage_event",
        tenant_id=str(ctx.tenant_id),
        event_id=request.event_id,
        status=status,
    )
    return {
        "id": request.event_id,
        "event_id": request.event_id,
        "status": status,
        "tenant_id": str(ctx.tenant_id),
        "customer_id": request.customer_id,
        "metric_name": request.metric_name,
        "quantity": request.quantity,
        "timestamp": request.timestamp.isoformat(),
        "created_at": datetime.now().isoformat(),
    }


@router.post("/events/batch")
async def ingest_usage_batch(
    request: UsageBatchRequest,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Ingest multiple usage events in a batch."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    created = 0
    duplicates = 0
    error_details: list[dict[str, str]] = []

    for event in request.events:
        try:
            event_dict = {
                "event_id": event.event_id,
                "metric": event.metric_name,
                "quantity": event.quantity,
                "source": event.event_name,
                "timestamp": event.timestamp.isoformat(),
                "request_id": event.event_id,
            }
            is_new = await repository.insert_usage_event(db, str(ctx.tenant_id), event_dict)
            if is_new:
                await repository.increment_aggregate(
                    db, str(ctx.tenant_id), event.metric_name, event.quantity
                )
                created += 1
            else:
                duplicates += 1
        except Exception as exc:
            error_details.append({"event_id": event.event_id, "error": type(exc).__name__})

    logger.info(
        "ingest_usage_batch",
        tenant_id=str(ctx.tenant_id),
        created=created,
        duplicates=duplicates,
        errors=len(error_details),
    )
    return {
        "created": created,
        "duplicates": duplicates,
        "errors": len(error_details),
        "error_details": error_details or None,
    }


@router.get("/usage/{customer_id}/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    customer_id: str,
    metric_name: str = Query(..., min_length=1, max_length=64),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get aggregated usage summary for a customer and metric."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    aggregates = await repository.get_usage_aggregates(db, str(ctx.tenant_id))
    total = aggregates.get(metric_name, 0.0)

    return {
        "customer_id": customer_id,
        "metric_name": metric_name,
        "total_quantity": total,
        "event_count": 0,
    }


@router.get("/usage/{customer_id}/events", response_model=list[UsageEventResponse])
async def list_usage_events(
    customer_id: str,
    metric_name: str | None = Query(None),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[dict[str, Any]]:
    """List individual usage events for a customer."""
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")

    logger.info(
        "list_usage_events",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        metric_name=metric_name,
    )
    # Phase 1: Stub. Full implementation will query usage event repository.
    return []


@router.post("/usage/{customer_id}/sync", response_model=UsageSyncResponse)
async def sync_usage_to_stripe(
    customer_id: str,
    metric_name: str | None = Query(None),
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Sync pending usage events to Stripe MeterEvents."""
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    logger.info(
        "sync_usage_to_stripe",
        tenant_id=str(ctx.tenant_id),
        customer_id=customer_id,
        metric_name=metric_name,
    )
    # Phase 1: Stub.
    raise ServiceUnavailableError(message="Stripe MeterEvents sync not yet configured in L7")
