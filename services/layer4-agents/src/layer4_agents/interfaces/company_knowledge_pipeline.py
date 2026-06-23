from __future__ import annotations

"""Ports for company knowledge cross-layer pipeline operations."""

from typing import Any, Protocol


class CompanyKnowledgePipelinePort(Protocol):
    """Tenant-scoped pipeline operations required by company knowledge onboarding."""

    async def crawl_website(
        self,
        *,
        tenant_id: str,
        url: str,
        name: str,
    ) -> dict[str, Any]:
        """Trigger a Layer 1 website crawl."""

    async def extract_value_attributes(
        self,
        *,
        tenant_id: str,
        content_id: str,
        source_url: str,
        markdown_content: str,
    ) -> dict[str, Any]:
        """Trigger Layer 2 value attribute extraction."""

    async def ingest_profile(
        self,
        *,
        tenant_id: str,
        ingestion_payload: dict[str, Any],
        passthrough_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ingest a company profile payload into Layer 3."""
