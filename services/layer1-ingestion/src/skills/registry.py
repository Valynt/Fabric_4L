from __future__ import annotations

"""Skill registry for Layer 1 Source Intelligence.

Maps job_type strings to skill instances.  Provides factory access
for pipeline stages that need skill-aware behavior.
"""


from typing import Any

from .base import BaseSkill
from .licensing_company_intake import LicensingCompanyIntakeSkill
from .prospect_research import ProspectResearchSkill

# Canonical mapping: job_type -> skill class
SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "licensing_company_intake": LicensingCompanyIntakeSkill,
    "prospect_research": ProspectResearchSkill,
}


def get_skill(job_type: str | None) -> BaseSkill | None:
    """Look up and instantiate a skill by job_type.

    Returns None for generic_scrape or unknown job types,
    letting the pipeline fall back to legacy behavior.
    """
    if not job_type or job_type == "generic_scrape":
        return None

    skill_cls = SKILL_REGISTRY.get(job_type)
    if skill_cls is None:
        return None

    return skill_cls()


def get_extraction_schema(job_type: str | None) -> dict[str, Any] | None:
    """Return the extraction schema for a given job_type, if any."""
    skill = get_skill(job_type)
    if skill is None:
        return None
    return skill.config.extraction_schema
