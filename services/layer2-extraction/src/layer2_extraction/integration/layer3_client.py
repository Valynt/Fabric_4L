"""Layer 3 Knowledge Graph client for Layer 2 extraction pipeline."""

from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict


class IngestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    ingestion_id: str
    entities_loaded: int = 0
    relationships_loaded: int = 0
    message: str = ""
    error: str | None = None


class IngestionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_id: str
    status: str = "unknown"
    progress_percent: float = 0.0
    entities_processed: int = 0
    entities_total: int = 0
    error_message: str | None = None


class _CircuitBreaker:
    """Simple in-memory circuit breaker for Layer 3 health."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._failures = 0
        self._last_failure_time: float | None = None
        self._state = "closed"  # closed | open | half_open

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = "open"

    def can_attempt(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open" and self._last_failure_time is not None:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout_seconds:
                self._state = "half_open"
                return True
        return self._state == "half_open"


class Layer3KnowledgeClient:
    """Client for Layer 3 Knowledge Graph ingestion.

    Reuses a single ``httpx.AsyncClient`` for connection pooling (opt #6)
    and implements a circuit breaker + health-check caching (opt #4).
    """

    def __init__(
        self,
        base_url: str = "",
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url or "http://localhost:8003"
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        self._health_cache_ttl_seconds = 5.0
        self._last_health_check: float = 0.0
        self._last_health_result = False
        self._circuit = _CircuitBreaker()

    async def health_check(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and (now - self._last_health_check) < self._health_cache_ttl_seconds:
            return self._last_health_result

        if not self._circuit.can_attempt():
            self._last_health_result = False
            self._last_health_check = now
            return False

        try:
            response = await self._client.get(f"{self.base_url}/health", timeout=5.0)
            healthy = response.status_code == 200
        except Exception:
            healthy = False

        self._last_health_check = now
        self._last_health_result = healthy

        if healthy:
            self._circuit.record_success()
        else:
            self._circuit.record_failure()
        return healthy

    async def ingest_rdf_data(
        self,
        *,
        rdf_data: str,
        source_url: str,
        extraction_job_id: str,
        prompt_template_version: str | None = None,
        prompt_template_hash: str | None = None,
    ) -> IngestionResponse:
        if not await self.health_check():
            return IngestionResponse(
                success=False,
                ingestion_id=extraction_job_id,
                error="Layer 3 circuit breaker open or health check failed",
            )
        try:
            payload = {
                "rdf_data": rdf_data,
                "source_url": source_url,
                "extraction_job_id": extraction_job_id,
            }
            if prompt_template_version is not None:
                payload["prompt_template_version"] = prompt_template_version
            if prompt_template_hash is not None:
                payload["prompt_template_hash"] = prompt_template_hash
            response = await self._client.post(
                f"{self.base_url}/v1/ingest",
                json=payload,
                timeout=30.0,
            )
            data = response.json()
            self._circuit.record_success()
            return IngestionResponse(**data)
        except Exception:
            self._circuit.record_failure()
            return IngestionResponse(
                success=False,
                ingestion_id=extraction_job_id,
                error="layer3_client_error",
            )

    async def batch_ingest_rdf_data(
        self,
        items: list[dict[str, Any]],
    ) -> list[IngestionResponse]:
        """Ingest multiple RDF payloads concurrently.

        Each item must contain keys: ``rdf_data``, ``source_url``,
        ``extraction_job_id``.
        """
        if not items:
            return []
        if not await self.health_check():
            return [
                IngestionResponse(
                    success=False,
                    ingestion_id=item.get("extraction_job_id", ""),
                    error="Layer 3 circuit breaker open or health check failed",
                )
                for item in items
            ]
        try:
            response = await self._client.post(
                f"{self.base_url}/v1/ingest/batch",
                json={"items": items},
                timeout=60.0,
            )
            data = response.json()
            self._circuit.record_success()
            return [IngestionResponse(**r) for r in data.get("results", [])]
        except Exception:
            self._circuit.record_failure()
            return [
                IngestionResponse(
                    success=False,
                    ingestion_id=item.get("extraction_job_id", ""),
                    error="layer3_client_error",
                )
                for item in items
            ]

    async def get_ingestion_status(self, ingestion_id: str) -> IngestionStatus:
        try:
            response = await self._client.get(
                f"{self.base_url}/v1/ingest/{ingestion_id}/status",
                timeout=5.0,
            )
            data = response.json()
            return IngestionStatus(**data)
        except Exception:
            return IngestionStatus(
                ingestion_id=ingestion_id,
                status="error",
                error_message="layer3_client_error",
            )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
