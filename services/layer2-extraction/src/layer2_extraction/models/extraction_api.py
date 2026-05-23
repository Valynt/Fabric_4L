"""API request and response models for Layer 2 extraction."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from layer2_extraction.models.ontology import (
    Capability,
    Feature,
    Persona,
    UseCase,
    ValueDriver,
)
from layer2_extraction.models.relationships import Relationship
from layer2_extraction.models.version_manifest import VersionManifest


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_url: str
    content: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    content_id: str = ""
    markdown_content: str = ""
    extraction_config: dict[str, Any] = Field(default_factory=dict)
    version_manifest: VersionManifest | None = None


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_url: str
    job_id: str = ""
    capabilities: list[Capability] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    use_cases: list[UseCase] = Field(default_factory=list)
    personas: list[Persona] = Field(default_factory=list)
    value_drivers: list[ValueDriver] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    extraction_cost_usd: float = 0.0
    chunks_processed: int = 0
    version_manifest: VersionManifest | None = None

    def get_all_entities(self) -> list[Any]:
        return (
            self.capabilities
            + self.features
            + self.use_cases
            + self.personas
            + self.value_drivers
        )

    def get_entity_by_id(self, entity_id: str) -> Any | None:
        for entity in self.get_all_entities():
            if getattr(entity, "id", None) == entity_id:
                return entity
        return None
