"""Operational signal extraction models."""

from __future__ import annotations

from enum import StrEnum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationalSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: str
    source_text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SignalExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[OperationalSignal] = Field(default_factory=list)
    source_url: str = ""
    extraction_cost_usd: float = 0.0


class ExtractionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    extraction_version: str = ""


class OperationalSignalExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signals: list[OperationalSignal] = Field(default_factory=list)
    metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)
    source_url: str = ""
    tenant_id: str = ""


class SignalReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class SignalReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewed_by: str = Field(min_length=1)


class ReviewedSignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    tenant_id: str
    account_id: str
    value_pack_id: str
    extraction_job_id: str
    signal_type: str
    source_text: str = ""
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_links: list[str] = Field(default_factory=list)
    review_status: SignalReviewStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
