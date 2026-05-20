"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: ValueSignal graph persistence routes for Layer 3 Knowledge Graph.

Stores ValueSignal objects as Neo4j nodes and provides tenant-scoped
query endpoints for L4 agents and the frontend.

Routes:
  POST  /api/v1/graph/signals                    Persist a ValueSignal node
  GET   /api/v1/graph/signals                    Query ValueSignal nodes
  GET   /api/v1/graph/signals/{signal_id}        Get a single ValueSignal node
  GET   /api/v1/graph/signals/{signal_id}/related Related entities
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from value_fabric.shared.identity import RequestContext, require_authenticated

from ...api.dependencies_tenant_secured import Neo4jTenantSessionSecured as Neo4jTenantSession, get_neo4j_secured as get_neo4j_with_tenant

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/graph/signals",
    tags=["signals"],
    dependencies=[Depends(require_authenticated)],
)

# Cypher: create or merge a ValueSignal node
_UPSERT_SIGNAL_CYPHER = """
MERGE (s:ValueSignal {id: $id, tenant_id: $tenant_id})
SET
  s.account_id       = $account_id,
  s.type             = $type,
  s.content          = $content,
  s.confidence       = $confidence,
  s.trust_score      = $trust_score,
  s.lifecycle_state  = $lifecycle_state,
  s.impact_area      = $impact_area,
  s.estimated_value  = $estimated_value,
  s.created_at       = $created_at,
  s.updated_at       = $updated_at
WITH s
MATCH (a:Account {id: $account_id, tenant_id: $tenant_id})
MERGE (s)-[:SIGNAL_FOR]->(a)
RETURN s
"""

_GET_SIGNAL_CYPHER = """
MATCH (s:ValueSignal {id: $id, tenant_id: $tenant_id})
RETURN s
"""

_LIST_SIGNALS_CYPHER = """
MATCH (s:ValueSignal {tenant_id: $tenant_id, account_id: $account_id})
WHERE s.lifecycle_state IN $lifecycle_states
  AND s.confidence >= $min_confidence
RETURN s
ORDER BY s.created_at DESC
SKIP $offset
LIMIT $limit
"""

_LIST_SIGNALS_WITH_TYPES_CYPHER = """
MATCH (s:ValueSignal {tenant_id: $tenant_id, account_id: $account_id})
WHERE s.lifecycle_state IN $lifecycle_states
  AND s.confidence >= $min_confidence
  AND s.type IN $types
RETURN s
ORDER BY s.created_at DESC
SKIP $offset
LIMIT $limit
"""

_RELATED_CYPHER = """
MATCH (s:ValueSignal {id: $id, tenant_id: $tenant_id})
OPTIONAL MATCH (s)-[:DRIVES]->(vd:ValueDriver {tenant_id: $tenant_id})
OPTIONAL MATCH (s)-[:INVOLVES]->(p:Persona {tenant_id: $tenant_id})
OPTIONAL MATCH (s)-[:SIGNAL_FOR]->(a:Account {tenant_id: $tenant_id})
RETURN
  collect(DISTINCT {id: vd.id, name: vd.name, type: 'ValueDriver'}) AS value_drivers,
  collect(DISTINCT {id: p.id, name: p.name, type: 'Persona'})       AS personas,
  collect(DISTINCT {id: a.id, name: a.name, type: 'Account'})       AS accounts
"""

_ALL_LIFECYCLE_STATES = [
    "draft", "extracted", "validated", "rejected", "promoted", "expired", "superseded"
]


def _node_to_dict(node: Any) -> dict[str, Any]:
    return dict(node)


# ---------------------------------------------------------------------------
# POST /api/v1/graph/signals — persist a ValueSignal node
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
async def persist_signal(
    body: dict[str, Any],
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> dict[str, Any]:
    """Persist a ValueSignal as a Neo4j node and link to its Account.

    Called by L2.5 after refinement. Idempotent via MERGE on (id, tenant_id).
    """
    required = ("id", "tenant_id", "account_id", "type", "content", "confidence")
    missing = [f for f in required if not body.get(f)]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields: {missing}",
        )

    # Enforce tenant from context, not body
    tenant_id = neo4j.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required")

    params = {
        "id": body["id"],
        "tenant_id": tenant_id,
        "account_id": body["account_id"],
        "type": body["type"],
        "content": body["content"][:500],  # truncate for graph storage
        "confidence": float(body.get("confidence", 0.0)),
        "trust_score": float(body.get("trust_score", 0.0)),
        "lifecycle_state": body.get("lifecycle_state", "draft"),
        "impact_area": body.get("impact_area"),
        "estimated_value": body.get("estimated_value"),
        "created_at": body.get("created_at", ""),
        "updated_at": body.get("updated_at", ""),
    }

    try:
        # tenant_id is resolved from Neo4jTenantSession and forced into params.
        result = await neo4j.run(_UPSERT_SIGNAL_CYPHER, params)
        record = await result.single()
        if record:
            return {"status": "ok", "signal": _node_to_dict(record["s"])}
        return {"status": "ok", "signal": params}
    except Exception as exc:
        logger.exception("Failed to persist ValueSignal %s to Neo4j", body.get("id"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph persistence failed",
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/v1/graph/signals — query signals
# ---------------------------------------------------------------------------


@router.get("")
async def list_graph_signals(
    account_id: str = Query(...),
    lifecycle_states: list[str] | None = Query(None),
    types: list[str] | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> dict[str, Any]:
    tenant_id = neo4j.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required")

    states = lifecycle_states or _ALL_LIFECYCLE_STATES

    params: dict[str, Any] = {
        "tenant_id": tenant_id,
        "account_id": account_id,
        "lifecycle_states": states,
        "min_confidence": min_confidence,
        "limit": limit,
        "offset": offset,
    }

    if types:
        cypher = _LIST_SIGNALS_WITH_TYPES_CYPHER
        params["types"] = types
    else:
        cypher = _LIST_SIGNALS_CYPHER

    try:
        # tenant_id is resolved from Neo4jTenantSession and forced into params.
        result = await neo4j.run(cypher, params)
        records = await result.data()
        items = [_node_to_dict(r["s"]) for r in records]
        return {"items": items, "total": len(items), "limit": limit, "offset": offset}
    except Exception as exc:
        logger.exception("Failed to query ValueSignals from Neo4j")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph query failed",
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/v1/graph/signals/{signal_id} — single signal
# ---------------------------------------------------------------------------


@router.get("/{signal_id}")
async def get_graph_signal(
    signal_id: str,
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> dict[str, Any]:
    tenant_id = neo4j.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required")

    try:
        result = await neo4j.run(_GET_SIGNAL_CYPHER, {"id": signal_id, "tenant_id": tenant_id})
        record = await result.single()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found in graph")
        return _node_to_dict(record["s"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get ValueSignal %s from Neo4j", signal_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph query failed",
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/v1/graph/signals/{signal_id}/related — related entities
# ---------------------------------------------------------------------------


@router.get("/{signal_id}/related")
async def get_signal_related(
    signal_id: str,
    _ctx: RequestContext = Depends(require_authenticated),
    neo4j: Neo4jTenantSession = Depends(get_neo4j_with_tenant),
) -> dict[str, Any]:
    tenant_id = neo4j.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context required")

    try:
        result = await neo4j.run(_RELATED_CYPHER, {"id": signal_id, "tenant_id": tenant_id})
        record = await result.single()
        if not record:
            return {"value_drivers": [], "personas": [], "accounts": []}
        return {
            "value_drivers": record["value_drivers"] or [],
            "personas": record["personas"] or [],
            "accounts": record["accounts"] or [],
        }
    except Exception as exc:
        logger.exception("Failed to get related entities for signal %s", signal_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph query failed",
        ) from exc
