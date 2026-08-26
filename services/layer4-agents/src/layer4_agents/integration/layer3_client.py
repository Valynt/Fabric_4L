from __future__ import annotations

"""Layer 3 Knowledge Graph client with tenant propagation (Task 2.3).

Provides async HTTP client for Layer 3 Knowledge Graph API with automatic
tenant context injection for all queries.
"""
import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TENANT_ID_HEADER = "X-Tenant-ID"
SERVICE_AUTH_HEADER = "X-Service-Auth"


class Layer3ClientError(Exception):
    """Raised when Layer 3 API call fails."""

    pass


class Layer3Client:
    """Async client for Layer 3 Knowledge Graph API with tenant propagation.

    All methods automatically include tenant_id as X-Tenant-ID header
    to ensure RLS policies are enforced at Layer 3.

    Example:
        client = Layer3Client("http://layer3:8000")

        # Query with tenant context
        result = await client.query_graph(
            tenant_id="tenant-123",
            query="MATCH (n:Account) RETURN n LIMIT 10"
        )
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        tenant_id: str | None = None,
        max_retries: int = 3,
    ):
        """Initialize Layer 3 client.

        Args:
            base_url: Layer 3 API base URL
            timeout: Request timeout in seconds
            tenant_id: Default tenant ID for all requests
            max_retries: Max retry attempts for transient failures
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._default_tenant_id = tenant_id
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return self._client

    def _get_headers(self, tenant_id: str | None = None) -> dict[str, str]:
        """Build request headers with tenant context.

        Args:
            tenant_id: Tenant ID to include in headers (uses default if None)

        Returns:
            Headers dict with X-Tenant-ID if tenant_id available
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        effective_tenant = tenant_id or self._default_tenant_id
        if effective_tenant:
            headers[TENANT_ID_HEADER] = effective_tenant

        # F-1 P0 fix: Include service auth secret for mutual authentication
        service_auth = os.getenv("SERVICE_AUTH_SECRET")
        if service_auth:
            headers[SERVICE_AUTH_HEADER] = service_auth

        return headers

    def _get_effective_tenant(self, tenant_id: str | None) -> str:
        """Get effective tenant ID or raise error if not available.

        Args:
            tenant_id: Optional tenant ID override

        Returns:
            Effective tenant ID

        Raises:
            Layer3ClientError: If no tenant ID available
        """
        effective = tenant_id or self._default_tenant_id
        if not effective:
            raise Layer3ClientError(
                "Tenant ID required. Provide tenant_id parameter or set default in constructor."
            )
        return effective

    async def _make_request(
        self,
        method: str,
        url: str,
        tenant_id: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        allow_404: bool = False,
    ) -> dict[str, Any] | None:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            tenant_id: Tenant ID for headers
            json: Optional JSON body
            params: Optional query params
            allow_404: If True, return None on 404 instead of raising

        Returns:
            Response JSON or None if 404 and allow_404=True

        Raises:
            Layer3ClientError: On request failure
        """
        client = await self._get_client()
        headers = self._get_headers(tenant_id)

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                )

                if response.status_code == 404 and allow_404:
                    return None

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise Layer3ClientError(
                        f"Request failed: HTTP {e.response.status_code}"
                    )
                last_error = e
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                # Retry transient network errors
                last_error = e
            except asyncio.CancelledError:
                raise
            except Exception as e:
                raise Layer3ClientError(f"Request failed: {e}")

        raise Layer3ClientError(f"Request failed after {self._max_retries} attempts: {last_error}")

    async def query_graph(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute Cypher query against knowledge graph.

        Args:
            query: Cypher query string
            parameters: Query parameters
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Query results

        Raises:
            Layer3ClientError: If query fails
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/graph/query"
        payload = {
            "query": query,
            "parameters": parameters or {},
        }
        return await self._make_request("POST", url, effective_tenant, json=payload)

    async def get_subgraph(
        self,
        center_entity_id: str,
        depth: int = 2,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Get subgraph centered on an entity.

        Args:
            center_entity_id: Entity to center subgraph on
            depth: Traversal depth (1-3)
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Subgraph with nodes and edges
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/graph/subgraph"
        params = {
            "center_entity_id": center_entity_id,
            "depth": depth,
        }
        return await self._make_request("GET", url, effective_tenant, params=params)

    async def semantic_search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 10,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform semantic search across entities.

        Args:
            query: Search query text
            entity_types: Optional filter by entity types
            limit: Maximum results
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Search results
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/entities/search"
        payload: dict[str, Any] = {
            "query": query,
            "limit": limit,
        }
        if entity_types:
            payload["entity_types"] = entity_types

        result = await self._make_request("POST", url, effective_tenant, json=payload)
        return result or {}

    async def get_entity(
        self,
        entity_id: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get entity by ID.

        Args:
            entity_id: Entity identifier
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Entity data or None if not found
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/entities/{entity_id}"

        return await self._make_request("GET", url, effective_tenant, allow_404=True)

    async def persist_signal(
        self,
        signal_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> str:
        """Persist a pain signal to the knowledge graph.

        Args:
            signal_data: Signal data dictionary
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Signal ID
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/signals"

        result = await self._make_request("POST", url, effective_tenant, json=signal_data)
        return result.get("signal_id", "")

    async def find_matching_evidence(
        self,
        signal_description: str,
        industry: str | None,
        limit: int,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find evidence matching a signal description.

        Args:
            signal_description: Signal text to match
            industry: Optional industry filter
            limit: Maximum results
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            List of evidence matches
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/evidence/search"

        payload = {
            "description": signal_description,
            "industry": industry,
            "limit": limit,
        }

        result = await self._make_request("POST", url, effective_tenant, json=payload)
        return result.get("matches", [])

    async def quantify_signal(
        self,
        signal_name: str,
        signal_description: str,
        impact_indicators: list[str],
        industry: str | None,
        prospect_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Quantify signal impact using formulas.

        Args:
            signal_name: Signal name
            signal_description: Signal description
            impact_indicators: Impact clues
            industry: Industry vertical
            prospect_data: Prospect data for variables
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Quantification result
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/signals/quantify"

        payload = {
            "signal_name": signal_name,
            "signal_description": signal_description,
            "impact_indicators": impact_indicators,
            "industry": industry,
            "prospect_data": prospect_data,
        }

        return await self._make_request("POST", url, effective_tenant, json=payload) or {}

    async def link_evidence(
        self,
        signal_id: str,
        evidence_matches: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> int:
        """Link evidence to a signal.

        Args:
            signal_id: Target signal ID
            evidence_matches: List of evidence matches
            tenant_id: Tenant ID for RLS (uses default if None)

        Returns:
            Number of links created
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/signals/{signal_id}/evidence"

        payload = {"evidence_matches": evidence_matches}

        result = await self._make_request("POST", url, effective_tenant, json=payload)
        return result.get("links_created", 0)

    async def get_signals_for_account(
        self,
        account_id: str,
        tenant_id: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get signals for an account.

        Args:
            account_id: Account identifier
            tenant_id: Tenant ID for RLS (uses default if None)
            category: Optional category filter

        Returns:
            List of signal data
        """
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/accounts/{account_id}/signals"

        params = {}
        if category:
            params["category"] = category

        result = await self._make_request("GET", url, effective_tenant, params=params)
        return result.get("signals", [])

    async def get_benchmark_variables(
        self,
        industry: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch benchmark variable defaults from Layer 3 knowledge endpoints."""
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/knowledge/benchmarks/variables"
        return await self._make_request(
            "GET",
            url,
            effective_tenant,
            params={"industry": industry},
        ) or {}

    async def get_value_driver_formulas(
        self,
        driver_ids: list[str],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch value-driver formulas from Layer 3 knowledge endpoints."""
        if not driver_ids:
            raise ValueError("driver_ids must be non-empty")
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/knowledge/value-drivers/formulas"
        params = [("driver_ids", driver_id) for driver_id in driver_ids]
        return await self._make_request("GET", url, effective_tenant, params=params) or {}

    async def review_signal(
        self,
        signal_id: str,
        account_id: str,
        review_status: str,
        reviewer_id: str,
        decision_note: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Review a signal (approve/reject) with tenant/account scoping."""
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/signals/{signal_id}/review"
        payload: dict[str, Any] = {
            "account_id": account_id,
            "review_status": review_status,
            "reviewer_id": reviewer_id,
        }
        if decision_note:
            payload["decision_note"] = decision_note
        return await self._make_request("PATCH", url, effective_tenant, json=payload) or {}


    async def decide_evidence(
        self,
        evidence_id: str,
        account_id: str,
        case_id: str,
        decision: str,
        reviewer_id: str,
        decision_note: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/evidence/{evidence_id}/decision"
        payload: dict[str, Any] = {"account_id": account_id, "case_id": case_id, "decision": decision, "reviewer_id": reviewer_id}
        if decision_note:
            payload["decision_note"] = decision_note
        return await self._make_request("PATCH", url, effective_tenant, json=payload) or {}

    async def link_evidence_driver(
        self,
        evidence_id: str,
        driver_id: str,
        account_id: str,
        case_id: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        effective_tenant = self._get_effective_tenant(tenant_id)
        url = f"{self.base_url}/v1/evidence/{evidence_id}/drivers/{driver_id}"
        payload = {"account_id": account_id, "case_id": case_id}
        return await self._make_request("POST", url, effective_tenant, json=payload) or {}
    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Layer3Client:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
