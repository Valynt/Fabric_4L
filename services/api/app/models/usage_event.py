from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class UsageEventRecord(BaseModel):
    event_id: str
    tenant_id: str
    api_key_id: str | None
    endpoint: str
    method: str
    product_code: str
    quantity: float = 1.0
    unit: str = "request"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict | None = None
