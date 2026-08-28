from __future__ import annotations

"""Layer 2 Extraction API Client.

Provides hybrid integration where L4 ContextExtractionAgent
calls L2 APIs for financial document processing.
"""


import logging
from typing import Any

import httpx
from value_fabric.shared.observability.trace_context import CANONICAL_TRACE_HEADER

from ._base import (
    SERVICE_AUTH_HEADER,  # noqa: F401  # re-exported for import compatibility
    TENANT_ID_HEADER,  # noqa: F401
    ServiceHttpClient,
)

logger = logging.getLogger(__name__)


class Layer2ExtractionClient(ServiceHttpClient):
    """Client for Layer 2 Extraction Pipeline API.

    Used by ContextExtractionAgent to:
    - Extract from SEC filings
    - Transcribe earnings calls
    - Extract financial metrics
    - Extract value attributes from website content for company knowledge

    Example:
        client = Layer2ExtractionClient(
            base_url="http://layer2-extraction:8000"
        )

        filing = await client.extract_filing(
            url="https://sec.gov/.../10-k.pdf",
            filing_type="10-K",
            ticker="AAPL"
        )
    """

    def __init__(
        self,
        base_url: str = "http://layer2-extraction:8000",
        api_key: str | None = None,
        timeout: float = 60.0,
        tenant_id: str | None = None,
    ):
        """Initialize Layer 2 client.

        Args:
            base_url: Layer 2 API base URL
            api_key: API key for authentication
            timeout: Request timeout
            tenant_id: Default tenant ID for service-to-service calls
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            tenant_id=tenant_id,
        )
        self.client = self._build_client(headers=self.client_auth_headers(api_key))

    def _require_tenant(self, tenant_id: str | None, *, operation: str) -> str:
        effective_tenant = tenant_id or self._default_tenant_id
        if not effective_tenant:
            raise Layer2ClientError(
                f"Missing tenant context for '{operation}'. Provide tenant_id or set a default tenant in constructor."
            )
        return effective_tenant

    async def extract_filing(
        self,
        url: str,
        filing_type: str,
        ticker: str | None = None,
        extraction_prompts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Extract data from SEC filing.

        Args:
            url: URL of filing document
            filing_type: 10-K, 10-Q, 8-K, etc.
            ticker: Company ticker symbol
            extraction_prompts: Custom extraction prompts

        Returns:
            Extracted financial data
        """
        payload = {
            "document_url": url,
            "filing_type": filing_type,
            "extraction_type": "sec_filing",
        }

        if ticker:
            payload["ticker"] = ticker
        if extraction_prompts:
            payload["prompts"] = extraction_prompts

        try:
            response = await self.client.post(
                "/v1/extract",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to extract filing: {e}")
            raise Layer2ClientError(f"Failed to extract filing: {e}") from e

    async def transcribe_earnings_call(
        self,
        audio_url: str,
        company: str,
        quarter: str,
        year: int,
    ) -> dict[str, Any]:
        """Transcribe earnings call audio.

        Args:
            audio_url: URL of audio file
            company: Company name
            quarter: Quarter (Q1, Q2, Q3, Q4)
            year: Year

        Returns:
            Transcription result
        """
        payload = {
            "audio_url": audio_url,
            "company": company,
            "quarter": quarter,
            "year": year,
        }

        try:
            response = await self.client.post(
                "/v1/transcribe/earnings",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to transcribe earnings call: {e}")
            raise Layer2ClientError(f"Failed to transcribe: {e}") from e

    async def extract_financial_metrics(
        self,
        document_text: str,
        metrics: list[str] | None = None,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """Extract financial metrics from text.

        Args:
            document_text: Text to analyze
            metrics: Specific metrics to extract
            ticker: Company ticker for context

        Returns:
            Extracted metrics
        """
        payload = {
            "text": document_text,
            "extraction_type": "financial_metrics",
        }

        if metrics:
            payload["metrics"] = metrics
        if ticker:
            payload["ticker"] = ticker

        try:
            response = await self.client.post(
                "/v1/extract/metrics",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to extract metrics: {e}")
            raise Layer2ClientError(f"Failed to extract metrics: {e}") from e

    async def identify_risk_factors(
        self,
        document_text: str,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Identify risk factors from text.

        Args:
            document_text: Text to analyze
            categories: Risk categories to identify

        Returns:
            Identified risks
        """
        payload = {
            "text": document_text,
            "extraction_type": "risk_factors",
        }

        if categories:
            payload["categories"] = categories

        try:
            response = await self.client.post(
                "/v1/extract/risks",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to identify risks: {e}")
            raise Layer2ClientError(f"Failed to identify risks: {e}") from e

    async def extract_and_ingest(
        self,
        url: str,
        filing_type: str,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """Extract from filing and auto-ingest to knowledge graph.

        Args:
            url: URL of filing document
            filing_type: 10-K, 10-Q, 8-K, etc.
            ticker: Company ticker symbol

        Returns:
            Extraction and ingestion result
        """
        payload = {
            "document_url": url,
            "filing_type": filing_type,
            "extraction_type": "sec_filing",
            "auto_ingest": True,
        }

        if ticker:
            payload["ticker"] = ticker

        try:
            response = await self.client.post(
                "/v1/extract-and-ingest",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to extract and ingest: {e}")
            raise Layer2ClientError(f"Failed to extract and ingest: {e}") from e

    async def extract_operational_signals(
        self,
        prospect_data: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Extract operational pain signals from prospect setup data.

        Args:
            prospect_data: Prospect setup information including company details,
                         business pains, friction points, desired outcomes
            trace_id: Optional trace ID for observability

        Returns:
            Extraction result with signals list and metadata

        Note:
            Tenant context is automatically propagated via request-scoped context.
            Do NOT pass tenant_id as a parameter (CONTRACT.md §2.1).
        """
        payload = {
            "prospect_data": prospect_data,
            "extraction_type": "operational_signals",
            "category": "Operational",
        }

        headers = {}
        if trace_id:
            headers[CANONICAL_TRACE_HEADER] = trace_id
        # Tenant context propagated via client initialization, not headers
        # See shared.identity.context for AsyncLocalStorage-based propagation

        try:
            response = await self.client.post(
                "/v1/extract/signals",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to extract operational signals: {e}")
            raise Layer2ClientError(f"Failed to extract signals: {e}") from e

    async def extract_value_attributes(
        self,
        content_id: str,
        source_url: str,
        markdown_content: str,
        tenant_id: str | None = None,
        extraction_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract structured value attributes from website content.

        Calls Layer 2 /v1/extract-and-ingest to extract entities
        and auto-ingest them to the knowledge graph.

        Args:
            content_id: Layer 1 content identifier
            source_url: URL of source document
            markdown_content: Markdown content to extract from
            tenant_id: Tenant context
            extraction_config: Extraction configuration with entity_types,
                              confidence_threshold, chunk_size, etc.

        Returns:
            Extraction and ingestion result
        """
        payload: dict[str, Any] = {
            "content_id": content_id,
            "source_url": source_url,
            "markdown_content": markdown_content,
            "extraction_config": extraction_config
            or {
                "entity_types": [
                    "Capability",
                    "UseCase",
                    "Persona",
                    "ValueDriver",
                    "Product",
                    "Industry",
                ],
                "confidence_threshold": 0.7,
                "chunk_size": 4000,
                "chunk_overlap": 200,
            },
        }
        effective_tenant = self._require_tenant(tenant_id, operation="extract_value_attributes")

        try:
            response = await self.client.post(
                "/v1/extract-and-ingest",
                json=payload,
                headers=self._get_headers(effective_tenant),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to extract value attributes: %s", e)
            raise Layer2ClientError(f"Failed to extract value attributes: {e}") from e

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


class Layer2ClientError(Exception):
    """Error from Layer 2 client."""

    pass
