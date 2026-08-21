"""Ingestion domain router — RDF ingest, sync status, and source deletion.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All write-paths use the sync_manager service; tenant_id is derived
exclusively from authenticated request context (never from X-Tenant-ID).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
)
from value_fabric.shared.models import JSONDict

from ...api.dependencies import get_sync_manager
from ...api.models import IngestRequest, IngestResponse, SyncStatusResponse

# X-Tenant-ID header is intentionally not accepted here. tenant_id is
# extracted exclusively from the authenticated request context to prevent
# callers from ingesting data under an arbitrary tenant.

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Ingestion"])


class GroundTruthNodeRequest(BaseModel):
    """Ground Truth node creation request from Layer 5.
    
    Matches the payload format used by Layer 5's Layer3Client.sync_truth_object().
    """
    node_type: str = Field(..., description="Node type (expected: 'GroundTruth')")
    properties: JSONDict = Field(..., description="Node properties")
    merge_keys: list[str] = Field(default_factory=list, description="Keys for MERGE operation")


class GroundTruthNodeResponse(BaseModel):
    """Ground Truth node creation response."""
    node_id: str = Field(..., description="Created node ID")
    status: Literal["created", "updated"] = Field(..., description="Whether node was created or updated")
    message: str = Field(default="", description="Additional message")


@router.post("/nodes", response_model=GroundTruthNodeResponse)
async def create_ground_truth_node(
    request: GroundTruthNodeRequest,
    fastapi_request: Request,
    sync_manager=Depends(get_sync_manager),
) -> GroundTruthNodeResponse:
    """Create or update a GroundTruth node from Layer 5.
    
    This endpoint is called by Layer 5's Layer3Client.sync_truth_object()
    to persist validated TruthObjects as :GroundTruth nodes in the Knowledge Graph.
    """
    ctx = getattr(fastapi_request.state, "governance_context", None) or getattr(fastapi_request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise AuthenticationError(message="Authenticated tenant context required for Ground Truth sync")

    if request.node_type != "GroundTruth":
        raise ServiceUnavailableError(message="Only GroundTruth node type is supported")

    props = request.properties
    truth_object_id = props.get("truth_object_id")
    if not truth_object_id:
        raise ServiceUnavailableError(message="truth_object_id is required in properties")

    # Ensure tenant_id is in properties for merge
    props["tenant_id"] = tenant_id

    # For now, delegate to the sync manager's node creation
    # This creates a :GroundTruth node with the provided properties
    from ...services.kg_sync import get_sync_manager as get_kg_sync_manager
    kg_sync = get_kg_sync_manager()
    
    try:
        # Create or update the GroundTruth node
        node_id = await kg_sync.upsert_ground_truth_node(
            truth_object_id=truth_object_id,
            tenant_id=tenant_id,
            properties=props,
        )
        
        return GroundTruthNodeResponse(
            node_id=node_id,
            status="created",
            message=f"GroundTruth node synced for truth_object_id={truth_object_id}"
        )
    except Exception as e:
        logger.error("Ground Truth node creation failed: %s", e)
        raise ServiceUnavailableError(message="Ground Truth sync failed")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_rdf(
    request: IngestRequest,
    fastapi_request: Request,
    sync_manager=Depends(get_sync_manager),
) -> IngestResponse:
    """Ingest RDF data from the Layer 2 extraction pipeline."""
    ctx = getattr(fastapi_request.state, "governance_context", None) or getattr(fastapi_request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise AuthenticationError(message = "Authenticated tenant context required for ingestion")

    # Fail closed: if a caller supplies tenant_id in the body, it MUST match
    # the authenticated tenant. Body tenant_id is never trusted as a source
    # of truth — a mismatch indicates confused-deputy or stale-client usage.
    if request.tenant_id is not None and request.tenant_id != tenant_id:
        raise AuthenticationError(
            message="Body tenant_id does not match authenticated tenant context"
        )

    try:
        stats = await sync_manager.sync_extraction_result(
            rdf_data=request.rdf_data,
            source_id=request.source_id,
            extraction_job_id=request.extraction_job_id,
            content_hash=request.content_hash,
            tenant_id=tenant_id,
        )

        raw_status = stats.get("status", "unknown")
        status = "success" if raw_status in {"synced", "success"} else raw_status
        if status not in {"success", "partial", "failed"}:
            status = "failed"

        normalized_status: Literal["success", "partial", "failed"] = "failed"
        if status == "success":
            normalized_status = "success"
        elif status == "partial":
            normalized_status = "partial"

        return IngestResponse.model_validate(
            {
                "status": normalized_status,
                "source_id": request.source_id,
                "entities_loaded": stats.get("entities_loaded", 0),
                "relationships_loaded": stats.get("relationships_loaded", 0),
                "triples_processed": stats.get("triples_processed", 0),
                "duration_seconds": stats.get("duration_seconds"),
                "error": stats.get("error"),
            }
        )
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        raise ServiceUnavailableError(message="Ingestion failed. Please try again later.")


@router.get("/ingest/status/{source_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    source_id: str,
    fastapi_request: Request,
    sync_manager=Depends(get_sync_manager),
) -> SyncStatusResponse:
    """Get synchronisation status for a source."""
    ctx = getattr(fastapi_request.state, "governance_context", None) or getattr(fastapi_request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise AuthenticationError(
            message="Authenticated tenant context required for ingestion"
        )

    status = await sync_manager.get_sync_status(source_id, tenant_id=tenant_id)
    if not status:
        raise NotFoundError(message = str(f"Source {source_id} not found"))

    return SyncStatusResponse(
        source_id=source_id,
        last_extraction_job_id=status.get("last_extraction_job_id"),
        content_hash=status.get("content_hash"),
        synced_at=status.get("synced_at"),
        status=status.get("status"),
        error=status.get("error"),
    )


@router.delete("/ingest/{source_id}")
async def delete_source(
    source_id: str,
    fastapi_request: Request,
    sync_manager=Depends(get_sync_manager),
) -> JSONDict:
    """Delete all data for a source."""
    ctx = getattr(fastapi_request.state, "governance_context", None) or getattr(fastapi_request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise AuthenticationError(
            message="Authenticated tenant context required for ingestion"
        )

    stats = await sync_manager.delete_source(source_id, tenant_id=tenant_id)
    return {
        "status": "deleted",
        "source_id": source_id,
        "entities_deleted": stats.get("entities_deleted", 0),
        "relationships_deleted": stats.get("relationships_deleted", 0),
    }
