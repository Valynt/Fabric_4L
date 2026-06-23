from __future__ import annotations

"""Licensing Company Ontology Intake Skill.

Used when the goal is: "Build the ontology of the company selling/licensing
the product."  Produces a SourceCorpus that feeds Layer 2/3 for ontology
construction.  Does NOT finalize the ontology.
"""


from typing import Any

from .base import BaseSkill, SkillConfig

# JSON Schema for AI extraction stage — licensing company sources
_LICENSING_COMPANY_EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["discovered_themes", "candidate_capabilities", "source_evidence"],
    "properties": {
        "discovered_themes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "High-level business themes found across sources",
        },
        "candidate_capabilities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "evidence_sources"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "related_features": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "buyer_personas": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "pain_points_addressed": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "business_outcomes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "URLs or file names supporting this capability",
                    },
                },
            },
        },
        "source_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source_url", "source_type", "confidence"],
                "properties": {
                    "source_url": {"type": "string"},
                    "source_type": {
                        "type": "string",
                        "enum": [
                            "product_page",
                            "solution_page",
                            "industry_page",
                            "persona_page",
                            "case_study",
                            "docs",
                            "enablement_asset",
                            "whitepaper",
                            "pricing_page",
                        ],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "extracted_at": {"type": "string", "format": "date-time"},
                },
            },
        },
    },
}


class LicensingCompanyIntakeSkill(BaseSkill):
    """Skill for ingesting and packaging a licensing company's source corpus."""

    @classmethod
    def _default_config(cls) -> SkillConfig:
        return SkillConfig(
            skill_name="licensing_company_intake",
            objective=(
                "Build a provenance-backed source corpus for a licensing company ontology."
            ),
            target_entity_type="licensing_company",
            required_source_types=[
                "product_page",
                "solution_page",
                "industry_page",
                "persona_page",
                "case_study",
                "docs",
                "enablement_asset",
            ],
            output_contract="SourceCorpus",
            downstream_events=[
                "layer1.source_corpus.ready",
                "layer2.ontology_extraction.requested",
            ],
            extraction_schema=_LICENSING_COMPANY_EXTRACTION_SCHEMA,
        )

    def build_output(
        self,
        job: Any,
        raw_contents: list[Any],
        extracted_data: list[Any],
    ) -> dict[str, Any]:
        """Build a SourceCorpus from pipeline results."""
        tenant_id = str(job.tenant_id) if job.tenant_id else None
        config = job.configuration or {}
        company_name = config.get("company_name", "Unknown")
        company_id = config.get("company_id")

        # Aggregate source groups by type
        source_groups: dict[str, int] = {}
        for rc in raw_contents:
            src_type = rc.source_type if hasattr(rc, "source_type") else "unknown"
            source_groups[src_type] = source_groups.get(src_type, 0) + 1

        # Collect candidate concepts from extraction
        candidate_concepts: set[str] = set()
        source_evidence: list[dict] = []

        for ed in extracted_data:
            data = ed.data if hasattr(ed, "data") and ed.data else {}
            candidate_concepts.update(data.get("discovered_themes", []))
            for ev in data.get("source_evidence", []):
                source_evidence.append(
                    {
                        "url": ev.get("source_url", ""),
                        "source_type": ev.get("source_type", "unknown"),
                        "confidence": ev.get("confidence", "medium"),
                        "extracted_at": ev.get("extracted_at"),
                    }
                )

        return {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "company_name": company_name,
            "corpus_type": "licensing_company_ontology_seed",
            "source_groups": [
                {"source_type": k, "count": v} for k, v in source_groups.items()
            ],
            "candidate_concepts": sorted(candidate_concepts),
            "provenance": source_evidence,
            "extraction_status": "ready_for_extraction",
            "job_id": str(job.id),
        }
