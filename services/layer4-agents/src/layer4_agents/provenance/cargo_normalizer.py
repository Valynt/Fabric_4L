from __future__ import annotations

"""
Cargo Context Normalizer & Provenance Classifier.

Translates real Cargo tool responses into Fabric canonical domain entities with
strictly honest provenance (no manufactured upstream providers, synthetic confidence,
or fake timestamps).
"""

import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import yaml
from pydantic import ValidationError
import structlog

from value_fabric.shared.contracts.account_intelligence import (
    AccountSignal,
    CompanyCompetitor,
    CompanyEnrichmentData,
    CompanyResolutionResult,
    EnrichedAccountContext,
    ProvenanceClassification,
    SignalProvenance,
    StakeholderProfile,
)
from layer4_agents.provenance.cargo_schemas import (
    CargoRawCompetitor,
    CargoRawEnrichment,
    CargoRawSignal,
    CargoRawStakeholder,
)

logger = structlog.get_logger()

# Resolve path to heuristics config (services/layer4-agents/config/cargo_heuristics.yaml)
_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "config",
    "cargo_heuristics.yaml",
)

def _load_heuristics() -> dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("failed_to_load_cargo_heuristics", error=str(e))
        return {}

_HEURISTICS = _load_heuristics()


class CargoContextNormalizer:
    """Normalizes Cargo external GTM data into Fabric domain representations."""

    PROVIDER_NAME = "cargo"
    TECH_CATEGORY_MAP = _HEURISTICS.get("tech_category_map", {})
    PERSONA_RULES = _HEURISTICS.get("persona_rules", [])

    @classmethod
    def create_provenance(
        cls,
        upstream_provider: str | None = None,
        provider_record_id: str | None = None,
        source_url: str | None = None,
        confidence: float | None = None,
        classification: ProvenanceClassification = ProvenanceClassification.PARTIALLY_TRACEABLE,
        is_fallback: bool = False,
        fallback_reason: str | None = None,
    ) -> SignalProvenance:
        """Create an honest SignalProvenance record."""
        return SignalProvenance(
            provider=cls.PROVIDER_NAME,
            upstream_provider=upstream_provider,
            provider_record_id=provider_record_id,
            retrieved_at=datetime.now(UTC),
            source_url=source_url,
            confidence=confidence,
            classification=classification,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
        )

    @classmethod
    def normalize_company_resolution(
        cls,
        raw_data: dict[str, Any],
        fallback_name: str,
        fallback_domain: str,
    ) -> CompanyResolutionResult:
        """Normalize company resolution output."""
        try:
            raw = CargoRawEnrichment.model_validate(raw_data)
        except ValidationError:
            # Fallback to dict parsing if validation fails, or create default
            raw = CargoRawEnrichment(**raw_data)

        canonical_name = raw.name or fallback_name
        domain = raw.companyDomain or fallback_domain
        provider_id = raw.id or raw.uuid or f"cargo:{domain}"

        return CompanyResolutionResult(
            canonical_name=canonical_name,
            domain=domain,
            provider_company_id=str(provider_id),
            matched_via="domain" if domain else "name",
            provenance=cls.create_provenance(
                upstream_provider=raw.source,
                provider_record_id=str(provider_id),
                source_url=raw.linkedinUrl,
                classification=ProvenanceClassification.TRACEABLE if raw.linkedinUrl else ProvenanceClassification.PARTIALLY_TRACEABLE,
            ),
        )

    @classmethod
    def categorize_technologies(cls, tech_list: list[str]) -> dict[str, list[str]]:
        """Group detected technologies into functional categories."""
        categorized: dict[str, list[str]] = {}
        uncategorized: list[str] = []

        for tech in tech_list:
            normalized_tech = tech.lower().replace(" ", "_").replace(".", "_")
            matched = False
            for category, signatures in cls.TECH_CATEGORY_MAP.items():
                if any(sig in normalized_tech for sig in signatures):
                    categorized.setdefault(category, []).append(tech)
                    matched = True
                    break
            if not matched:
                uncategorized.append(tech)

        if uncategorized:
            categorized["other"] = uncategorized
        return categorized

    @classmethod
    def normalize_competitors(cls, raw_competitors: list[dict[str, Any]]) -> list[CompanyCompetitor]:
        """Normalize competitors returned by Cargo."""
        competitors: list[CompanyCompetitor] = []
        for c in raw_competitors:
            try:
                raw = CargoRawCompetitor.model_validate(c)
            except ValidationError:
                continue

            if not raw.name:
                continue
            
            competitors.append(
                CompanyCompetitor(
                    name=raw.name,
                    domain=raw.domain,
                    linkedin_url=raw.linkedinUrl,
                    provenance=cls.create_provenance(
                        provider_record_id=f"comp:{raw.domain or raw.name}",
                        source_url=raw.linkedinUrl,
                        classification=ProvenanceClassification.TRACEABLE if raw.linkedinUrl else ProvenanceClassification.PARTIALLY_TRACEABLE,
                    ),
                )
            )
        return competitors

    @classmethod
    def normalize_company_enrichment(
        cls,
        raw_data: dict[str, Any],
        domain: str,
        company_name: str | None = None,
        competitors: list[CompanyCompetitor] | None = None,
    ) -> CompanyEnrichmentData:
        """Normalize raw company firmographics from Cargo Enrich company tool."""
        try:
            raw = CargoRawEnrichment.model_validate(raw_data)
        except ValidationError:
            raw = CargoRawEnrichment(**raw_data)

        name = raw.name or company_name or domain.split(".")[0].capitalize()
        industry = raw.linkedinIndustry or raw.industry
        
        employee_count = raw.employeesCount or raw.employee_count
        if employee_count is not None:
            try:
                employee_count = int(employee_count)
            except (ValueError, TypeError):
                employee_count = None

        annual_revenue = raw.annual_revenue_usd or raw.revenue
        if annual_revenue is not None:
            try:
                annual_revenue = float(annual_revenue)
            except (ValueError, TypeError):
                annual_revenue = None

        raw_tech = raw.technologies or []
        if isinstance(raw_tech, list):
            tech_list = [str(t) for t in raw_tech]
            categorized_tech = cls.categorize_technologies(tech_list)
        elif isinstance(raw_tech, dict):
            tech_list = [item for sublist in raw_tech.values() if isinstance(sublist, list) for item in sublist]
            categorized_tech = raw_tech
        else:
            tech_list = []
            categorized_tech = {}

        provider_record_id = str(raw.id or raw.uuid or f"enrich:{domain}")
        
        founding_year = int(raw.foundedYear or raw.founding_year) if (raw.foundedYear or raw.founding_year) else None
        followers = int(raw.followersCount) if raw.followersCount else None

        return CompanyEnrichmentData(
            name=name,
            domain=domain,
            industry=industry,
            sub_industry=raw.sub_industry,
            employee_count=employee_count,
            employee_range=raw.employee_range,
            annual_revenue_usd=annual_revenue,
            headquarters_city=raw.city,
            headquarters_state=raw.state,
            headquarters_country=raw.country,
            postal_code=raw.postalCode,
            operating_locations=[loc for loc in [raw.city, raw.country] if loc],
            description=raw.description,
            linkedin_url=raw.linkedinUrl,
            crunchbase_url=raw.crunchbaseUrl,
            ownership_type=raw.ownership,
            founding_year=founding_year,
            followers_count=followers,
            technologies=tech_list,
            tech_stack_by_category=categorized_tech,
            competitors=competitors or [],
            provenance=cls.create_provenance(
                provider_record_id=provider_record_id,
                source_url=raw.linkedinUrl,
                classification=ProvenanceClassification.TRACEABLE if raw.linkedinUrl else ProvenanceClassification.PARTIALLY_TRACEABLE,
            ),
        )

    @classmethod
    def infer_stakeholder_persona(cls, job_title: str) -> tuple[str, str, str]:
        """Infer persona role, seniority level, and department from job title."""
        title_lower = job_title.lower()
        for rule in cls.PERSONA_RULES:
            keywords = rule.get("keywords", [])
            if any(kw in title_lower for kw in keywords):
                return rule.get("role", "Stakeholder"), rule.get("seniority", "Individual / Lead"), rule.get("department", "General")

        if "director" in title_lower:
            return "Director / Champion", "Director", "Management"
        if "manager" in title_lower or "lead" in title_lower:
            return "Operational Lead", "Manager", "Operations"
        return "Stakeholder", "Individual / Lead", "General"

    @classmethod
    def normalize_stakeholders(
        cls,
        raw_leads: list[dict[str, Any]],
        domain: str,
    ) -> list[StakeholderProfile]:
        """Normalize stakeholders returned from Cargo."""
        stakeholders: list[StakeholderProfile] = []

        for lead in raw_leads:
            try:
                raw = CargoRawStakeholder.model_validate(lead)
            except ValidationError:
                continue

            first_name = raw.firstName or raw.first_name or ""
            last_name = raw.lastName or raw.last_name or ""
            full_name = raw.full_name or f"{first_name} {last_name}".strip()
            if not full_name:
                continue

            job_title = raw.title or raw.job_title or "Unknown Title"
            persona_role, seniority, dept = cls.infer_stakeholder_persona(job_title)
            linkedin_url = raw.linkedinUrl or raw.profile_url

            # Ignore fake placeholder date "2001-01-01" from upstream provider
            joined_at = raw.joined_at
            recently_hired = False
            if joined_at and not joined_at.startswith("2001-01-01"):
                recently_hired = bool(raw.recently_hired)

            profile = StakeholderProfile(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                job_title=job_title,
                persona_role=persona_role,
                seniority_level=seniority,
                department=dept,
                linkedin_url=linkedin_url,
                work_email=raw.work_email or raw.email,
                about=raw.about,
                is_recently_hired=recently_hired,
                tenure_months=raw.tenure_months,
                provenance=cls.create_provenance(
                    provider_record_id=raw.companyLinkedinId or full_name,
                    source_url=linkedin_url,
                    classification=ProvenanceClassification.TRACEABLE if linkedin_url else ProvenanceClassification.PARTIALLY_TRACEABLE,
                ),
            )
            stakeholders.append(profile)

        return stakeholders

    @classmethod
    def normalize_signals(
        cls,
        raw_signals: list[dict[str, Any]],
        domain: str,
    ) -> list[AccountSignal]:
        """Normalize raw buying and business signals from Cargo."""
        signals: list[AccountSignal] = []

        for sig in raw_signals:
            try:
                raw = CargoRawSignal.model_validate(sig)
            except ValidationError:
                continue

            category = raw.category or raw.signal_category or "business"
            signal_type = raw.type or raw.signal_type or "signal"
            headline = raw.headline or raw.title or raw.description or "Detected Signal"
            
            confidence = raw.confidence
            try:
                confidence = float(confidence) if confidence is not None else None
            except (ValueError, TypeError):
                confidence = None

            signals.append(
                AccountSignal(
                    signal_category=category,
                    signal_type=signal_type,
                    headline=headline,
                    description=raw.description,
                    confidence=confidence,
                    detected_at=datetime.now(UTC),
                    metadata=raw.metadata or {},
                    provenance=cls.create_provenance(
                        upstream_provider=raw.source,
                        provider_record_id=str(raw.id or f"sig:{domain}:{signal_type}"),
                        confidence=confidence,
                        classification=ProvenanceClassification.TRACEABLE if raw.source_url else ProvenanceClassification.PARTIALLY_TRACEABLE,
                    ),
                )
            )

        return signals

    @classmethod
    def assemble_context(
        cls,
        company_data: CompanyEnrichmentData,
        stakeholders: list[StakeholderProfile],
        signals: list[AccountSignal],
        tenant_id: UUID,
        account_id: UUID | None = None,
        retrieval_path: str = "primary",
    ) -> EnrichedAccountContext:
        """Combine normalized domain entities into complete EnrichedAccountContext."""
        return EnrichedAccountContext(
            account_id=account_id,
            tenant_id=tenant_id,
            company=company_data,
            stakeholders=stakeholders,
            signals=signals,
            raw_provider_record_id=company_data.provenance.provider_record_id,
            retrieval_path=retrieval_path,
            assembled_at=datetime.now(UTC),
        )
