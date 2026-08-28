"""L1 account-intelligence models.

These types are provider-agnostic. Do not add Cargo request/response models here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FetchRequest(BaseModel):
    tenant_id: UUID
    account_id: UUID
    slugs: list[str]
    client_request_id: str
    correlation_id: str
    manifest_id: str
    purpose: Literal["evaluation", "production"] = "evaluation"
    live_calls: bool = False
    cursor: str | None = None


class PageInfo(BaseModel):
    next_cursor: str | None = None
    truncated: bool = False


class RawSnapshot(BaseModel):
    snapshot_id: UUID
    tenant_id: UUID
    account_id: UUID
    provider: str
    slug: str
    fetched_at: datetime
    processing_region: str
    raw_payload_ref: str
    raw_payload_hash: str
    hash_alg: Literal["sha256+rfc8785"] = "sha256+rfc8785"
    source_record_id: str | None = None
    mock: bool = False


class RejectedPayload(BaseModel):
    slug: str
    reason_code: str
    message: str


class FetchBatch(BaseModel):
    tenant_id: UUID
    account_id: UUID
    provider: str
    content_state: Literal["full", "partial", "empty"]
    snapshots: list[RawSnapshot] = Field(default_factory=list)
    rejected: list[RejectedPayload] = Field(default_factory=list)
    page: PageInfo = Field(default_factory=PageInfo)
    replayed: bool = False


class ProviderHealth(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    latency_ms: int | None = None
    last_success: datetime | None = None
