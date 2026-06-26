from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class APIKeyPermission(str):
    """Permission string allowed on an API key."""


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Literal["read_only", "analyst", "content_admin", "tenant_admin"] = "analyst"
    permissions: list[str] = Field(default_factory=list)


class APIKeyCreateResponse(BaseModel):
    key_id: str
    name: str
    api_key: str  # raw key shown exactly once
    prefix: str
    tenant_id: str
    role: str
    permissions: list[str]
    created_at: str


class APIKeyRecord(BaseModel):
    """Stored API key record (raw secret is never persisted)."""

    key_id: str
    tenant_id: str
    name: str
    key_hash: str
    prefix: str
    role: str
    permissions: list[str]
    enabled: bool = True
    revoked_at: str | None = None
    expires_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_used_at: str | None = None


class APIKeyListItem(BaseModel):
    key_id: str
    name: str
    prefix: str
    role: str
    permissions: list[str]
    enabled: bool
    created_at: str
    last_used_at: str | None


class APIKeyListResponse(BaseModel):
    items: list[APIKeyListItem]
