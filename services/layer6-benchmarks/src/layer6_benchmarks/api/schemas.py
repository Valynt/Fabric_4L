"""Pydantic request/response schemas for Layer 6 Benchmark API."""


from typing import Any

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    """Summary of benchmark dataset."""

    dataset_id: str
    name: str
    description: str
    industry: str
    segment: str | None
    geography: str | None
    metrics: list[str]
    metric_count: int
    version: str
    data_source: str | None


class DatasetDetail(BaseModel):
    """Detailed benchmark dataset."""

    dataset_id: str
    name: str
    description: str
    industry: str
    segment: str | None
    geography: str | None
    metrics: dict[str, dict]
    version: str
    data_source: str | None


class ComparisonRequestPayload(BaseModel):
    """Payload for comparison request."""

    dataset_id: str
    metric: str
    company_value: str = Field(..., description="Company value as string (Decimal)")
    industry: str
    segment: str | None = None


class ComparisonResponse(BaseModel):
    """Response from comparison."""

    percentile: int
    peer_median: str
    peer_range: tuple[str, str]
    sample_size: int
    confidence: str
    assessment: str


class ValidationRequestPayload(BaseModel):
    """Payload for validation request."""

    dataset_id: str
    metric: str
    value: str = Field(..., description="Value as string (Decimal)")
    tolerance_percent: int = 10


class ValidationResponse(BaseModel):
    """Response from validation."""

    is_valid: bool
    expected_range: tuple[str, str]
    actual_value: str
    deviation_percent: float | None
    severity: str
    message: str


class RecommendRangeRequestPayload(BaseModel):
    """Payload for GroundTruthAPI range recommendation."""

    dataset_id: str
    metric: str
    industry: str | None = None
    segment: str | None = None


class PercentileDistributionResponse(BaseModel):
    """Distribution envelope returned by GroundTruthAPI methods."""

    p10: str
    p25: str
    p50: str
    p75: str
    p90: str
    mean: str
    std_dev: str
    sample_size: int
    shape: str = "unknown"


class BenchmarkProvenanceResponse(BaseModel):
    """Provenance-safe benchmark source metadata."""

    metric: str
    dataset_id: str
    data_source: str | None
    source_count: int
    confidence: str
    confidence_score: float
    license_class: str = "unspecified"
    caveats: list[str] = []


class RecommendRangeResponse(BaseModel):
    """Response for recommendRange."""

    dataset_id: str
    metric: str
    industry: str
    segment: str | None
    unit: str
    distribution: PercentileDistributionResponse
    provenance: BenchmarkProvenanceResponse


class CompareDistributionRequestPayload(BaseModel):
    """Payload for compareAgainstDistribution."""

    dataset_id: str
    metric: str
    company_value: str = Field(..., description="Company value as string (Decimal)")
    industry: str | None = None
    segment: str | None = None


class CompareDistributionResponse(BaseModel):
    """Response for compareAgainstDistribution."""

    dataset_id: str
    metric: str
    company_value: str
    percentile: int
    variance_from_median_percent: float
    peer_median: str
    peer_range: tuple[str, str]
    sample_size: int
    confidence: str
    assessment: str
    distribution: PercentileDistributionResponse
    provenance: BenchmarkProvenanceResponse


class ValidateValueRequestPayload(BaseModel):
    """Payload for validateValue."""

    dataset_id: str
    metric: str
    value: str = Field(..., description="Value as string (Decimal)")
    tolerance_percent: int = 0


class ValidateValueResponse(BaseModel):
    """Response for validateValue."""

    dataset_id: str
    metric: str
    is_valid: bool
    expected_range: tuple[str, str]
    actual_value: str
    deviation_percent: float | None
    severity: str
    message: str
    distribution: PercentileDistributionResponse
    provenance: BenchmarkProvenanceResponse


class MetricCatalogItem(BaseModel):
    """Metric catalog entry independent from raw storage shape."""

    dataset_id: str
    metric: str
    display_name: str
    description: str
    industry: str
    segment: str | None
    geography: str | None
    unit: str
    sample_size: int
    confidence: str


class MetricCatalogResponse(BaseModel):
    """Response listing available benchmark metrics."""

    metrics: list[MetricCatalogItem]


class MetricProvenanceRequestPayload(BaseModel):
    """Payload for getMetricProvenance."""

    dataset_id: str
    metric: str


class CoverageCell(BaseModel):
    """Coverage status for a benchmark dimension cell."""

    industry: str
    metric_count: int
    status: str


class CoverageStatusResponse(BaseModel):
    """Response for benchmark coverage status."""

    total_metrics: int
    industries: list[CoverageCell]
    required_industries: list[str]
    missing_required_industries: list[str]


class VMRTValidationRequestPayload(BaseModel):
    """Payload for VMRT schema/linkage validation."""

    trace: dict[str, Any]
    min_quality_score: float = Field(default=3.5, ge=0, le=5)


class VMRTValidationResponse(BaseModel):
    """Response from VMRT validation."""

    is_valid: bool
    trace_id: str | None
    schema_version: str | None
    production_ready: bool
    quality_score_overall: str | None
    errors: list[str]


class VMRTTraceUpsertRequestPayload(BaseModel):
    """Payload for validating and persisting a VMRT trace."""

    trace: dict[str, Any]
    min_quality_score: float = Field(default=3.5, ge=0, le=5)
    status: str = Field(default="validated", pattern="^(draft|validated)$")


class VMRTTracePromotionRequestPayload(BaseModel):
    """Payload for promoting a VMRT trace to production-ready governance state."""

    reviewer: str = Field(min_length=1)
    min_quality_score: float = Field(default=3.5, ge=0, le=5)


class VMRTTraceRecordResponse(BaseModel):
    """Persisted VMRT trace metadata response."""

    trace_id: str
    schema_version: str
    status: str
    production_ready: bool
    quality_score_overall: str | None
    errors: list[str]
    reviewer: str | None = None
    created_at: str
    updated_at: str
    promoted_at: str | None = None
    trace: dict[str, Any] | None = None


class DatasetUpsertPayload(BaseModel):
    dataset_id: str
    name: str
    description: str
    industry: str
    segment: str | None = None
    geography: str | None = None
    metrics: dict[str, dict]
    version: str = "1.0.0"
    data_source: str | None = None
    is_public: bool = False
    ownership_mode: str = "tenant"


class IndustriesResponse(BaseModel):
    """Response listing available industries."""

    industries: list[str]


class DatasetUpsertResponse(BaseModel):
    """Response from dataset upsert operation."""

    dataset_id: str
    ownership_mode: str
