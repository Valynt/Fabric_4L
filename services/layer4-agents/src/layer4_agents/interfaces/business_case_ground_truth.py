from __future__ import annotations

"""Ports for business-case Ground Truth interactions."""

from collections.abc import Callable
from typing import Any, Protocol


class BusinessCaseGroundTruthPort(Protocol):
    """Tenant-scoped Ground Truth operations used by business-case workflows."""

    async def list_truths(
        self,
        *,
        organization_id: str,
        claim_type: str | None = None,
        min_maturity: int | None = None,
        min_confidence: float | None = None,
        applies_to_opportunity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List matching TruthObjects for the authenticated organization."""

    async def submit_truth(
        self,
        *,
        claim: str,
        claim_type: str,
        confidence: float,
        organization_id: str,
        applies_to: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        raw_extraction_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a promoted business-case claim to Ground Truth."""

    async def validate_claim(
        self,
        *,
        tenant_id: str,
        claim_id: str,
        claim_text: str,
        evidence_refs: list[Any],
        account_id: str | None = None,
        value_pack_id: str = "business_case",
    ) -> dict[str, Any]:
        """Validate a generated claim and return normalized validation data."""

    async def sync_validated_truths(self, *, organization_id: str) -> dict[str, Any]:
        """Sync validated TruthObjects to the knowledge graph."""

    async def close(self) -> None:
        """Release resources held by the port implementation."""


BusinessCaseGroundTruthClientFactory = Callable[[str], BusinessCaseGroundTruthPort | None]
