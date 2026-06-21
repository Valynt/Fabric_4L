from __future__ import annotations

"""Layer 3 adapter for signal and evidence review route operations."""

from typing import Any

from layer4_agents.integration.layer3_client import Layer3Client
from layer4_agents.interfaces.signal_review import SignalReviewPort


class Layer3SignalReviewAdapter(SignalReviewPort):
    """SignalReviewPort implementation backed by the Layer 3 API."""

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url

    async def review_signal(
        self,
        *,
        signal_id: str,
        account_id: str,
        review_status: str,
        reviewer_id: str,
        decision_note: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        async with Layer3Client(base_url=self._base_url) as client:
            return await client.review_signal(
                signal_id=signal_id,
                account_id=account_id,
                review_status=review_status,
                reviewer_id=reviewer_id,
                decision_note=decision_note,
                tenant_id=tenant_id,
            )

    async def decide_evidence(
        self,
        *,
        evidence_id: str,
        account_id: str,
        case_id: str,
        decision: str,
        reviewer_id: str,
        decision_note: str | None = None,
        tenant_id: str,
    ) -> dict[str, Any]:
        async with Layer3Client(base_url=self._base_url) as client:
            return await client.decide_evidence(
                evidence_id=evidence_id,
                account_id=account_id,
                case_id=case_id,
                decision=decision,
                reviewer_id=reviewer_id,
                decision_note=decision_note,
                tenant_id=tenant_id,
            )

    async def link_evidence_driver(
        self,
        *,
        evidence_id: str,
        driver_id: str,
        account_id: str,
        case_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        async with Layer3Client(base_url=self._base_url) as client:
            return await client.link_evidence_driver(
                evidence_id=evidence_id,
                driver_id=driver_id,
                account_id=account_id,
                case_id=case_id,
                tenant_id=tenant_id,
            )
