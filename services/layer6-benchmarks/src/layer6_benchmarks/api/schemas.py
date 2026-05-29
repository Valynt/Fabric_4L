"""Pydantic request/response schemas for Layer 6 Benchmark API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    """Summary of benchmark dataset."""

    dataset_id: str
    name: str
    description: str
    industry: str
    segment: Optional[str]
    geography: Optional[str]
    metrics: List[str]
    metric_count: int
    version: str
    data_source: Optional[str]


class DatasetDetail(BaseModel):
    """Detailed benchmark dataset."""

    dataset_id: str
    name: str
    description: str
    industry: str
    segment: Optional[str]
    geography: Optional[str]
    metrics: Dict[str, dict]
    version: str
    data_source: Optional[str]


class ComparisonRequestPayload(BaseModel):
    """Payload for comparison request."""

    dataset_id: str
    metric: str
    company_value: str = Field(..., description="Company value as string (Decimal)")
    industry: str
    segment: Optional[str] = None


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
    deviation_percent: Optional[float]
    severity: str
    message: str


class DatasetUpsertPayload(BaseModel):
    dataset_id: str
    name: str
    description: str
    industry: str
    segment: Optional[str] = None
    geography: Optional[str] = None
    metrics: Dict[str, dict]
    version: str = "1.0.0"
    data_source: Optional[str] = None
    is_public: bool = False
    ownership_mode: str = "tenant"


class IndustriesResponse(BaseModel):
    """Response listing available industries."""

    industries: List[str]


class DatasetUpsertResponse(BaseModel):
    """Response from dataset upsert operation."""

    dataset_id: str
    ownership_mode: str
