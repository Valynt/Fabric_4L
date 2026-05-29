from __future__ import annotations

"""Benchmark Service client interface for Layer 4 Agents.

Provides clean extension point for Layer 6 Benchmark Service integration.
Uses REST API contracts for cross-service operations.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx


@dataclass
class BenchmarkDataset:
    """Benchmark dataset reference."""

    id: str
    name: str
    industry: str
    segment: str | None
    metrics: list[str]  # e.g., ["revenue", "efficiency", "cost"]
    statistical_profile: dict[str, Any]  # p10, p50, p90, etc.


@dataclass
class ComparisonRequest:
    """Request for peer comparison."""

    dataset_id: str
    metric: str
    company_value: Decimal
    industry: str
    segment: str | None = None


@dataclass
class ComparisonResult:
    """Result of peer comparison."""

    percentile: int  # 0-100
    peer_median: Decimal
    peer_range: tuple[Decimal, Decimal]  # (p10, p90)
    sample_size: int
    confidence: str  # high, medium, low


@dataclass
class RangeValidationRequest:
    """Request for range validation."""

    dataset_id: str
    metric: str
    value: Decimal
    tolerance_percent: int = 10


@dataclass
class RangeValidationResult:
    """Result of range validation."""

    is_valid: bool
    expected_range: tuple[Decimal, Decimal]
    actual_value: Decimal
    deviation_percent: float | None
    severity: str  # info, warning, error


class IBenchmarkClient(ABC):
    """Abstract interface for benchmark service client.

    Implementation can be:
    - HTTP client for standalone L6 service (production)
    - In-memory mock for testing
    - Direct class instance for in-process usage
    """

    @abstractmethod
    async def get_dataset(self, dataset_id: str) -> BenchmarkDataset | None:
        """Retrieve benchmark dataset by ID."""
        pass

    @abstractmethod
    async def list_datasets(
        self,
        industry: str | None = None,
        segment: str | None = None,
    ) -> list[BenchmarkDataset]:
        """List available benchmark datasets."""
        pass

    @abstractmethod
    async def compare(self, request: ComparisonRequest) -> ComparisonResult:
        """Execute peer comparison."""
        pass

    @abstractmethod
    async def validate_range(
        self,
        request: RangeValidationRequest,
    ) -> RangeValidationResult:
        """Validate value against benchmark range."""
        pass


class HTTPBenchmarkClient(IBenchmarkClient):
    """HTTP client for Layer 6 Benchmark Service.

    Production implementation communicating with standalone
    benchmark service on port 8006.
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
            self._client = httpx.AsyncClient(timeout=self.timeout)
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
        return [BenchmarkDataset(**item) for item in data["datasets"]]

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
