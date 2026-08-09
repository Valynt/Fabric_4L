"""Server-sent event streaming for extraction jobs."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from value_fabric.shared.error_handling.exceptions import NotFoundError

from layer2_extraction.api.deps import RequestContext, require_authenticated
from layer2_extraction.api.extraction_pipeline import _compute_overall_status, job_store

router = APIRouter()

# SSE Event Generator Constants
#
# LIFECYCLE POLICY (see TestOverallStatusMatrix in test_sse_streaming.py):
# - "partial" (extraction=completed, ingestion=pending/queued) is INTENTIONALLY
#   NON-TERMINAL. The stream keeps polling because ingestion may still progress.
# - The stream only terminates when overall_status reaches "completed" or "failed".
# - ingestion_status must become "completed", "skipped", or "failed" for the
#   SSE generator to break and send the terminal event.
# - TIMEOUT / HEARTBEAT behavior is NOT YET IMPLEMENTED. Before production
#   hardening, decide: server-side max idle polls, client-side timeout, or
#   heartbeat events to detect stalled "partial" jobs.
_SSE_POLL_INTERVAL_SECONDS = 0.5
_SSE_PROGRESS_THRESHOLD_PERCENT = 5
_SSE_PROGRESS_BOUNDARY_VALUES = {0, 50, 100}
_SSE_STATUS_PROGRESS_MAP = {
    "pending": 0,
    "running": 25,
    "partial": 75,
    "completed": 100,
    "failed": 100,
}
_SSE_LOG_LEVELS = {"running": "info", "completed": "success", "failed": "error"}
_SSE_LOG_MESSAGES = {
    "running": "Extraction pipeline is running",
    "completed": "Extraction pipeline completed successfully",
    "failed": "Extraction pipeline failed",
}
_SSE_LOGGABLE_STATUSES = {"running", "completed", "failed"}
_SSE_TERMINAL_STATUSES = {"completed", "failed"}


async def _job_event_generator(job_id: str):
    """Generate SSE events for a pipeline job.

    Yields Server-Sent Events with progress updates, status changes,
    and entity discovery from the extraction pipeline.
    """
    import json

    last_status: str | None = None
    last_progress = -1
    sent_entities: set[str] = set()

    while True:
        job = await job_store.get(job_id)

        if not job:
            # Job not found - send error and close
            yield f"event: error\ndata: {json.dumps({'message': f'Job {job_id} not found'})}\n\n"
            break

        # Compute overall_status from extraction and ingestion status
        overall_status = _compute_overall_status(job.extraction_status, job.ingestion_status)

        # Calculate progress based on status
        progress = _SSE_STATUS_PROGRESS_MAP.get(overall_status, 0)

        # Send status event on change
        if overall_status != last_status:
            last_status = overall_status
            event_data: dict[str, Any] = {
                "type": "status",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "data": overall_status,
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        # Send progress event on significant change or at boundaries
        progress_diff = abs(progress - last_progress)
        if (
            progress_diff >= _SSE_PROGRESS_THRESHOLD_PERCENT
            or progress in _SSE_PROGRESS_BOUNDARY_VALUES
        ):
            last_progress = progress
            event_data = {
                "type": "progress",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "data": progress,
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        # Send entity events for newly discovered entities during active extraction
        if job.entities_extracted > 0 and job.extraction_status == "running":
            entity_key = f"entity_{job_id}_{job.entities_extracted}"
            if entity_key not in sent_entities:
                sent_entities.add(entity_key)
                event_data = {
                    "type": "entity",
                    "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "data": {
                        "type": "Capability",
                        "name": f"Discovered Capability {job.entities_extracted}",
                    },
                }
                yield f"data: {json.dumps(event_data)}\n\n"

        # Send log events for status transitions
        if overall_status in _SSE_LOGGABLE_STATUSES:
            log_message = _SSE_LOG_MESSAGES.get(overall_status, f"Status: {overall_status}")
            if overall_status == "failed":
                log_message = f"{_SSE_LOG_MESSAGES['failed']}: {job.last_error or 'Unknown error'}"
            elif overall_status == "running":
                log_message = f"Extraction pipeline {job_id} is running"
            elif overall_status == "completed":
                log_message = f"Extraction pipeline {job_id} completed successfully"

            event_data = {
                "type": "log",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "data": {
                    "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "level": _SSE_LOG_LEVELS.get(overall_status, "info"),
                    "message": log_message,
                },
            }
            yield f"data: {json.dumps(event_data)}\n\n"

        # Check for completion
        if overall_status in _SSE_TERMINAL_STATUSES:
            event_type = "complete" if overall_status == "completed" else "error"
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "data": {
                    "job_id": job_id,
                    "status": overall_status,
                    "entities_extracted": job.entities_extracted,
                    "relationships_extracted": job.relationships_extracted,
                    "error": job.last_error if overall_status == "failed" else None,
                },
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            break

        # Poll interval - check for updates
        await asyncio.sleep(_SSE_POLL_INTERVAL_SECONDS)


@router.get("/v1/extract/jobs/{job_id}/events")
async def stream_job_events(job_id: str, ctx: RequestContext = Depends(require_authenticated)):
    """Stream real-time events for a pipeline job via SSE.

    Returns a Server-Sent Events stream with progress updates,
    status changes, entity discovery, and log messages.

    Event types:
    - `progress`: Extraction progress percentage (0-100)
    - `status`: Job status changes (pending, running, completed, failed)
    - `log`: Pipeline log messages with timestamp and level
    - `entity`: Newly discovered entities during extraction
    - `complete`: Job completion event
    - `error`: Error event with details

    Args:
        job_id: The pipeline job ID to stream events for

    Returns:
        StreamingResponse with text/event-stream content type
    """
    tenant_id = str(ctx.tenant_id)
    # Validate tenant-scoped access before streaming.
    if not await job_store.get(job_id, tenant_id=tenant_id):
        raise NotFoundError(message=str(f"Job {job_id} not found"))

    return StreamingResponse(
        _job_event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
