"""Centralized, audited graph-mutation pipeline for Layer 3.

All relationship writes (CREATE, MERGE, DELETE) should route through this
module so that provenance, versioning, and tenant isolation are enforced
uniformly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from value_fabric.layer3.db.query_execution import run_tenant_query
from value_fabric.layer3.utils.cypher_security import (
    ALLOWED_REL_TYPES,
    validate_cypher_identifier,
)


class AuditedGraphMutation:
    """Mandatory mutation gateway for all graph relationship changes.

    Guarantees:
    1. Relationship types are allowlisted before Cypher interpolation.
    2. Tenant isolation is enforced via ``TenantQueryExecutor``.
    3. Every mutation produces an ``AuditEvent`` node.
    4. Optional relationship versioning via ``RelationshipVersion`` nodes.
    """

    def __init__(
        self,
        tenant_id: str,
        session,
        metrics: Any | None = None,
    ):
        self.tenant_id = tenant_id
        self.session = session
        self.metrics = metrics

    async def write_relationship(
        self,
        src_id: str,
        rel_type: str,
        tgt_id: str,
        properties: dict[str, Any] | None = None,
        versioned: bool = False,
    ) -> dict[str, Any]:
        """Merge a relationship between two tenant-scoped nodes and audit the change."""
        validate_cypher_identifier(rel_type, ALLOWED_REL_TYPES, kind="relationship type")

        now = datetime.now(UTC).isoformat()
        props = dict(properties or {})

        # Double-check rel_type is allowlisted at runtime (defense-in-depth)
        if rel_type not in ALLOWED_REL_TYPES:
            raise ValueError(f"Relationship type '{rel_type}' not in allowlist")

        merge_query = f"""
        MATCH (src {{id: $src_id, tenant_id: $tenant_id}})
        MATCH (tgt {{id: $tgt_id, tenant_id: $tenant_id}})
        MERGE (src)-[r:{rel_type}]->(tgt)
        SET r.updated_at = $now
        RETURN r
        """
        await run_tenant_query(
            self.session,
            merge_query,
            {
                "src_id": src_id,
                "tgt_id": tgt_id,
                "tenant_id": self.tenant_id,
                "now": now,
                **props,
            },
            tenant_id=self.tenant_id,
        )

        await self._audit("WRITE_RELATIONSHIP", src_id, rel_type, tgt_id, props)

        if versioned:
            await self._version_relationship(src_id, rel_type, tgt_id, props)

        return {"status": "ok", "rel_type": rel_type}

    async def delete_relationship(
        self,
        src_id: str,
        rel_type: str,
        tgt_id: str,
    ) -> dict[str, Any]:
        """Delete a relationship between two tenant-scoped nodes and audit the change."""
        validate_cypher_identifier(rel_type, ALLOWED_REL_TYPES, kind="relationship type")

        delete_query = f"""
        MATCH (src {{id: $src_id, tenant_id: $tenant_id}})
              -[r:{rel_type}]->
              (tgt {{id: $tgt_id, tenant_id: $tenant_id}})
        DELETE r
        """
        await run_tenant_query(
            self.session,
            delete_query,
            {
                "src_id": src_id,
                "tgt_id": tgt_id,
                "tenant_id": self.tenant_id,
            },
            tenant_id=self.tenant_id,
        )

        await self._audit("DELETE_RELATIONSHIP", src_id, rel_type, tgt_id, {})

        return {"status": "ok", "rel_type": rel_type}

    async def _audit(
        self,
        action: str,
        src_id: str,
        rel_type: str,
        tgt_id: str,
        details: dict[str, Any],
    ) -> None:
        audit_query = """
        CREATE (a:AuditEvent {
            id: $id,
            tenant_id: $tenant_id,
            timestamp: $timestamp,
            event_type: $event_type,
            entity_id: $entity_id,
            action: $action,
            agent: $agent,
            details: $details
        })
        """
        await run_tenant_query(
            self.session,
            audit_query,
            {
                "id": str(uuid.uuid4()),
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": "graph_mutation",
                "entity_id": f"{src_id}-{rel_type}->{tgt_id}",
                "action": action,
                "agent": "AuditedGraphMutation",
                "details": details,
            },
            tenant_id=self.tenant_id,
        )

    async def _version_relationship(
        self,
        src_id: str,
        rel_type: str,
        tgt_id: str,
        details: dict[str, Any],
    ) -> None:
        version_query = """
        CREATE (v:RelationshipVersion {
            id: $id,
            tenant_id: $tenant_id,
            src_id: $src_id,
            rel_type: $rel_type,
            tgt_id: $tgt_id,
            timestamp: $timestamp,
            details: $details
        })
        """
        await run_tenant_query(
            self.session,
            version_query,
            {
                "id": str(uuid.uuid4()),
                "tenant_id": self.tenant_id,
                "src_id": src_id,
                "rel_type": rel_type,
                "tgt_id": tgt_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "details": details,
            },
            tenant_id=self.tenant_id,
        )
