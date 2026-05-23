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

    def register(self, job_id: str, connection: Any) -> None:
        pass

    def unregister(self, job_id: str, connection: Any) -> None:
        pass


def get_pipeline_ws_manager() -> _PipelineWSManager:
    """Return the singleton pipeline websocket manager."""
    return _PipelineWSManager()


__all__ = ["PipelineStage", "get_pipeline_ws_manager"]
