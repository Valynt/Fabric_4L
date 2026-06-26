from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.database import db
from app.models.usage_event import UsageEventRecord

if TYPE_CHECKING:
    from value_fabric.shared.identity.context import RequestContext


def record_usage(
    *,
    request,
    ctx: RequestContext,
    product_code: str,
    quantity: float = 1.0,
    unit: str = "request",
    metadata: dict | None = None,
) -> UsageEventRecord:
    """Persist a usage event for the current request.

    Callers should invoke this after auth succeeds and before returning the
    response so the event carries accurate tenant/api-key context.
    """
    event = UsageEventRecord(
        event_id=str(uuid.uuid4()),
        tenant_id=str(ctx.tenant_id),
        api_key_id=str(ctx.api_key_id) if ctx.api_key_id else None,
        endpoint=request.url.path,
        method=request.method,
        product_code=product_code,
        quantity=quantity,
        unit=unit,
        metadata=metadata or {},
    )
    db.usage_events.insert(event.event_id, event)
    return event


def list_usage_events(tenant_id: str, *, limit: int = 100) -> list[UsageEventRecord]:
    return db.usage_events.list(tenant_id=tenant_id, limit=limit)
