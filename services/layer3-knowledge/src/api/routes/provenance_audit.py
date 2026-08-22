from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Provenance and audit read-only route group."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

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


def _parse_audit_details(value: Any) -> dict[str, Any]:
    """Deserialize JSON-encoded audit details stored as a Neo4j string property."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    return {}


def _require_tenant_id_from_context(
    request: Request | None,
    *,
    missing_tenant_detail: str,
) -> str:
    if not request:
        raise AuthenticationError(message = "Authentication context is required")

    ctx = getattr(request.state, "governance_context", None)
    if ctx is None:
        raise AuthenticationError(message = "Authentication context is required")

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        raise ValidationError(message = str(missing_tenant_detail))

    return tenant_id


def _record_to_audit_log_entry(r: dict[str, Any]) -> AuditLogEntry:
    """Convert raw Neo4j record into AuditLogEntry."""
    return AuditLogEntry(
        id=r.get("id", str(uuid.uuid4())),
        timestamp=r.get("timestamp", datetime.now(UTC)),
        source="provenance",
        event_type=r.get("event_type", "unknown"),
        entity_id=r.get("entity_id"),
        entity_type=r.get("entity_type"),
        action=r.get("action", "unknown"),
        agent=r.get("agent", "system"),
        details=_parse_audit_details(r.get("details")),
    )


async def _fetch_provenance_steps(
    neo4j: Any,
    entity_id: str,
    tenant_id: str,
    entity_created_at: Any,
) -> list[ProvenanceStep]:
    """Query and format provenance steps for an entity, providing fallback step if empty."""
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
            timestamp=s.get("timestamp", datetime.now(UTC)),
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
                timestamp=entity_created_at or datetime.now(UTC),
                agent="ExtractionEngine-v2.1",
                entity_id=entity_id,
            )
        ]
    return steps


async def _fetch_provenance_audit_logs(
    neo4j: Any,
    tenant_id: str,
    from_date: datetime | None,
    to_date: datetime | None,
    entity_type: str | None,
    event_type: str | None,
    agent: str | None,
    page: int,
    per_page: int,
) -> list[AuditLogEntry]:
    """Query and map provenance audit event logs from Neo4j."""
    query = """
    OPTIONAL MATCH (a:AuditEvent)
    WHERE ($from_date IS NULL OR a.timestamp >= $from_date)
      AND ($to_date IS NULL OR a.timestamp <= $to_date)
      AND ($entity_type IS NULL OR a.entity_type = $entity_type)
      AND ($event_type IS NULL OR a.event_type = $event_type)
      AND ($agent IS NULL OR a.agent = $agent)
      AND a.tenant_id = $tenant_id
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
        "tenant_id": tenant_id,
        "skip": (page - 1) * per_page,
        "limit": per_page,
    }

    result = await neo4j.execute_query(query, params)
    return [_record_to_audit_log_entry(r) for r in result if r.get("id")]


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
        raise ValidationError(message = "entity_id is required")

    tenant_id = _require_tenant_id_from_context(
        request,
        missing_tenant_detail="tenant_id is required for provenance access",
    )

    entity_id = entity_id.strip()
    if len(entity_id) > 255:
        raise ValidationError(message = "entity_id too long (max 255 chars)")

    try:
        neo4j = app_state.neo4j_driver
        if not neo4j:
            raise ServiceUnavailableError(message = "Neo4j not available")

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
            raise NotFoundError(message = str(f"Entity {entity_id} not found"))

        record = entity_result[0]
        steps = await _fetch_provenance_steps(
            neo4j, entity_id, tenant_id, record.get("created_at")
        )

        return ProvenanceTrailResponse(
            entity_id=record.get("entity_id", entity_id),
            entity_type=record.get("entity_type", "Unknown"),
            entity_name=record.get("entity_name", "Unknown"),
            created_at=record.get("created_at", datetime.now(UTC)),
            source=record.get("source", "unknown"),
            extraction_job_id=record.get("extraction_job_id"),
            steps=steps,
            confidence_score=record.get("confidence_score"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provenance query failed: {e}")
        raise ServiceUnavailableError(message="Provenance query failed. Please try again later.")


@router.get(
    "/v1/audit/logs",
    response_model=AuditLogResponse,
    tags=["Audit"],
    summary="List Audit Logs",
    description="Query system audit events from Neo4j provenance or API access logs",
)
async def list_audit_logs(
    request: Request,
    app_state: AppState = Depends(get_app_state),
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
):
    tenant_id = _require_tenant_id_from_context(
        request,
        missing_tenant_detail="tenant_id is required for audit log access",
    )

    try:
        entries: list[AuditLogEntry] = []

        if source in ("provenance", "all"):
            neo4j = app_state.neo4j_driver
            if neo4j:
                try:
                    entries = await _fetch_provenance_audit_logs(
                        neo4j=neo4j,
                        tenant_id=tenant_id,
                        from_date=from_date,
                        to_date=to_date,
                        entity_type=entity_type,
                        event_type=event_type,
                        agent=agent,
                        page=page,
                        per_page=per_page,
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
        raise ServiceUnavailableError(message="Failed to query audit logs")
