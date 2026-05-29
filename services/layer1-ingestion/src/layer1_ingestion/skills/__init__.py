"""Layer 1 Source Intelligence Skill Registry.

Skill-aware orchestration layer on top of the existing Celery scraping pipeline.
Provides intent, output contracts, and downstream event definitions
without replacing the execution substrate.
"""

from .base import BaseSkill, SkillConfig
from .licensing_company_intake import LicensingCompanyIntakeSkill
from .prospect_research import ProspectResearchSkill
from .registry import SKILL_REGISTRY, get_extraction_schema, get_skill

__all__ = [
    "BaseSkill",
    "SkillConfig",
    "LicensingCompanyIntakeSkill",
    "ProspectResearchSkill",
    "SKILL_REGISTRY",
    "get_skill",
    "get_extraction_schema",
]
