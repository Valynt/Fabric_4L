from __future__ import annotations

"""Ports used by ContextExtractionAgent for cross-layer context extraction."""

from typing import Any, Protocol


class ContextIngestionPort(Protocol):
    """Layer 1 ingestion operations available to ContextExtractionAgent."""


class ContextFinancialExtractionPort(Protocol):
    """Layer 2 financial extraction operations required by ContextExtractionAgent."""

    async def extract_filing(
        self,
        *,
        url: str,
        filing_type: str,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """Extract financial data from a filing."""
