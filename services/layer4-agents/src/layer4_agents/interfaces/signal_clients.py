from __future__ import annotations

"""Ports used by the signal-detection agent for cross-layer calls."""

from typing import Any, Protocol


class SignalExtractionPort(Protocol):
    """Layer 2 signal extraction operations required by SignalDetectionAgent."""

    async def extract_operational_signals(
        self,
        *,
        prospect_data: dict[str, Any],
        trace_id: str | None,
    ) -> dict[str, Any]:
        """Extract operational signals from prospect setup data."""


class SignalKnowledgePort(Protocol):
    """Layer 3 knowledge operations required by SignalDetectionAgent."""

    async def find_matching_evidence(
        self,
        *,
        signal_description: str,
        industry: str | None = None,
        limit: int = 5,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find evidence that matches a signal."""

    async def quantify_signal(
        self,
        *,
        signal_name: str,
        signal_description: str,
        impact_indicators: list[str],
        industry: str | None,
        prospect_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Quantify signal impact."""

    async def persist_signal(
        self,
        *,
        signal_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> str:
        """Persist a signal to the knowledge graph."""

    async def link_evidence(
        self,
        *,
        signal_id: str,
        evidence_matches: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> int:
        """Link persisted evidence to a signal."""

    async def get_signals_for_account(
        self,
        *,
        account_id: str,
        tenant_id: str,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return signals for an account."""
