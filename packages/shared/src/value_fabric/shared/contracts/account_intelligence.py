from __future__ import annotations

"""
Account Intelligence Domain Contract — Value Fabric Platform Shared Contract.

Defines the shared port abstraction for external account intelligence, enrichment,
stakeholder discovery, and buying signal acquisition across all Fabric layers (L1-L7).

Architectural Invariants:
1. Platform Contract: Owned by value_fabric.shared, consumable by L1, L2, L2.5, L4, and ValuePilot.
2. Zero Vendor Leakage: External DTOs are strictly isolated behind normalizers.
3. Honest Provenance: No manufactured upstream citations, fake URLs, or synthetic confidence.
4. Observable Degradation: Fallback events explicitly record attempted provider, failure reason,
   and retrieval path.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Provenance Classification
# ---------------------------------------------------------------------------


class ProvenanceClassification(str, Enum):
    """Classification of external fact reliability and traceability."""

    TRACEABLE = "TRACEABLE"  # Direct verified citation (e.g. SEC filing URL, verified company LinkedIn URL)
    PARTIALLY_TRACEABLE = "PARTIALLY_TRACEABLE"  # Aggregated by provider platform with observable entity match
    OPAQUE = "OPAQUE"  # Upstream source undisclosed by provider, or synthetic/unverified heuristic


class SignalProvenance(BaseModel):
    """Provenance metadata attached to every externally derived field or signal."""

    provider: str = Field(..., description="Provider adapter name (e.g. 'cargo', 'apollo', 'legacy_sec')")
    upstream_provider: str | None = Field(default=None, description="Original upstream source if explicitly disclosed")
    provider_record_id: str | None = Field(default=None, description="Original record ID in provider system")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Retrieval timestamp")
    source_url: str | None = Field(default=None, description="Direct URL to source record if disclosed by provider")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Provider-reported confidence if available")
    classification: ProvenanceClassification = Field(
        default=ProvenanceClassification.PARTIALLY_TRACEABLE,
        description="Traceability classification",
    )
    is_fallback: bool = Field(default=False, description="True if retrieved via fallback path")
    fallback_reason: str | None = Field(default=None, description="Reason for degradation/fallback if applicable")


# ---------------------------------------------------------------------------
# Domain Models (Strict Separation from Vendor Schemas)
# ---------------------------------------------------------------------------


class CompanyResolutionResult(BaseModel):
    """Normalized result of resolving an external entity identity."""

    canonical_name: str
    domain: str
    provider_company_id: str
    matched_via: str = "domain"
    provenance: SignalProvenance


class CompanyCompetitor(BaseModel):
    """Normalized competitor record."""

    name: str
    domain: str | None = None
    linkedin_url: str | None = None
    provenance: SignalProvenance


class CompanyEnrichmentData(BaseModel):
    """Normalized firmographics, workforce, and operational intelligence."""

    name: str
    domain: str
    industry: str | None = None
    sub_industry: str | None = None
    employee_count: int | None = None
    employee_range: str | None = None
    annual_revenue_usd: float | None = None
    headquarters_city: str | None = None
    headquarters_state: str | None = None
    headquarters_country: str | None = None
    postal_code: str | None = None
    operating_locations: list[str] = Field(default_factory=list)
    description: str | None = None
    linkedin_url: str | None = None
    crunchbase_url: str | None = None
    ownership_type: str | None = None
    founding_year: int | None = None
    followers_count: int | None = None
    technologies: list[str] = Field(default_factory=list)
    tech_stack_by_category: dict[str, list[str]] = Field(default_factory=dict)
    competitors: list[CompanyCompetitor] = Field(default_factory=list)
    provenance: SignalProvenance


class StakeholderProfile(BaseModel):
    """Normalized stakeholder profile for value selling."""

    first_name: str
    last_name: str
    full_name: str
    job_title: str
    persona_role: str = "Stakeholder"
    seniority_level: str = "Individual / Lead"
    department: str = "General"
    linkedin_url: str | None = None
    work_email: str | None = None
    about: str | None = None
    is_recently_hired: bool = False
    tenure_months: int | None = None
    provenance: SignalProvenance


class AccountSignal(BaseModel):
    """Normalized business, technology, workforce, or buying signal."""

    signal_category: str
    signal_type: str
    headline: str
    description: str | None = None
    confidence: float | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: SignalProvenance


class EnrichedAccountContext(BaseModel):
    """Complete aggregated account intelligence context."""

    account_id: UUID | None = None
    tenant_id: UUID
    company: CompanyEnrichmentData
    stakeholders: list[StakeholderProfile] = Field(default_factory=list)
    signals: list[AccountSignal] = Field(default_factory=list)
    raw_provider_record_id: str | None = None
    retrieval_path: str = "primary"  # "primary" | "fallback" | "degraded"
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Account Intelligence Provider Port
# ---------------------------------------------------------------------------


class AccountIntelligenceProvider(ABC):
    """Shared port for external Account Intelligence providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    async def resolve_company(
        self,
        name: str,
        domain: str,
        tenant_id: UUID,
    ) -> CompanyResolutionResult | None:
        """Resolve company identity."""
        pass

    @abstractmethod
    async def enrich_company(
        self,
        domain: str,
        company_name: str | None = None,
        tenant_id: UUID | None = None,
    ) -> CompanyEnrichmentData | None:
        """Retrieve firmographics and workforce data."""
        pass

    @abstractmethod
    async def discover_stakeholders(
        self,
        domain: str,
        company_name: str | None = None,
        persona_keywords: list[str] | None = None,
        limit: int = 25,
        tenant_id: UUID | None = None,
    ) -> list[StakeholderProfile]:
        """Discover key leadership and buying personas."""
        pass

    @abstractmethod
    async def get_company_signals(
        self,
        domain: str,
        company_name: str | None = None,
        tenant_id: UUID | None = None,
    ) -> list[AccountSignal]:
        """Acquire business, technology, and hiring signals."""
        pass

    @abstractmethod
    async def get_full_account_context(
        self,
        domain: str,
        company_name: str,
        tenant_id: UUID,
        account_id: UUID | None = None,
    ) -> EnrichedAccountContext | None:
        """Assemble full normalized account intelligence context."""
        pass
