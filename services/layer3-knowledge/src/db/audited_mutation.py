from __future__ import annotations

"""Centralized, audited graph-mutation pipeline for Layer 3.

All relationship writes (CREATE, MERGE, DELETE) should route through this
module so that provenance, versioning, and tenant isolation are enforced
uniformly.

Enhanced for Phase 1 security hardening:
- Node operations (write_node, delete_node)
- Bulk operations (write_nodes_batch, write_relationships_batch, delete_by_source)
- Context enrichment (request_id, account_id, operation_source)
- Metrics integration (mutation rate, failure tracking)
"""


import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..utils.cypher_security import (
    ALLOWED_REL_TYPES,
    TENANT_OWNED_LABELS,
    validate_cypher_identifier,
)
from .query_execution import run_validated_query

try:
    from ..metrics.prometheus_metrics import get_metrics
except Exception:
    get_metrics = None  # type: ignore[assignment]


class AuditedGraphMutation:
    """Mandatory mutation gateway for all graph relationship changes.

    Guarantees:
    1. Relationship types are allowlisted before Cypher interpolation.
    2. Tenant isolation is enforced via ``TenantQueryExecutor``.
    3. Every mutation produces an ``AuditEvent`` node.
    4. Optional relationship versioning via ``RelationshipVersion`` nodes.
    5. Metrics tracking for mutation rate and failures.
    6. Context enrichment (request_id, account_id, operation_source).
    """

    def __init__(
        self,
        tenant_id: str,
        session,
        metrics: Any | None = None,
        request_id: str | None = None,
        account_id: str | None = None,
        operation_source: str | None = None,
    ):
        normalized_tenant_id = str(tenant_id).strip() if tenant_id is not None else ""
        if not normalized_tenant_id:
            raise ValueError("tenant_id is required for audited graph mutations")

        self.tenant_id = normalized_tenant_id
        self.session = session
        self.metrics = metrics or get_metrics()
        self.request_id = request_id
        self.account_id = account_id
        self.operation_source = operation_source

    async def write_relationship(
        self,
        src_id: str,
        rel_type: str,
        tgt_id: str,
        properties: dict[str, Any] | None = None,
        versioned: bool = True,  # Changed to default True for security
    ) -> dict[str, Any]:
        """Merge a relationship between two tenant-scoped nodes and audit the change."""
        validate_cypher_identifier(
            rel_type, ALLOWED_REL_TYPES, kind="relationship type"
        )

        now = datetime.now(UTC).isoformat()
        props = dict(properties or {})

        # Double-check rel_type is allowlisted at runtime (defense-in-depth)
        if rel_type not in ALLOWED_REL_TYPES:
            self._increment_mutation_failure("relationship_type_not_allowed")
            raise ValueError(f"Relationship type '{rel_type}' not in allowlist")

        merge_query = f"""
        MATCH (src {{id: $src_id, tenant_id: $tenant_id}})
        MATCH (tgt {{id: $tgt_id, tenant_id: $tenant_id}})
        MERGE (src)-[r:{rel_type}]->(tgt)
        SET r += $properties, r.updated_at = $now
        RETURN r
        """
        try:
            await run_validated_query(
                self.session,
                merge_query,
                {
                    "src_id": src_id,
                    "tgt_id": tgt_id,
                    "tenant_id": self.tenant_id,
                    "now": now,
                    "properties": props,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.write_relationship",
            )
            self._increment_mutation_success("relationship")
        except Exception:
            self._increment_mutation_failure("relationship_write_error")
            raise

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
        validate_cypher_identifier(
            rel_type, ALLOWED_REL_TYPES, kind="relationship type"
        )

        delete_query = f"""
        MATCH (src {{id: $src_id, tenant_id: $tenant_id}})
              -[r:{rel_type}]->
              (tgt {{id: $tgt_id, tenant_id: $tenant_id}})
        DELETE r
        """
        try:
            await run_validated_query(
                self.session,
                delete_query,
                {
                    "src_id": src_id,
                    "tgt_id": tgt_id,
                    "tenant_id": self.tenant_id,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_relationship",
            )
            self._increment_mutation_success("relationship_delete")
        except Exception:
            self._increment_mutation_failure("relationship_delete_error")
            raise

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
            details: $details,
            request_id: $request_id,
            account_id: $account_id,
            operation_source: $operation_source
        })
        """
        await run_validated_query(
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
                "details": json.dumps(details),
                "request_id": self.request_id,
                "account_id": self.account_id,
                "operation_source": self.operation_source,
            },
            tenant_id=self.tenant_id,
            require_explicit_tenant_id=True,
            query_name="audited_mutation.audit_relationship",
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
        await run_validated_query(
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
            require_explicit_tenant_id=True,
            query_name="audited_mutation.version_relationship",
        )

    # ---------------------------------------------------------------------------
    # Node operations (Phase 1 enhancement)
    # ---------------------------------------------------------------------------

    async def write_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge a tenant-scoped node and audit the change."""
        validate_cypher_identifier(label, TENANT_OWNED_LABELS, kind="node label")
        now = datetime.now(UTC).isoformat()
        props = dict(properties or {})
        props["id"] = node_id
        props["tenant_id"] = self.tenant_id
        props["updated_at"] = now

        merge_query = f"""
        MERGE (n:{label} {{id: $id, tenant_id: $tenant_id}})
        SET n += $properties
        RETURN n
        """
        try:
            await run_validated_query(
                self.session,
                merge_query,
                {
                    "id": node_id,
                    "tenant_id": self.tenant_id,
                    "properties": props,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.write_node",
            )
            self._increment_mutation_success("node")
        except Exception:
            self._increment_mutation_failure("node_write_error")
            raise

        await self._audit_node("WRITE_NODE", label, node_id, props)

        return {"status": "ok", "label": label, "id": node_id}

    async def delete_node(
        self,
        label: str,
        node_id: str,
    ) -> dict[str, Any]:
        """Delete a tenant-scoped node and audit the change."""
        validate_cypher_identifier(label, TENANT_OWNED_LABELS, kind="node label")
        delete_query = f"""
        MATCH (n:{label} {{id: $id, tenant_id: $tenant_id}})
        DETACH DELETE n
        """
        try:
            await run_validated_query(
                self.session,
                delete_query,
                {
                    "id": node_id,
                    "tenant_id": self.tenant_id,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_node",
            )
            self._increment_mutation_success("node_delete")
        except Exception:
            self._increment_mutation_failure("node_delete_error")
            raise

        await self._audit_node("DELETE_NODE", label, node_id, {})

        return {"status": "ok", "label": label, "id": node_id}

    async def _audit_node(
        self,
        action: str,
        label: str,
        node_id: str,
        details: dict[str, Any],
    ) -> None:
        audit_query = """
        CREATE (a:AuditEvent {
            id: $id,
            tenant_id: $tenant_id,
            timestamp: $timestamp,
            event_type: "graph_mutation",
            entity_id: $entity_id,
            action: $action,
            agent: $agent,
            details: $details,
            request_id: $request_id,
            account_id: $account_id,
            operation_source: $operation_source
        })
        """
        await run_validated_query(
            self.session,
            audit_query,
            {
                "id": str(uuid.uuid4()),
                "tenant_id": self.tenant_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": "graph_mutation",
                "entity_id": f"{label}:{node_id}",
                "action": action,
                "agent": "AuditedGraphMutation",
                "details": json.dumps(details, default=str),
                "request_id": self.request_id,
                "account_id": self.account_id,
                "operation_source": self.operation_source,
            },
            tenant_id=self.tenant_id,
            require_explicit_tenant_id=True,
            query_name="audited_mutation.audit_node",
        )

    # ---------------------------------------------------------------------------
    # Bulk operations (Phase 1 enhancement for ingestion)
    # ---------------------------------------------------------------------------

    async def write_nodes_batch(
        self,
        label: str,
        nodes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch merge tenant-scoped nodes and audit the batch operation."""
        validate_cypher_identifier(label, TENANT_OWNED_LABELS, kind="node label")
        now = datetime.now(UTC).isoformat()
        node_count = len(nodes)

        merge_query = f"""
        UNWIND $nodes as node
        MERGE (n:{label} {{id: node.id, tenant_id: $tenant_id}})
        SET n += node.properties
        SET n.updated_at = $now
        RETURN count(n) as merged
        """
        try:
            result = await run_validated_query(
                self.session,
                merge_query,
                {
                    "nodes": [
                        {
                            "id": n.get("id"),
                            "properties": {
                                **n,
                                "tenant_id": self.tenant_id,
                                "updated_at": now,
                            },
                        }
                        for n in nodes
                    ],
                    "tenant_id": self.tenant_id,
                    "now": now,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.write_nodes_batch",
            )
            record = await result.single() if hasattr(result, "single") else None
            processed_count = (
                record.get("merged", node_count)
                if isinstance(record, dict) or hasattr(record, "get")
                else node_count
            )
            self._increment_mutation_success("node_batch")
        except Exception:
            self._increment_mutation_failure("node_batch_error")
            raise

        await self._audit_node(
            "WRITE_NODES_BATCH",
            label,
            f"batch_{node_count}",
            {"count": processed_count, "requested_count": node_count},
        )

        return {"status": "ok", "label": label, "count": processed_count}

    async def write_relationships_batch(
        self,
        rel_type: str,
        triples: list[dict[str, str]],
        versioned: bool = False,
    ) -> dict[str, Any]:
        """Batch merge relationships and audit the batch operation.

        When ``versioned=True``, a ``RelationshipVersion`` node is created for
        every triple in a single UNWIND round trip — mirroring the per-call
        versioning behavior of :meth:`write_relationship` (default ``True``) so
        batch and single paths keep identical provenance.
        """
        validate_cypher_identifier(
            rel_type, ALLOWED_REL_TYPES, kind="relationship type"
        )

        if rel_type not in ALLOWED_REL_TYPES:
            self._increment_mutation_failure("relationship_type_not_allowed")
            raise ValueError(f"Relationship type '{rel_type}' not in allowlist")

        now = datetime.now(UTC).isoformat()
        triple_count = len(triples)

        params: dict[str, Any] = {
            "triples": triples,
            "tenant_id": self.tenant_id,
            "now": now,
        }
        if versioned:
            merge_query = f"""
            UNWIND $triples as triple
            MATCH (src {{id: triple.src_id, tenant_id: $tenant_id}})
            MATCH (tgt {{id: triple.tgt_id, tenant_id: $tenant_id}})
            MERGE (src)-[r:{rel_type}]->(tgt)
            SET r += coalesce(triple.properties, {{}})
            SET r.updated_at = $now
            CREATE (v:RelationshipVersion {{
                id: triple.iid,
                tenant_id: $tenant_id,
                src_id: triple.src_id,
                rel_type: $rel_type,
                tgt_id: triple.tgt_id,
                timestamp: $now,
                details: coalesce(triple.properties, {{}})
            }})
            RETURN count(r) as merged
            """
            params["rel_type"] = rel_type
            # Each version node needs a unique id; enrich a copy so the
            # caller's input list is not mutated.
            params["triples"] = [
                {**t, "iid": str(uuid.uuid4())} for t in triples
            ]
        else:
            merge_query = f"""
            UNWIND $triples as triple
            MATCH (src {{id: triple.src_id, tenant_id: $tenant_id}})
            MATCH (tgt {{id: triple.tgt_id, tenant_id: $tenant_id}})
            MERGE (src)-[r:{rel_type}]->(tgt)
            SET r += coalesce(triple.properties, {{}})
            SET r.updated_at = $now
            RETURN count(r) as merged
            """
        try:
            result = await run_validated_query(
                self.session,
                merge_query,
                params,
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.write_relationships_batch",
            )
            record = await result.single() if hasattr(result, "single") else None
            processed_count = (
                record.get("merged", triple_count)
                if isinstance(record, dict) or hasattr(record, "get")
                else triple_count
            )
            self._increment_mutation_success("relationship_batch")
        except Exception:
            self._increment_mutation_failure("relationship_batch_error")
            raise

        await self._audit(
            "WRITE_RELATIONSHIPS_BATCH",
            f"batch_{triple_count}",
            rel_type,
            f"batch_{triple_count}",
            {"count": processed_count, "requested_count": triple_count},
        )

        return {"status": "ok", "rel_type": rel_type, "count": processed_count}

    async def delete_relationships_batch(
        self,
        rel_type: str,
        triples: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Batch delete relationships and audit the batch operation."""
        validate_cypher_identifier(
            rel_type, ALLOWED_REL_TYPES, kind="relationship type"
        )

        if rel_type not in ALLOWED_REL_TYPES:
            self._increment_mutation_failure("relationship_type_not_allowed")
            raise ValueError(f"Relationship type '{rel_type}' not in allowlist")

        triple_count = len(triples)

        delete_query = f"""
        UNWIND $triples as triple
        MATCH (src {{id: triple.src_id, tenant_id: $tenant_id}})
        MATCH (tgt {{id: triple.tgt_id, tenant_id: $tenant_id}})
        MATCH (src)-[r:{rel_type}]->(tgt)
        DELETE r
        RETURN count(r) as deleted
        """
        try:
            result = await run_validated_query(
                self.session,
                delete_query,
                {
                    "triples": triples,
                    "tenant_id": self.tenant_id,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_relationships_batch",
            )
            record = await result.single() if hasattr(result, "single") else None
            processed_count = (
                record["deleted"]
                if isinstance(record, dict) and "deleted" in record
                else triple_count
            )
            self._increment_mutation_success("relationship_delete_batch")
        except Exception:
            self._increment_mutation_failure("relationship_delete_batch_error")
            raise

        await self._audit(
            "DELETE_RELATIONSHIPS_BATCH",
            f"batch_{triple_count}",
            rel_type,
            f"batch_{triple_count}",
            {"count": processed_count, "requested_count": triple_count},
        )

        return {"status": "ok", "rel_type": rel_type, "count": processed_count}

    async def delete_by_source(
        self,
        source_id: str,
    ) -> dict[str, Any]:
        """Delete all entities and relationships from a specific source."""
        stats = {"relationships_deleted": 0, "entities_deleted": 0}

        # Delete relationships first
        rel_query = """
        MATCH (n)-[r]->(m)
        WHERE n.source_id = $source_id AND n.tenant_id = $tenant_id
        DELETE r
        RETURN count(r) as deleted
        """
        try:
            rel_result = await run_validated_query(
                self.session,
                rel_query,
                {"source_id": source_id, "tenant_id": self.tenant_id},
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_by_source.relationships",
            )
            record = await rel_result.single()
            stats["relationships_deleted"] = record["deleted"] if record else 0
            self._increment_mutation_success("relationship_delete_batch")
        except Exception:
            self._increment_mutation_failure("relationship_delete_batch_error")
            raise

        # Delete entities
        entity_query = """
        MATCH (n)
        WHERE n.source_id = $source_id AND n.tenant_id = $tenant_id
        DELETE n
        RETURN count(n) as deleted
        """
        try:
            entity_result = await run_validated_query(
                self.session,
                entity_query,
                {"source_id": source_id, "tenant_id": self.tenant_id},
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_by_source.entities",
            )
            record = await entity_result.single()
            stats["entities_deleted"] = record["deleted"] if record else 0
            self._increment_mutation_success("node_delete_batch")
        except Exception:
            self._increment_mutation_failure("node_delete_batch_error")
            raise

        await self._audit_node("DELETE_BY_SOURCE", "Source", source_id, stats)

        return {"status": "ok", "source_id": source_id, **stats}

    async def delete_by_request(
        self,
        request_id: str,
    ) -> dict[str, object]:
        """Delete all tenant nodes scoped to a request id (compensation use case).

        Used by the dual-store transaction coordinator's compensating rollback
        to remove nodes created during a failed transaction. Scoping by both
        ``tenant_id`` and ``_request_id`` ensures only nodes from THIS
        transaction are deleted — never unrelated historical entities.
        """
        query = """
        MATCH (n {tenant_id: $tenant_id})
        WHERE n._request_id = $request_id
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """
        try:
            result = await run_validated_query(
                self.session,
                query,
                {"tenant_id": self.tenant_id, "request_id": request_id},
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.delete_by_request",
            )
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0
            self._increment_mutation_success("node_delete_by_request")
        except Exception:
            self._increment_mutation_failure("node_delete_by_request_error")
            raise

        await self._audit_node(
            "DELETE_BY_REQUEST",
            "Request",
            request_id,
            {"deleted_count": deleted_count},
        )

        return {"status": "ok", "deleted_count": deleted_count}

    async def emit_audit_event(
        self,
        action: str,
        entity_id: str,
        details: dict[str, object] | None = None,
        event_type: str = "dual_store_coordinator",
        agent: str = "DualStoreTransactionCoordinator",
    ) -> dict[str, object]:
        """Emit an AuditEvent node through the audited mutation gateway.

        This is the gateway-approved path for audit events produced by the
        dual-store transaction coordinator. Routing through the gateway
        ensures tenant isolation, audit logging, and metrics are enforced.
        """
        audit_id = str(uuid.uuid4())
        audit_query = """
        CREATE (a:AuditEvent {
            id: $id,
            tenant_id: $tenant_id,
            timestamp: $timestamp,
            event_type: $event_type,
            entity_id: $entity_id,
            action: $action,
            agent: $agent,
            details: $details,
            request_id: $request_id,
            account_id: $account_id,
            operation_source: $operation_source
        })
        """
        try:
            await run_validated_query(
                self.session,
                audit_query,
                {
                    "id": audit_id,
                    "tenant_id": self.tenant_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event_type": event_type,
                    "entity_id": entity_id,
                    "action": action,
                    "agent": agent,
                    "details": json.dumps(details or {}, default=str),
                    "request_id": self.request_id,
                    "account_id": self.account_id,
                    "operation_source": self.operation_source,
                },
                tenant_id=self.tenant_id,
                require_explicit_tenant_id=True,
                allow_system_query=True,
                query_name="audited_mutation.emit_audit_event",
            )
            self._increment_mutation_success("audit_event_emit")
        except Exception:
            self._increment_mutation_failure("audit_event_emit_error")
            raise

        return {"status": "ok", "id": audit_id}

    # ---------------------------------------------------------------------------
    # Metrics helpers (Phase 1 enhancement)
    # ---------------------------------------------------------------------------

    def _increment_mutation_success(self, operation_type: str) -> None:
        """Increment mutation success counter."""
        if self.metrics:
            try:
                self.metrics.increment_graph_mutation_success(
                    operation_type=operation_type
                )
            except AttributeError:
                # Metrics may not have this method yet, will add in Phase 3
                pass

    def _increment_mutation_failure(self, error_type: str) -> None:
        """Increment mutation failure counter."""
        if self.metrics:
            try:
                self.metrics.increment_graph_mutation_failure(error_type=error_type)
            except AttributeError:
                # Metrics may not have this method yet, will add in Phase 3
                pass
