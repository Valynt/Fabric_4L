from __future__ import annotations

"""Prospect Research Skill.

Used when the goal is: "Research this account so we can understand likely pain,
initiatives, stakeholders, and value hypotheses."  Produces an
AccountIntelligencePacket that feeds Layer 2/4 for signal extraction and
value hypothesis generation.
"""


from typing import Any

from .base import BaseSkill, SkillConfig

# JSON Schema for AI extraction stage — prospect research
_PROSPECT_RESEARCH_EXTRACTION_SCHEMA = {
    "type": "object",
    "required": [
        "company_profile",
        "observed_signals",
        "likely_stakeholders",
        "source_evidence",
    ],
    "properties": {
        "company_profile": {
            "type": "object",
            "properties": {
                "size": {"type": "string"},
                "geography": {"type": "string"},
                "business_model": {"type": "string"},
                "industry": {"type": "string"},
            },
        },
        "observed_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["signal", "source", "confidence"],
                "properties": {
                    "signal": {"type": "string"},
                    "source": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "detail": {"type": "string"},
                },
            },
        },
        "strategic_initiatives": {
            "type": "array",
            "items": {"type": "string"},
        },
        "likely_pain_areas": {
            "type": "array",
            "items": {"type": "string"},
        },
        "likely_stakeholders": {
            "type": "array",
            "items": {"type": "string"},
        },
        "possible_value_hypotheses": {
            "type": "array",
            "items": {"type": "string"},
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
                            "website",
                            "about_page",
                            "leadership_page",
                            "careers_page",
                            "press_release",
                            "news",
                            "crm_note",
                            "call_transcript",
                            "annual_report",
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


class ProspectResearchSkill(BaseSkill):
    """Skill for researching a sales prospect and packaging account intelligence."""

    @classmethod
    def _default_config(cls) -> SkillConfig:
        return SkillConfig(
            skill_name="prospect_research",
            objective=(
                "Build an account intelligence packet for a sales prospect."
            ),
            target_entity_type="sales_prospect",
            required_source_types=[
                "website",
                "about_page",
                "leadership_page",
                "careers_page",
                "press_release",
                "news",
                "crm_note",
                "call_transcript",
            ],
            output_contract="AccountIntelligencePacket",
            downstream_events=[
                "layer1.account_intelligence.ready",
                "layer2.signal_extraction.requested",
            ],
            extraction_schema=_PROSPECT_RESEARCH_EXTRACTION_SCHEMA,
        )

    def build_output(
        self,
        job: Any,
        raw_contents: list[Any],
        extracted_data: list[Any],
    ) -> dict[str, Any]:
        """Build an AccountIntelligencePacket from pipeline results."""
        tenant_id = str(job.tenant_id) if job.tenant_id else None
        config = job.configuration or {}
        account_name = config.get("account_name", "Unknown")
        account_id = config.get("account_id")

        observed_signals: list[dict] = []
        likely_pain_areas: set[str] = set()
        likely_stakeholders: set[str] = set()
        company_profile: dict = {}
        source_references: list[dict] = []

        for ed in extracted_data:
            data = ed.data if hasattr(ed, "data") and ed.data else {}

            # Merge company profile (take first non-empty)
            prof = data.get("company_profile", {})
            if prof and not company_profile:
                company_profile = prof

            # Collect signals with source evidence
            for sig in data.get("observed_signals", []):
                observed_signals.append(
                    {
                        "signal": sig.get("signal", ""),
                        "source": sig.get("source", ""),
                        "confidence": sig.get("confidence", "medium"),
                        "detail": sig.get("detail", ""),
                    }
                )

            likely_pain_areas.update(data.get("likely_pain_areas", []))
            likely_stakeholders.update(data.get("likely_stakeholders", []))

            for ev in data.get("source_evidence", []):
                source_references.append(
                    {
                        "url": ev.get("source_url", ""),
                        "source_type": ev.get("source_type", "unknown"),
                        "confidence": ev.get("confidence", "medium"),
                        "extracted_at": ev.get("extracted_at"),
                    }
                )

        return {
            "tenant_id": tenant_id,
            "account_id": account_id,
            "account_name": account_name,
            "packet_type": "prospect_research",
            "company_profile": company_profile,
            "observed_signals": observed_signals,
            "likely_pain_areas": sorted(likely_pain_areas),
            "likely_stakeholders": sorted(likely_stakeholders),
            "source_references": source_references,
            "confidence_summary": {
                "signal_count": len(observed_signals),
                "high_confidence_signals": sum(
                    1 for s in observed_signals if s.get("confidence") == "high"
                ),
            },
            "next_recommended_events": self.config.downstream_events,
            "job_id": str(job.id),
        }
