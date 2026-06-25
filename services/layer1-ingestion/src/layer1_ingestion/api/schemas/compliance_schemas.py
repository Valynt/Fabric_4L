"""Pydantic schemas for compliance-related API operations."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ComplianceLogResponse(BaseModel):
    """Compliance log entry."""

    id: UUID
    event_type: str
    severity: str
    request_url: str
    request_timestamp: datetime
    response_action_taken: str | None
    response_reason: str | None
    created_at: datetime


class ComplianceSummaryResponse(BaseModel):
    """Compliance summary statistics."""

    period: dict[str, datetime]
    robots_txt_compliance: dict[str, int | None | dict[str, Any]]
    rate_limiting: dict[str, int | None | dict[str, Any]]
    pii_detection: dict[str, int]
    domain_policies: dict[str, int | None | dict[str, Any]]
