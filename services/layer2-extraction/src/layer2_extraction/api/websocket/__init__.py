"""Layer 2 API websocket package.

Provides pipeline stage types and websocket manager for real-time
extraction progress streaming.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PipelineStage(str, Enum):
    """Canonical pipeline stage identifiers for websocket progress updates."""

    CHUNKING = "chunking"
    ENTITY_EXTRACTION = "entity_extraction"
    SEMANTIC_ALIGNMENT = "semantic_alignment"
    DEDUPLICATION = "deduplication"
    VALIDATION = "validation"
    RDF_GENERATION = "rdf_generation"


class _PipelineWSManager:
    """Placeholder websocket manager for pipeline progress streaming.

    Full implementation tracked in layer2-extraction websocket backlog.
    Stubs required for api/main.py import surface and OpenAPI export.
    """

    async def broadcast(self, job_id: str, stage: PipelineStage, message: dict[str, Any]) -> None:
        pass

    async def broadcast_ingestion_status(
        self,
        job_id: str,
        status: str,
        retry_count: int = 0,
        max_retries: int = 0,
        error: str | None = None,
        entities_loaded: int | None = None,
        relationships_loaded: int | None = None,
    ) -> None:
        pass

    async def broadcast_stage_start(
        self,
        job_id: str,
        stage: PipelineStage,
        stage_number: int = 0,
        total_stages: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def broadcast_stage_complete(
        self,
        job_id: str,
        stage: PipelineStage,
        stage_number: int = 0,
        total_stages: int = 0,
        result_summary: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def broadcast_stage_progress(
        self,
        job_id: str,
        stage: PipelineStage,
        stage_number: int = 0,
        total_stages: int = 0,
        items_processed: int = 0,
        items_total: int = 0,
        stage_percent: int = 0,
    ) -> None:
        pass

    async def broadcast_pipeline_complete(
        self,
        job_id: str,
        status: str,
        entities_extracted: int = 0,
        relationships_extracted: int = 0,
        rdf_path: str | None = None,
        errors: list[str] | None = None,
        entities_loaded: int | None = None,
        relationships_loaded: int | None = None,
    ) -> None:
        pass

    async def broadcast_error(
        self,
        job_id: str,
        stage: PipelineStage,
        error: str,
        recoverable: bool = False,
    ) -> None:
        pass

    def register(self, job_id: str, connection: Any) -> None:
        pass

    def unregister(self, job_id: str, connection: Any) -> None:
        pass


def get_pipeline_ws_manager() -> _PipelineWSManager:
    """Return the singleton pipeline websocket manager."""
    return _PipelineWSManager()


__all__ = ["PipelineStage", "get_pipeline_ws_manager"]
