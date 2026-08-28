from __future__ import annotations

"""Layer 1 Ingestion API Client.

Provides hybrid integration where L4 ContextExtractionAgent
calls L1 APIs for document processing.
"""


import asyncio
import logging
import time
from typing import Any, Final

import httpx

from ._base import (
    SERVICE_AUTH_HEADER,  # noqa: F401  # re-exported for import compatibility
    TENANT_ID_HEADER,  # noqa: F401
    ServiceHttpClient,
)

logger = logging.getLogger(__name__)

# Job terminal states
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"completed", "failed", "cancelled"})


class Layer1IngestionClient(ServiceHttpClient):
    """Client for Layer 1 Ingestion API.

    Used by ContextExtractionAgent to:
    - Create ingestion jobs
    - Poll for completion
    - Retrieve extraction results
    - Create and execute website crawl targets

    Example:
        client = Layer1IngestionClient(
            base_url="http://layer1-ingestion:8000",
            api_key=os.getenv("LAYER1_API_KEY")
        )

        job = await client.create_job(
            target_url="https://example.com/doc.pdf",
            document_type="pdf"
        )

        result = await client.wait_for_completion(job["job_id"])
    """

    def __init__(
        self,
        base_url: str = "http://layer1-ingestion:8000",
        api_key: str | None = None,
        timeout: float = 30.0,
        tenant_id: str | None = None,
    ):
        """Initialize Layer 1 client.

        Args:
            base_url: Layer 1 API base URL
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

    def _require_tenant(
        self,
        tenant_id: str | None,
        *,
        operation: str,
        allow_system_call: bool = False,
        audit_reason: str | None = None,
    ) -> str:
        """Require tenant context for tenant-scoped operations."""
        effective_tenant = tenant_id or self._default_tenant_id
        if effective_tenant:
            return effective_tenant
        if allow_system_call and audit_reason:
            logger.warning("Privileged system call for %s: %s", operation, audit_reason)
            return ""
        raise Layer1ClientError(
            f"Missing tenant context for '{operation}'. Provide tenant_id or use privileged system-call path with audit reason."
        )

    async def create_job(
        self,
        target_url: str,
        document_type: str = "auto",
        tenant_id: str | None = None,
        extraction_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a document ingestion job.

        Args:
            target_url: URL of document to ingest
            document_type: Type of document (pdf, html, etc.)
            tenant_id: Tenant context
            extraction_config: Extraction configuration

        Returns:
            Job creation result with job_id
        """
        payload = {
            "target": {
                "url": target_url,
                "type": "http",
            },
            "document_type": document_type,
            "extraction_config": extraction_config
            or {
                "structured_data": True,
                "metadata": True,
            },
        }

        if tenant_id:
            payload["tenant_id"] = tenant_id

        try:
            response = await self.client.post(
                "/jobs",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to create ingestion job: {e}")
            raise Layer1ClientError(f"Failed to create job: {e}") from e

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get job status.

        Args:
            job_id: Job identifier

        Returns:
            Job status
        """
        try:
            response = await self.client.get(f"/jobs/{job_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get job status: {e}")
            raise Layer1ClientError(f"Failed to get status: {e}") from e

    async def wait_for_completion(
        self,
        job_id: str,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """Poll for job completion.

        Args:
            job_id: Job to wait for
            timeout: Maximum wait time
            poll_interval: Seconds between polls

        Returns:
            Completed job result
        """
        start_time = time.monotonic()

        while True:
            status = await self.get_job_status(job_id)

            job_status = status.get("status", "unknown")

            if job_status in TERMINAL_STATES:
                return status

            elapsed = time.monotonic() - start_time
            if elapsed > timeout:
                raise Layer1ClientError(f"Timeout waiting for job {job_id}")

            await asyncio.sleep(poll_interval)

    async def get_extraction_result(self, job_id: str) -> dict[str, Any]:
        """Get extraction result for completed job.

        Args:
            job_id: Completed job ID

        Returns:
            Extraction result
        """
        try:
            response = await self.client.get(f"/jobs/{job_id}/results")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get extraction result: {e}")
            raise Layer1ClientError(f"Failed to get result: {e}") from e

    # ========================================================================
    # Website Crawl Target APIs
    # ========================================================================

    async def create_website_target(
        self,
        url: str,
        name: str | None = None,
        tenant_id: str | None = None,
        extraction_config: dict[str, Any] | None = None,
        allow_system_call: bool = False,
        audit_reason: str | None = None,
    ) -> dict[str, Any]:
        """Create a scraping target for a website.

        Args:
            url: Website URL to crawl
            name: Human-readable name for the target
            tenant_id: Tenant context (uses default if not provided)
            extraction_config: Extraction configuration

        Returns:
            Created target details
        """
        payload: dict[str, Any] = {
            "name": name or f"Company knowledge crawl: {url}",
            "url": url,
            "target_type": "single_page",
            "source_category": "website",
            "crawl_path": "browser",
            "extraction_config": extraction_config
            or {
                "method": "ai_llm",
                "llm_provider": "openai",
                "max_depth": 2,
                "follow_links": True,
            },
            "browser_config": {
                "engine": "chromium",
                "headless": True,
                "javascript_enabled": True,
            },
            "tags": ["company-knowledge", "onboarding"],
        }
        effective_tenant = self._require_tenant(
            tenant_id,
            operation="create_website_target",
            allow_system_call=allow_system_call,
            audit_reason=audit_reason,
        )

        try:
            response = await self.client.post(
                "/targets",
                json=payload,
                headers=self._get_headers(effective_tenant or None),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to create website target: %s", e)
            raise Layer1ClientError(f"Failed to create target: {e}") from e

    async def execute_target(
        self,
        target_id: str,
        tenant_id: str | None = None,
        priority: int = 5,
        allow_system_call: bool = False,
        audit_reason: str | None = None,
    ) -> dict[str, Any]:
        """Trigger immediate execution of a scraping target.

        Args:
            target_id: Target identifier
            tenant_id: Tenant context
            priority: Execution priority (1-10)

        Returns:
            Execution response with job_id
        """
        payload = {"priority": priority}
        effective_tenant = self._require_tenant(
            tenant_id,
            operation="execute_target",
            allow_system_call=allow_system_call,
            audit_reason=audit_reason,
        )

        try:
            response = await self.client.post(
                f"/targets/{target_id}/execute",
                json=payload,
                headers=self._get_headers(effective_tenant or None),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to execute target: %s", e)
            raise Layer1ClientError(f"Failed to execute target: {e}") from e

    async def crawl_website(
        self,
        url: str,
        tenant_id: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to create and execute a website crawl target.

        Args:
            url: Website URL to crawl
            tenant_id: Tenant context
            name: Human-readable name

        Returns:
            Execution result with target_id and job_id
        """
        target = await self.create_website_target(
            url=url,
            name=name,
            tenant_id=tenant_id,
        )
        target_id = target.get("id")
        if not target_id:
            raise Layer1ClientError("Target creation response missing 'id'")

        execution = await self.execute_target(target_id, tenant_id=tenant_id)
        return {
            "target_id": target_id,
            **execution,
        }

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


class Layer1ClientError(Exception):
    """Error from Layer 1 client."""

    pass
