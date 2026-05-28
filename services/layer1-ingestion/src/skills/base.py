from __future__ import annotations

"""Base classes for Layer 1 Source Intelligence Skills."""


from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class SkillConfig(BaseModel):
    """Configuration for a Source Intelligence Skill."""

    skill_name: str = Field(..., description="Canonical skill identifier")
    objective: str = Field(..., description="What the skill is trying to achieve")
    target_entity_type: str = Field(..., description="Type of entity being researched")
    required_source_types: list[str] = Field(
        default_factory=list,
        description="Source types this skill needs to collect",
    )
    output_contract: str = Field(
        ...,
        description="Name of the output model this skill produces",
    )
    downstream_events: list[str] = Field(
        default_factory=list,
        description="Events to emit after successful output storage",
    )
    extraction_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for AI extraction stage",
    )


class BaseSkill(ABC):
    """Abstract base for all Layer 1 Source Intelligence Skills.

    Skills provide:
    - Intent (why work is being done)
    - Source targeting (what to collect)
    - Extraction schema (what to extract)
    - Output builder (how to package results)
    - Downstream events (what to emit next)
    """

    config: SkillConfig

    def __init__(self, config: SkillConfig | None = None) -> None:
        self.config = config or self._default_config()

    @classmethod
    @abstractmethod
    def _default_config(cls) -> SkillConfig:
        """Return the default configuration for this skill."""
        raise NotImplementedError

    @abstractmethod
    def build_output(
        self,
        job: Any,
        raw_contents: list[Any],
        extracted_data: list[Any],
    ) -> dict[str, Any]:
        """Build the skill-specific structured output from pipeline results.

        Args:
            job: The ScrapingJob instance
            raw_contents: List of RawContent records produced by the crawl
            extracted_data: List of ExtractedData records from AI extraction

        Returns:
            Dict matching the skill's output contract schema
        """
        raise NotImplementedError

    @property
    def skill_name(self) -> str:
        return self.config.skill_name

    @property
    def output_contract(self) -> str:
        return self.config.output_contract

    @property
    def downstream_events(self) -> list[str]:
        return self.config.downstream_events
