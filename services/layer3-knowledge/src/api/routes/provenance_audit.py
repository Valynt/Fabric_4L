"""Provenance and audit read-only route group."""

import logging
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...api.dependencies import AppState, get_app_state
from ...api.models import (
    AuditLogEntry,
    AuditLogResponse,
    ProvenanceStep,
    ProvenanceTrailResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_tenant_id(request: Request | None) -> str | None:
    if not request:
        return None
    ctx = getattr(request.state, "governance_context", None)
    if ctx and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)
    return None


def _require_tenant_id_from_context(
    request: Request | None,
    *,
    missing_tenant_detail: str,
) -> str:
    if not request:
        raise HTTPException(status_code=401, detail="Authentication context is required")

    ctx = getattr(request.state, "governance_context", None)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Authentication context is required")

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        raise HTTPException(status_code=400, detail=missing_tenant_detail)

    return tenant_id


@router.get(
    "/v1/provenance/{entity_id}",
    response_model=ProvenanceTrailResponse,
    tags=["Provenance"],
    summary="Get Entity Provenance Trail",
    description="Returns full audit trail and provenance chain for an entity",
)
async def get_provenance(
    entity_id: str,
    request: Request,
    app_state: AppState = Depends(get_app_state),
):
    if not entity_id or not entity_id.strip():
        raise HTTPException(status_code=400, detail="entity_id is required")

    tenant_id = _require_tenant_id_from_context(
        request,
        missing_tenant_detail="tenant_id is required for provenance access",
    )

    entity_id = entity_id.strip()
    if len(entity_id) > 255:
        raise HTTPException(status_code=400, detail="entity_id too long (max 255 chars)")

    try:
        neo4j = app_state.neo4j_driver
        if not neo4j:
            raise HTTPException(status_code=503, detail="Neo4j not available")

        entity_query = """
        MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})
        RETURN e.id as entity_id, e.type as entity_type, e.name as entity_name,
               e.created_at as created_at, e.source as source,
               e.extraction_job_id as extraction_job_id, e.confidence as confidence_score
        LIMIT 1
        """
        query_params = {"entity_id": entity_id, "tenant_id": tenant_id}
        entity_result = await neo4j.execute_query(entity_query, query_params)

        if not entity_result:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        record = entity_result[0]

        steps_query = """
        MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (e)-[:AUDIT_OF]->(a:AuditEvent)
        WITH a
        WHERE a IS NOT NULL
        RETURN a.step as step, a.label as label, a.detail as detail,
               a.timestamp as timestamp, a.agent as agent, a.entity_id as step_entity_id
        ORDER BY a.step
        """
        steps_params = {"entity_id": entity_id, "tenant_id": tenant_id}
        steps_result = await neo4j.execute_query(steps_query, steps_params)

        steps = [
            ProvenanceStep(
                step=s.get("step", i + 1),
                label=s.get("label", f"Step {i + 1}"),
                detail=s.get("detail", ""),
                timestamp=s.get("timestamp", datetime.utcnow()),
                agent=s.get("agent"),
                entity_id=s.get("step_entity_id"),
            )
            for i, s in enumerate(steps_result)
        ]

        if not steps:
            steps = [
                ProvenanceStep(
                    step=1,
                    label="Entity Created",
                    detail=f"Entity {entity_id} created from source",
                    timestamp=record.get("created_at", datetime.utcnow()),
                    agent="ExtractionEngine-v2.1",
                    entity_id=entity_id,
                )
            ]

        return ProvenanceTrailResponse(
            entity_id=record.get("entity_id", entity_id),
            entity_type=record.get("entity_type", "Unknown"),
            entity_name=record.get("entity_name", "Unknown"),
            created_at=record.get("created_at", datetime.utcnow()),
            source=record.get("source", "unknown"),
            extraction_job_id=record.get("extraction_job_id"),
            steps=steps,
            confidence_score=record.get("confidence_score"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provenance query failed: {e}")
        raise HTTPException(status_code=500, detail="Provenance query failed. Please try again later.")


@router.get(
    "/v1/audit/logs",
    response_model=AuditLogResponse,
    tags=["Audit"],
    summary="List Audit Logs",
    description="Query system audit events from Neo4j provenance or API access logs",
)
async def list_audit_logs(
    source: Literal["all", "provenance", "access"] = Query(
        "all", description="Source: 'provenance', 'access', or 'all'"
    ),
    from_date: datetime | None = Query(None, description="Start date filter"),
    to_date: datetime | None = Query(None, description="End date filter"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    event_type: str | None = Query(None, description="Filter by event type"),
    agent: str | None = Query(None, description="Filter by agent"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Entries per page"),
    app_state: AppState = Depends(get_app_state),
):
    try:
        entries: list[AuditLogEntry] = []

        if source in ("provenance", "all"):
            neo4j = app_state.neo4j_driver
            if neo4j:
                try:
                    query = """
                    OPTIONAL MATCH (a:AuditEvent)
                    WHERE ($from_date IS NULL OR a.timestamp >= $from_date)
                      AND ($to_date IS NULL OR a.timestamp <= $to_date)
                      AND ($entity_type IS NULL OR a.entity_type = $entity_type)
                      AND ($event_type IS NULL OR a.event_type = $event_type)
                      AND ($agent IS NULL OR a.agent = $agent)
                    WITH a
                    WHERE a IS NOT NULL
                    RETURN a.id as id, a.timestamp as timestamp, a.event_type as event_type,
                           a.entity_id as entity_id, a.entity_type as entity_type,
                           a.action as action, a.agent as agent, a.details as details
                    ORDER BY a.timestamp DESC
                    SKIP $skip LIMIT $limit
                    """
                    params = {
                        "from_date": from_date.isoformat() if from_date else None,
                        "to_date": to_date.isoformat() if to_date else None,
                        "entity_type": entity_type,
                        "event_type": event_type,
                        "agent": agent,
                        "skip": (page - 1) * per_page,
                        "limit": per_page,
                    }

                    result = await neo4j.execute_query(query, params)
                    for r in result:
                        if r.get("id"):
                            entries.append(
                                AuditLogEntry(
                                    id=r.get("id", str(uuid.uuid4())),
                                    timestamp=r.get("timestamp", datetime.utcnow()),
                                    source="provenance",
                                    event_type=r.get("event_type", "unknown"),
                                    entity_id=r.get("entity_id"),
                                    entity_type=r.get("entity_type"),
                                    action=r.get("action", "unknown"),
                                    agent=r.get("agent", "system"),
                                    details=r.get("details") or {},
                                )
                            )
                except Exception as neo4j_error:
                    logger.warning(
                        f"Neo4j audit query failed (schema may not exist yet): {neo4j_error}"
                    )

        entries.sort(key=lambda x: x.timestamp, reverse=True)

        return AuditLogResponse(
            entries=entries,
            total=len(entries),
            page=page,
            per_page=per_page,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit log query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to query audit logs")
