"""Canonical parameter manifest models for Fabric_4L v3.0.

A ParameterManifest defines the inputs, validation rules, and evidence
requirements for a business case or value summary. Every displayed fact,
recommendation, value driver, stakeholder, metric, benchmark, or business-case
parameter must be traceable to source evidence through a parameter manifest
entry.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ParameterType(str, Enum):
    """Allowed parameter value types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    CURRENCY = "currency"
    PERCENT = "percent"
    ENUM = "enum"


class ParameterStatus(str, Enum):
    """Lifecycle status of a parameter value."""

    EXTRACTED = "extracted"
    VALIDATED = "validated"
    OVERRIDE = "override"
    MISSING = "missing"
    CONTESTED = "contested"


class ParameterValidationRule(BaseModel):
    """Validation rule for a parameter value."""

    model_config = ConfigDict(from_attributes=True)

    rule_type: str = Field(..., description="e.g. range, regex, required, enum")
    config: dict = Field(default_factory=dict)
    error_message: Optional[str] = None


class ParameterEvidenceRequirement(BaseModel):
    """Evidence requirement for a parameter value."""

    model_config = ConfigDict(from_attributes=True)

    min_evidence_chunks: int = 0
    min_evidence_strength: str = "weak"
    allowed_source_types: Optional[list[str]] = None
    required_provenance_classes: Optional[list[str]] = None


class ParameterManifest(BaseModel):
    """A single input definition in the business-case parameter manifest."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID = Field(..., description="Owning tenant — always from authenticated context")
    account_id: UUID
    opportunity_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = None
    description: Optional[str] = None
    parameter_type: ParameterType
    required: bool = False
    default_value: Optional[dict] = None
    validation_rules: list[ParameterValidationRule] = Field(default_factory=list)
    evidence_requirement: Optional[ParameterEvidenceRequirement] = None
    override_allowed: bool = True
    created_at: datetime
    updated_at: datetime


class ParameterValue(BaseModel):
    """Concrete value for a parameter manifest entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_id: UUID
    parameter_id: UUID
    opportunity_id: Optional[UUID] = None
    value: Optional[dict] = None
    status: ParameterStatus = ParameterStatus.EXTRACTED
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    overridden_by: Optional[UUID] = None
    overridden_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ParameterManifestCreate(BaseModel):
    """Request body for creating a parameter manifest entry."""

    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    opportunity_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = None
    description: Optional[str] = None
    parameter_type: ParameterType
    required: bool = False
    default_value: Optional[dict] = None
    validation_rules: list[ParameterValidationRule] = Field(default_factory=list)
    evidence_requirement: Optional[ParameterEvidenceRequirement] = None
    override_allowed: bool = True


class ParameterValueCreate(BaseModel):
    """Request body for creating a parameter value."""

    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    parameter_id: UUID
    opportunity_id: Optional[UUID] = None
    value: Optional[dict] = None
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
