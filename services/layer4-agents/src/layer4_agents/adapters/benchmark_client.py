from __future__ import annotations

"""HTTP adapter for the Layer 6 Benchmark Service port."""

from decimal import Decimal
from typing import Any

import httpx

from ..integration._base import DEFAULT_CONNECTION_LIMITS
from ..interfaces.benchmark_client import (
    BenchmarkDataset,
    ComparisonRequest,
    ComparisonResult,
    IBenchmarkClient,
    RangeValidationRequest,
    RangeValidationResult,
)


class HTTPBenchmarkClient(IBenchmarkClient):
    """HTTP client for Layer 6 Benchmark Service.

    Production implementation communicating with standalone benchmark service
    on port 8006.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8006",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, limits=DEFAULT_CONNECTION_LIMITS)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_dataset(self, dataset_id: str) -> BenchmarkDataset | None:
        """Retrieve benchmark dataset by ID."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/v1/benchmarks/datasets/{dataset_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return BenchmarkDataset(**data)

    async def list_datasets(
        self,
        industry: str | None = None,
        segment: str | None = None,
    ) -> list[BenchmarkDataset]:
        """List available benchmark datasets."""
        client = await self._get_client()
        params: dict[str, Any] = {}
        if industry:
            params["industry"] = industry
        if segment:
            params["segment"] = segment

        response = await client.get(
            f"{self.base_url}/v1/benchmarks/datasets",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        # The L6 /v1/benchmarks/datasets endpoint returns a plain JSON array,
        # not a {"datasets": [...]} envelope.
        items = data if isinstance(data, list) else data.get("datasets", data)
        return [BenchmarkDataset(**item) for item in items]

    async def compare(self, request: ComparisonRequest) -> ComparisonResult:
        """Execute peer comparison."""
        client = await self._get_client()
        payload = {
            "dataset_id": request.dataset_id,
            "metric": request.metric,
            "company_value": str(request.company_value),
            "industry": request.industry,
            "segment": request.segment,
        }
        response = await client.post(
            f"{self.base_url}/v1/benchmarks/compare",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return ComparisonResult(
            percentile=data["percentile"],
            peer_median=Decimal(data["peer_median"]),
            peer_range=(Decimal(data["peer_range"][0]), Decimal(data["peer_range"][1])),
            sample_size=data["sample_size"],
            confidence=data["confidence"],
        )

    async def validate_range(
        self,
        request: RangeValidationRequest,
    ) -> RangeValidationResult:
        """Validate value against benchmark range."""
        client = await self._get_client()
        payload = {
            "dataset_id": request.dataset_id,
            "metric": request.metric,
            "value": str(request.value),
            "tolerance_percent": request.tolerance_percent,
        }
        response = await client.post(
            f"{self.base_url}/v1/benchmarks/validate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return RangeValidationResult(
            is_valid=data["is_valid"],
            expected_range=(Decimal(data["expected_range"][0]), Decimal(data["expected_range"][1])),
            actual_value=Decimal(data["actual_value"]),
            deviation_percent=data.get("deviation_percent"),
            severity=data["severity"],
        )
