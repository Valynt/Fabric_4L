"""AccountIntelligenceProvider port.

Implementations return FetchBatch of RawSnapshot. They must not emit
Observation, EnrichedAccountContext, valueDriverTags, KPI, or ROI.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from layer1_ingestion.providers.account_intelligence.models import (
    FetchBatch,
    FetchRequest,
    ProviderHealth,
)


class AccountIntelligenceProvider(Protocol):
    provider_name: str

    async def fetch(self, request: FetchRequest) -> FetchBatch:
        """Fetch allowlisted slugs as immutable raw snapshots."""
        ...

    async def health(self, tenant_id: UUID) -> ProviderHealth:
        """Health check scoped to tenant."""
        ...
