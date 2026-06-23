from __future__ import annotations

"""Ports for signal and evidence review operations."""

from typing import Any, Protocol


class SignalReviewPort(Protocol):
    """Review operations required by the signal API route."""

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
        """Persist signal review metadata."""

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
        """Persist evidence accept/reject decision metadata."""

    async def link_evidence_driver(
        self,
        *,
        evidence_id: str,
        driver_id: str,
        account_id: str,
        case_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Link evidence to a value driver."""
