from __future__ import annotations

"""HTTP adapter for the Layer 6 Benchmark Service port."""

from decimal import Decimal
from typing import Any

import httpx

from ..interfaces.benchmark_client import (
    BenchmarkDataset,
    BenchmarkProvenance,
    CompareDistributionRequest,
    CompareDistributionResult,
    ComparisonRequest,
    ComparisonResult,
    IBenchmarkClient,
    PercentileDistribution,
    RangeValidationRequest,
    RangeValidationResult,
    RecommendRangeRequest,
    RecommendRangeResult,
    ValidateValueRequest,
    ValidateValueResult,
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
        return _dataset_from_payload(data)

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
        return [_dataset_from_payload(item) for item in data]

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

    async def recommend_range(self, request: RecommendRangeRequest) -> RecommendRangeResult:
        """Return the governed percentile envelope for a benchmark metric."""
        client = await self._get_client()
        payload = {
            "dataset_id": request.dataset_id,
            "metric": request.metric,
            "industry": request.industry,
            "segment": request.segment,
        }
        response = await client.post(
            f"{self.base_url}/v1/benchmarks/recommend-range",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return RecommendRangeResult(
            dataset_id=data["dataset_id"],
            metric=data["metric"],
            industry=data["industry"],
            segment=data.get("segment"),
            unit=data["unit"],
            distribution=_distribution_from_payload(data["distribution"]),
            provenance=_provenance_from_payload(data["provenance"]),
        )

    async def compare_distribution(
        self,
        request: CompareDistributionRequest,
    ) -> CompareDistributionResult:
        """Position a company value against the full peer distribution."""
        client = await self._get_client()
        payload = {
            "dataset_id": request.dataset_id,
            "metric": request.metric,
            "company_value": str(request.company_value),
            "industry": request.industry,
            "segment": request.segment,
        }
        response = await client.post(
            f"{self.base_url}/v1/benchmarks/compare-distribution",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return CompareDistributionResult(
            dataset_id=data["dataset_id"],
            metric=data["metric"],
            company_value=Decimal(data["company_value"]),
            percentile=data["percentile"],
            variance_from_median_percent=data["variance_from_median_percent"],
            peer_median=Decimal(data["peer_median"]),
            peer_range=(Decimal(data["peer_range"][0]), Decimal(data["peer_range"][1])),
            sample_size=data["sample_size"],
            confidence=data["confidence"],
            assessment=data["assessment"],
            distribution=_distribution_from_payload(data["distribution"]),
            provenance=_provenance_from_payload(data["provenance"]),
        )

    async def validate_value(self, request: ValidateValueRequest) -> ValidateValueResult:
        """Validate a quantitative claim against the governed p10-p90 range."""
        client = await self._get_client()
        payload = {
            "dataset_id": request.dataset_id,
            "metric": request.metric,
            "value": str(request.value),
            "tolerance_percent": request.tolerance_percent,
        }
        response = await client.post(
            f"{self.base_url}/v1/benchmarks/validate-value",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return ValidateValueResult(
            dataset_id=data["dataset_id"],
            metric=data["metric"],
            is_valid=data["is_valid"],
            expected_range=(Decimal(data["expected_range"][0]), Decimal(data["expected_range"][1])),
            actual_value=Decimal(data["actual_value"]),
            deviation_percent=data.get("deviation_percent"),
            severity=data["severity"],
            message=data["message"],
            distribution=_distribution_from_payload(data["distribution"]),
            provenance=_provenance_from_payload(data["provenance"]),
        )


def _distribution_from_payload(data: dict[str, Any]) -> PercentileDistribution:
    return PercentileDistribution(
        p10=Decimal(data["p10"]),
        p25=Decimal(data["p25"]),
        p50=Decimal(data["p50"]),
        p75=Decimal(data["p75"]),
        p90=Decimal(data["p90"]),
        mean=Decimal(data["mean"]),
        std_dev=Decimal(data["std_dev"]),
        sample_size=data["sample_size"],
        shape=data.get("shape", "unknown"),
    )


def _provenance_from_payload(data: dict[str, Any]) -> BenchmarkProvenance:
    return BenchmarkProvenance(
        metric=data["metric"],
        dataset_id=data["dataset_id"],
        data_source=data.get("data_source"),
        source_count=data["source_count"],
        confidence=data["confidence"],
        confidence_score=data["confidence_score"],
        license_class=data["license_class"],
        caveats=data.get("caveats", []),
    )


def _dataset_from_payload(data: dict[str, Any]) -> BenchmarkDataset:
    metrics = data.get("metrics", [])
    if isinstance(metrics, dict):
        metric_names = list(metrics.keys())
        statistical_profile = {
            name: metric.get("profile", {}) for name, metric in metrics.items()
        }
    else:
        metric_names = list(metrics)
        statistical_profile = {}

    return BenchmarkDataset(
        id=data["dataset_id"],
        name=data["name"],
        industry=data["industry"],
        segment=data.get("segment"),
        metrics=metric_names,
        statistical_profile=statistical_profile,
    )
