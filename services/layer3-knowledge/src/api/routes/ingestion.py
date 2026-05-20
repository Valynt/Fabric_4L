"""Ingestion domain router — RDF ingest, sync status, and source deletion.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
All write-paths use the sync_manager service; tenant_id is extracted from
the authenticated request context or the X-Tenant-ID header.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from ...api.dependencies import get_sync_manager
from ...api.models import IngestRequest, IngestResponse, SyncStatusResponse

# X-Tenant-ID header is intentionally not accepted here. tenant_id is
# extracted exclusively from the authenticated request context to prevent
# callers from ingesting data under an arbitrary tenant.

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Ingestion"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_rdf(
    request: IngestRequest,
    fastapi_request: Request,
    sync_manager=Depends(get_sync_manager),
) -> IngestResponse:
    """Ingest RDF data from the Layer 2 extraction pipeline."""
    ctx = getattr(fastapi_request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise HTTPException(
            status_code=401, detail="Authenticated tenant context required for ingestion"
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
        raise HTTPException(
            status_code=500, detail="Ingestion failed. Please try again later."
        )


@router.get("/ingest/status/{source_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    source_id: str,
    sync_manager=Depends(get_sync_manager),
) -> SyncStatusResponse:
    """Get synchronisation status for a source."""
    status = await sync_manager.get_sync_status(source_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

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
    sync_manager=Depends(get_sync_manager),
) -> dict[str, Any]:
    """Delete all data for a source."""
    stats = await sync_manager.delete_source(source_id)
    return {
        "status": "deleted",
        "source_id": source_id,
        "entities_deleted": stats.get("entities_deleted", 0),
        "relationships_deleted": stats.get("relationships_deleted", 0),
    }
