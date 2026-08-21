"""
Layer 3 Knowledge Graph sync operations for Ground Truth integration.

Provides idempotent upsert of GroundTruth nodes from Layer 5.
"""

from __future__ import annotations

import logging
from uuid import UUID

from value_fabric.shared.models import JSONDict

from ...db import run_validated_query
from ...db.driver import get_driver
from ..utils.cypher_security import (
    ALLOWED_REL_TYPES,
    ALLOWED_TARGET_LABELS,
    validate_cypher_identifier,
)

logger = logging.getLogger(__name__)

GROUND_TRUTH_LABEL = "GroundTruth"


async def upsert_ground_truth_node(
    *,
    tenant_id: UUID,
    truth_object_id: UUID,
    claim: str,
    claim_type: str,
    confidence: float,
    status: str,
    maturity_level: int,
    value: JSONDict | None = None,
    applies_to: JSONDict | None = None,
    source_count: int = 0,
) -> str:
    """
    Idempotently upsert a GroundTruth node in the knowledge graph.
    
    Uses MERGE on (truth_object_id, tenant_id) to ensure idempotency.
    
    Returns:
        The Neo4j node ID (elementId) of the created/updated GroundTruth node.
    """
    driver = get_driver()
    
    # Prepare properties for the node
    properties = {
        "truth_object_id": str(truth_object_id),
        "tenant_id": str(tenant_id),
        "claim": claim,
        "claim_type": claim_type,
        "confidence": confidence,
        "status": status,
        "maturity_level": maturity_level,
        "source_count": source_count,
        "value": value,
        "applies_to": applies_to,
    }
    
    # Build the MERGE query
    validate_cypher_identifier(GROUND_TRUTH_LABEL, ALLOWED_TARGET_LABELS, kind="label")
    query = (
        f"MERGE (g:{GROUND_TRUTH_LABEL} {{truth_object_id: $truth_object_id, tenant_id: $tenant_id}})\n"  # cypher-dynamic-safe: GROUND_TRUTH_LABEL is hardcoded literal  # cypher-mutation-safe: label is hardcoded constant, tenant-scoped
        "    SET g += $properties\n"
        "    SET g.updated_at = datetime()\n"
        "    RETURN elementId(g) as node_id\n"
        "    "
    )
    
    params = {
        "truth_object_id": str(truth_object_id),
        "tenant_id": str(tenant_id),
        "properties": properties,
    }
    
    async with driver.session() as session:
        result = await run_validated_query(
            session.run,
            query,
            params,
            tenant_id=str(tenant_id),
            query_name="upsert_ground_truth_node",
        )
        record = await result.single()
        if record:
            return str(record["node_id"])
    
    raise RuntimeError("Failed to upsert GroundTruth node")


async def link_ground_truth_to_entity(
    *,
    tenant_id: UUID,
    ground_truth_node_id: str,
    target_entity_id: str,
    relationship_type: str = "GROUNDS",
    properties: JSONDict | None = None,
) -> bool:
    """
    Create a relationship between a GroundTruth node and an existing KG entity.
    
    Returns True on success.
    """
    driver = get_driver()
    
    rel_props = properties or {}
    rel_props["created_at"] = "datetime()"

    validate_cypher_identifier(relationship_type, ALLOWED_REL_TYPES, kind="rel_type")
    query = (
        "MATCH (g:GroundTruth), (e:Entity)\n"
        "WHERE elementId(g) = $gt_node_id AND e.tenant_id = $tenant_id AND e.id = $entity_id\n"
        f"    MERGE (g)-[r:{relationship_type}]->(e)\n"  # cypher-dynamic-safe: relationship_type validated against ALLOWED_REL_TYPES allowlist
        "    SET r += $rel_props\n"
        "    RETURN elementId(r) as rel_id\n"
        "    "
    )
    
    params = {
        "gt_node_id": ground_truth_node_id,
        "tenant_id": str(tenant_id),
        "entity_id": target_entity_id,
        "rel_props": properties or {},
    }
    
    async with driver.session() as session:
        result = await run_validated_query(
            session.run,
            query,
            params,
            tenant_id=str(tenant_id),
            query_name="link_ground_truth_to_entity",
        )
        record = await result.single()
        return record is not None


async def get_ground_truth_node(
    *,
    tenant_id: UUID,
    truth_object_id: UUID,
) -> JSONDict | None:
    """Retrieve a GroundTruth node by truth_object_id and tenant_id."""
    driver = get_driver()
    
    query = """
    MATCH (g:GroundTruth {truth_object_id: $truth_object_id, tenant_id: $tenant_id})
    RETURN elementId(g) as node_id, g
    """
    
    params = {
        "truth_object_id": str(truth_object_id),
        "tenant_id": str(tenant_id),
    }
    
    async with driver.session() as session:
        result = await run_validated_query(
            session.run,
            query,
            params,
            tenant_id=str(tenant_id),
            query_name="get_ground_truth_node",
        )
        record = await result.single()
        if record:
            node = dict(record["g"])
            node["node_id"] = record["node_id"]
            return node
    return None
