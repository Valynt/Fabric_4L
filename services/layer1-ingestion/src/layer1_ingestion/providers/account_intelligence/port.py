from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel


class FetchRequest(BaseModel):
    tenant_id: UUID
    account_id: UUID
    slugs: list[str]  # must be in allowlist.json
    correlation_id: str

class RawSnapshot(BaseModel):
    slug: str
    raw_payload: bytes  # hashed + stored immutably
    fetched_at: datetime
    provenance: dict  # minimal metadata only
    hash: str  # canonical_hash(raw_payload + slug + tenant)

class FetchBatch(BaseModel):
    snapshots: list[RawSnapshot]
    errors: list[dict] = []

class ProviderHealth(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    latency_ms: int
    last_success: datetime | None

class AccountIntelligenceProvider(Protocol):
    """Strict L1 port. L1 produces only immutable raw snapshots.
    Observation classification and economic meaning live in L2.
    """
    provider_name: Literal["cargo", "fake"]

    async def fetch(self, request: FetchRequest) -> FetchBatch:
        """Fetch raw snapshots for approved slugs only.
        Must respect tenant isolation, idempotency, and kill switch.
        """
        ...

    async def health(self, tenant_id: UUID) -> ProviderHealth:
        """Health check scoped to tenant."""
        ...
