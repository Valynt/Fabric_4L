"""Pydantic schemas for ValueClaim API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from layer5_ground_truth.models.value_evidence_graph_enums import (
    ClaimStatus,
    ClaimType,
    Confidence,
)


class ValueClaimCreate(BaseModel):
    """Request body for creating a ValueClaim."""

    account_id: UUID
    statement: str = Field(..., min_length=1, max_length=2048)
    claim_type: ClaimType
    value_unit: str = Field(..., min_length=1, max_length=64)
    conservative_value: Decimal
    expected_value: Decimal
    aggressive_value: Decimal
    confidence: Confidence
    status: ClaimStatus | None = Field(default=ClaimStatus.DRAFT)
    case_id: UUID | None = None
    truth_object_id: UUID | None = None

    @field_validator(
        "conservative_value", "expected_value", "aggressive_value", mode="before"
    )
    @classmethod
    def coerce_numeric(cls, v: object) -> Decimal:
        return Decimal(v)  # type: ignore[arg-type]

    @field_validator("statement")
    @classmethod
    def statement_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("statement must not be blank")
        return v


class ValueClaimStatusTransition(BaseModel):
    """Request body for transitioning a ValueClaim status."""

    status: ClaimStatus


class ValueClaimResponse(BaseModel):
    """Full ValueClaim representation in API responses."""

    id: UUID
    tenant_id: UUID
    account_id: UUID
    case_id: UUID | None = None
    statement: str
    claim_type: str
    value_unit: str
    conservative_value: Decimal
    expected_value: Decimal
    aggressive_value: Decimal
    confidence: str
    status: str
    maturity_level: int
    created_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime
    truth_object_id: UUID | None = None

    model_config = {"from_attributes": True}


class ValueClaimSummary(BaseModel):
    """Compact ValueClaim representation for list responses."""

    id: UUID
    account_id: UUID
    statement: str
    claim_type: str
    value_unit: str
    expected_value: Decimal
    confidence: str
    status: str
    maturity_level: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ValueClaimListResponse(BaseModel):
    """Paginated list response for ValueClaims."""

    items: list[ValueClaimSummary]
    total: int
    limit: int
    offset: int
    has_more: bool
