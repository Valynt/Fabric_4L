"""Compliance route handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.orm import Session
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..shared.database import get_db_from_context_sync
from ..shared.models import ComplianceEventType, ComplianceLog
from .dependencies import get_tenant_id
from .schemas.compliance_schemas import ComplianceSummaryResponse


class list_compliance_logsResult(TypedDictModel):
    items: Any
    limit: Any
    page: Any
    total: Any


async def list_compliance_logs(
    event_type: list[ComplianceEventType] | None = Query(None),
    severity: str | None = Query(None),
    domain: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    job_id: UUID | None = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Query compliance logs."""
    query = db.query(ComplianceLog).filter(ComplianceLog.tenant_id == org_id)

    if event_type:
        types = [t.value for t in event_type]
        query = query.filter(ComplianceLog.event_type.in_(types))

    if severity:
        query = query.filter(ComplianceLog.severity == severity)

    if domain:
        query = query.filter(ComplianceLog.request_url.contains(domain))

    if date_from:
        query = query.filter(ComplianceLog.created_at >= date_from)

    if date_to:
        query = query.filter(ComplianceLog.created_at <= date_to)

    if job_id:
        query = query.filter(ComplianceLog.job_id == job_id)

    total = query.count()
    offset = (page - 1) * limit
    logs = (
        query.order_by(ComplianceLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return list_compliance_logsResult.model_validate(
        {
            "items": [
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "severity": log.severity,
                    "request_url": log.request_url,
                    "request_timestamp": log.request_timestamp.isoformat(),
                    "response_action_taken": log.response_action_taken,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }
    )


async def get_compliance_summary(
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get compliance summary for organization."""
    query = db.query(ComplianceLog).filter(
        ComplianceLog.tenant_id == org_id,
        ComplianceLog.created_at >= period_start,
        ComplianceLog.created_at <= period_end,
    )

    total_logs = query.count()

    robots_checks = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value
    ).count()
    allowed = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value,
        ComplianceLog.robots_txt_check.isnot(None),
    ).count()

    rate_limits = query.filter(
        ComplianceLog.event_type == ComplianceEventType.RATE_LIMIT_APPLIED.value
    ).count()
    pii_detections = query.filter(
        ComplianceLog.event_type == ComplianceEventType.PII_DETECTED.value
    ).count()
    domain_blocks = query.filter(
        ComplianceLog.event_type == ComplianceEventType.DOMAIN_BLOCKED.value
    ).count()

    robots_logs = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value
    ).all()
    crawl_delays_respected = sum(
        1
        for log in robots_logs
        if (log.robots_txt_check or {}).get("crawl_delay") not in (None, 0)
    )

    rate_limit_logs = query.filter(
        ComplianceLog.event_type == ComplianceEventType.RATE_LIMIT_APPLIED.value
    ).all()
    delay_values = [
        (log.rate_limit_event or {}).get("delay_ms")
        for log in rate_limit_logs
        if isinstance((log.rate_limit_event or {}).get("delay_ms"), int)
    ]
    average_delay_ms = (
        int(sum(delay_values) / len(delay_values)) if delay_values else None
    )

    allowlisted_count = query.filter(
        ComplianceLog.event_type == ComplianceEventType.DOMAIN_ALLOWED.value
    ).count()

    return ComplianceSummaryResponse(
        period={"start": period_start, "end": period_end},
        robots_txt_compliance={
            "total_checks": robots_checks,
            "allowed": allowed,
            "blocked": robots_checks - allowed,
            "crawl_delays_respected": crawl_delays_respected,
        },
        rate_limiting={
            "total_requests": total_logs,
            "throttled_requests": rate_limits,
            "average_delay_ms": average_delay_ms,
            "average_delay_ms_metadata": {
                "status": "unknown" if average_delay_ms is None else "measured",
                "reason": (
                    "No delay_ms values found in compliance rate_limit_event logs"
                    if average_delay_ms is None
                    else None
                ),
            },
        },
        pii_detection={
            "scans_performed": total_logs,
            "detections": pii_detections,
            "redactions_applied": query.filter(
                ComplianceLog.event_type == ComplianceEventType.PII_REDACTED.value
            ).count(),
        },
        domain_policies={
            "allowlisted": allowlisted_count,
            "blocklisted": domain_blocks,
            "blocked_requests": domain_blocks,
        },
    )
