"""Relationship models for Layer 2 extraction."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BenefitType(str, Enum):
    COST_REDUCTION = "cost_reduction"
    REVENUE_GROWTH = "revenue_growth"
    RISK_REDUCTION = "risk_reduction"
    EFFICIENCY_GAIN = "efficiency_gain"
    COMPLIANCE = "compliance"
    OTHER = "other"


class DriverType(str, Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    COMPLIANCE = "compliance"
    CUSTOMER = "customer"
    OTHER = "other"


class EnablementType(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    PREREQUISITE = "prerequisite"
    COMPLEMENTARY = "complementary"


class PredicateType(str, Enum):
    ENABLES = "enables"
    REQUIRES = "requires"
    PRODUCES = "produces"
    MEASURES = "measures"
    DEPENDS_ON = "depends_on"
    PART_OF = "part_of"
    ASSOCIATED_WITH = "associated_with"
    BENEFITS = "benefits"
    DRIVES = "drives"
    ALTERNATIVE_TO = "alternative_to"
    IMPLEMENTS = "implements"
    CAPABILITY_SUBTYPE_OF = "capability_subtype_of"
    SEMANTICALLY_EQUIVALENT = "semantically_equivalent"


class Relationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    subject_id: str = ""
    predicate: PredicateType = PredicateType.ASSOCIATED_WITH
    object_id: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    provenance: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)

    # Alias fields for test compatibility
    source_id: str = ""
    target_id: str = ""
    raw_predicate: str = ""
    canonical_predicate: PredicateType = PredicateType.ASSOCIATED_WITH
    evidence_text: str = ""
    source_url: str = ""
    extraction_job_id: str = ""
    tenant_id: str | None = None
    deterministic_id: str | None = None
    schema_version: str = "unknown"
    prompt_version: str = "unknown"
    model_version: str = "unknown"

    # Relationship property fields
    impact_level: Any | None = None
    strength: float | None = None
    enablement_type: Any | None = None
    contribution_weight: float | None = None
    driver_type: Any | None = None
    benefit_type: Any | None = None
    influence_weight: float | None = None

    @model_validator(mode="after")
    def _sync_alias_fields(self) -> Relationship:
        if self.source_id and not self.subject_id:
            self.subject_id = self.source_id
        if self.target_id and not self.object_id:
            self.object_id = self.target_id
        canonical_set = "canonical_predicate" in self.model_fields_set
        predicate_set = "predicate" in self.model_fields_set
        if canonical_set and not predicate_set:
            self.predicate = self.canonical_predicate
        elif predicate_set and not canonical_set:
            self.canonical_predicate = self.predicate
        if self.subject_id and not self.source_id:
            self.source_id = self.subject_id
        if self.object_id and not self.target_id:
            self.target_id = self.object_id
        return self

    @model_validator(mode="after")
    def _validate_not_empty(self) -> Relationship:
        if not self.source_id or not self.source_id.strip():
            raise ValueError("source_id cannot be empty")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("target_id cannot be empty")
        return self

    @model_validator(mode="after")
    def _validate_source_id_format(self) -> Relationship:
        if self.source_id:
            hyphen_count = self.source_id.count("-")
            if hyphen_count >= 2 and not re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                self.source_id,
                re.IGNORECASE,
            ):
                raise ValueError("source_id must be a valid UUID")
        return self

    def get_inverse(self) -> Relationship:
        return self.inverse()

    def inverse(self) -> Relationship:
        inverse_pred = {
            PredicateType.ENABLES: PredicateType.REQUIRES,
            PredicateType.REQUIRES: PredicateType.ENABLES,
            PredicateType.DEPENDS_ON: PredicateType.ENABLES,
            PredicateType.PRODUCES: PredicateType.MEASURES,
            PredicateType.MEASURES: PredicateType.PRODUCES,
            PredicateType.PART_OF: PredicateType.ASSOCIATED_WITH,
            PredicateType.BENEFITS: PredicateType.DRIVES,
            PredicateType.DRIVES: PredicateType.BENEFITS,
            PredicateType.ALTERNATIVE_TO: PredicateType.ALTERNATIVE_TO,
            PredicateType.IMPLEMENTS: PredicateType.CAPABILITY_SUBTYPE_OF,
            PredicateType.CAPABILITY_SUBTYPE_OF: PredicateType.IMPLEMENTS,
        }.get(self.predicate, self.predicate)
        return Relationship(
            id=f"{self.id}_inv" if self.id else "",
            subject_id=self.object_id,
            predicate=inverse_pred,
            object_id=self.subject_id,
            confidence=self.confidence,
            provenance=self.provenance,
            attributes=self.attributes.copy(),
            source_id=self.object_id,
            target_id=self.subject_id,
            canonical_predicate=inverse_pred,
        )

    @model_validator(mode="after")
    def _validate_relationship(self) -> Relationship:
        if self.subject_id and self.object_id and self.subject_id == self.object_id:
            raise ValueError("subject_id and object_id cannot be the same")
        return self


class RelationshipGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationships: list[Relationship] = Field(default_factory=list)

    def add(self, rel: Relationship) -> None:
        for existing in self.relationships:
            if (existing.source_id == rel.source_id and
                existing.target_id == rel.target_id and
                existing.predicate == rel.predicate):
                return
        self.relationships.append(rel)

    def add_relationship(self, rel: Relationship) -> None:
        self.add(rel)

    def get_by_subject(self, subject_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.subject_id == subject_id]

    def get_by_object(self, object_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.object_id == object_id]

    def get_by_predicate(self, predicate: PredicateType) -> list[Relationship]:
        return [r for r in self.relationships if r.predicate == predicate]

    def get_outgoing(self, entity_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.source_id == entity_id]

    def get_incoming(self, entity_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.target_id == entity_id]

    def to_dict(self) -> dict[str, Any]:
        return {"relationships": [r.model_dump() for r in self.relationships]}
