"""Route request and response schemas for the Layer 2 API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

DEFAULT_ENTITY_TYPES = ["Capability", "UseCase", "Persona", "ValueDriver"]
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_CONFIDENCE_THRESHOLD = 0.75


def default_extraction_config() -> dict[str, object]:
    return {
        "entity_types": list(DEFAULT_ENTITY_TYPES),
        "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
    }


class ExtractRequest(BaseModel):
    """Request body for extraction endpoint."""

    content_id: str = Field(..., description="ID of content to extract from (from Layer 1)")
    source_url: str = Field(..., description="URL of source document")
    markdown_content: str = Field(..., description="Markdown content to extract from")
    extraction_config: dict = Field(default_factory=default_extraction_config)


class ExtractResponse(BaseModel):
    """Response from extraction endpoint."""

    extraction_job_id: str
    status: str
    message: str


class ExtractionStatusResponse(BaseModel):
    """Status of a combined extraction + ingestion pipeline job."""

    job_id: str
    overall_status: str
    extraction_status: str
    ingestion_status: str
    entities_extracted: int
    relationships_extracted: int
    retry_count: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None


class EntityListResponse(BaseModel):
    """List of entities in the ontology."""

    entity_type: str
    entities: list[dict]
    total: int


class RelationshipsResponse(BaseModel):
    """Relationships for an entity."""

    entity_id: str
    incoming: list[dict]
    outgoing: list[dict]


class ProvenanceResponse(BaseModel):
    """Provenance chain for an entity or output."""

    activity_id: str
    source: dict
    extraction: dict
    steps: list[dict]
    output: dict


class ExtractAndIngestResponse(BaseModel):
    """Response for combined extract-and-ingest endpoint."""

    job_id: str
    overall_status: str
    extraction_status: str
    ingestion_status: str
    message: str


class QuarantineStatusResponse(BaseModel):
    """Validation quarantine review payload for failed extraction artifacts."""

    job_id: str
    quarantine_id: str
    tenant_id: str
    source_hash: str
    model_version: str
    schema_version: str
    prompt_template_version: str
    prompt_template_hash: str | None = None
    validation_errors: list[str]
    reason: str
    review_status: str
    retry_eligible: bool
    created_at: datetime
