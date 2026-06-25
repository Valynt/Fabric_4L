from __future__ import annotations

"""Benchmark Service client interface for Layer 4 Agents.

Provides clean extension point for Layer 6 Benchmark Service integration.
Uses REST API contracts for cross-service operations.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


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
class PercentileDistribution:
    """Distribution envelope returned by GroundTruthAPI."""

    p10: Decimal
    p25: Decimal
    p50: Decimal
    p75: Decimal
    p90: Decimal
    mean: Decimal
    std_dev: Decimal
    sample_size: int
    shape: str = "unknown"


@dataclass
class BenchmarkProvenance:
    """Provenance-safe benchmark source metadata."""

    metric: str
    dataset_id: str
    data_source: str | None
    source_count: int
    confidence: str
    confidence_score: float
    license_class: str
    caveats: list[str]


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


@dataclass
class RecommendRangeRequest:
    """Request for a benchmark percentile envelope."""

    dataset_id: str
    metric: str
    industry: str | None = None
    segment: str | None = None


@dataclass
class RecommendRangeResult:
    """Result for a benchmark percentile envelope."""

    dataset_id: str
    metric: str
    industry: str
    segment: str | None
    unit: str
    distribution: PercentileDistribution
    provenance: BenchmarkProvenance


@dataclass
class CompareDistributionRequest:
    """Request for full distribution comparison."""

    dataset_id: str
    metric: str
    company_value: Decimal
    industry: str | None = None
    segment: str | None = None


@dataclass
class CompareDistributionResult:
    """Result from compareAgainstDistribution."""

    dataset_id: str
    metric: str
    company_value: Decimal
    percentile: int
    variance_from_median_percent: float
    peer_median: Decimal
    peer_range: tuple[Decimal, Decimal]
    sample_size: int
    confidence: str
    assessment: str
    distribution: PercentileDistribution
    provenance: BenchmarkProvenance


@dataclass
class ValidateValueRequest:
    """Request for claim validation against a benchmark distribution."""

    dataset_id: str
    metric: str
    value: Decimal
    tolerance_percent: int = 0


@dataclass
class ValidateValueResult:
    """Result from validateValue."""

    dataset_id: str
    metric: str
    is_valid: bool
    expected_range: tuple[Decimal, Decimal]
    actual_value: Decimal
    deviation_percent: float | None
    severity: str
    message: str
    distribution: PercentileDistribution
    provenance: BenchmarkProvenance


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

    @abstractmethod
    async def recommend_range(self, request: RecommendRangeRequest) -> RecommendRangeResult:
        """Return the governed percentile envelope for a benchmark metric."""
        pass

    @abstractmethod
    async def compare_distribution(
        self,
        request: CompareDistributionRequest,
    ) -> CompareDistributionResult:
        """Position a company value against the full peer distribution."""
        pass

    @abstractmethod
    async def validate_value(self, request: ValidateValueRequest) -> ValidateValueResult:
        """Validate a quantitative claim against the governed p10-p90 range."""
        pass
