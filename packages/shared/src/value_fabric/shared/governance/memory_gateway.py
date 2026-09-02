"""MemoryGateway — provenance-tracked retrieval proxy.

Wraps Layer 3 retrieval engines (GraphRAGEngine, HybridSearch) with:
1. Content hashing for provenance tracking
2. Source lineage recording
3. Audit event emission (MEMORY_ACCESS)
4. Replay snapshot integration

Agents MUST use ``MemoryGateway.query()`` instead of calling retrieval
engines directly.

GATE Framework §3.1 — MemoryGateway
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.audit.models import (
    AuditAction,
    AuditOutcome,
    MemoryAccessRecord,
)
from value_fabric.shared.crypto.canonical import canonical_hash

logger = logging.getLogger(__name__)


class MemoryGateway:
    """Provenance-tracked retrieval gateway.

    Wraps a retrieval engine and records content hashes, source lineage,
    and audit events for every retrieval operation.

    Args:
        retrieval_engine: GraphRAGEngine or HybridSearch instance.
        tenant_id: Tenant context for multi-tenant retrieval.
        agent_id: Agent identifier for audit attribution.
        trace_id: Trace ID for audit correlation.
        source_blocklist: Optional set/list of source IDs to filter out.
    """

    def __init__(
        self,
        retrieval_engine: Any,
        tenant_id: str,
        agent_id: str | None = None,
        trace_id: str | None = None,
        source_blocklist: list[str] | set[str] | None = None,
        policy_facade: Any | None = None,
    ) -> None:
        self._engine = retrieval_engine
        self._tenant_id = tenant_id
        self._agent_id = agent_id
        self._trace_id = trace_id
        self._source_blocklist: set[str] = set(source_blocklist or [])
        self._access_log: list[dict[str, Any]] = []
        self._policy_facade = policy_facade

    @staticmethod
    def _decision_allows(decision: Any) -> bool:
        """Normalize a policy-facade decision into an allow/deny boolean."""
        effect = getattr(decision, "effect", None)
        if effect is not None:
            value = getattr(effect, "value", effect)
            if isinstance(value, str):
                normalized = value.strip().upper()
                if normalized in {"ALLOW", "ALLOWED"}:
                    return True
                if normalized in {"DENY", "DENIED", "INDETERMINATE"}:
                    return False

        if isinstance(getattr(decision, "allowed", None), bool):
            return bool(decision.allowed)
        if isinstance(getattr(decision, "denied", None), bool):
            return not bool(decision.denied)
        if isinstance(getattr(decision, "indeterminate", None), bool):
            return not bool(decision.indeterminate)

        return False

    async def _enforce_policy(self, *, action: str, resource: str, input_data: dict[str, Any]) -> None:
        """Fail closed before a memory call is allowed through."""
        if not self._tenant_id or self._tenant_id in {"unknown", "None", "null", ""}:
            raise PermissionError("Memory access denied: tenant context is required.")
        if self._policy_facade is None:
            raise PermissionError("Memory access denied: policy enforcement is unavailable.")

        decision = await self._policy_facade.evaluate_action(
            action=action,
            resource=resource,
            tenant_id=self._tenant_id,
            actor_id=self._agent_id,
            input_data=input_data,
            trace_id=self._trace_id,
        )
        if not self._decision_allows(decision):
            reason = getattr(decision, "reason", None) or "Policy denied"
            raise PermissionError(f"Memory access denied: {reason}")

    @property
    def access_log(self) -> list[dict[str, Any]]:
        """Read-only access to the retrieval log for replay recording."""
        return list(self._access_log)

    async def query(
        self,
        query_text: str,
        entity_type: str | None = None,
        max_hops: int | None = None,
        min_confidence: float | None = None,
        max_results: int = 10,
        source_blocklist: list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        """Execute a provenance-tracked retrieval query.

        Delegates to the underlying retrieval engine, then computes
        content hashes and emits a MEMORY_ACCESS audit event.

        Args:
            query_text: Natural language query.
            entity_type: Filter by entity type.
            max_hops: Maximum graph traversal hops.
            min_confidence: Minimum confidence threshold.
            max_results: Maximum number of results.
            source_blocklist: Optional per-call override of blocked source IDs.

        Returns:
            Retrieval result with provenance metadata added.
        """
        await self._enforce_policy(
            action="memory.query",
            resource="memory",
            input_data={
                "query_text": query_text,
                "entity_type": entity_type,
                "max_hops": max_hops,
                "min_confidence": min_confidence,
                "max_results": max_results,
            },
        )

        # Execute retrieval
        result = await self._engine.query(
            query_text=query_text,
            entity_type=entity_type,
            max_hops=max_hops,
            min_confidence=min_confidence,
            max_results=max_results,
        )

        # Normalize result to dict
        if hasattr(result, "__dataclass_fields__"):
            # GraphRAGResult is a dataclass
            result_dict = {
                "query": result.query,
                "entities": result.entities,
                "relationships": result.relationships,
                "context_graph": result.context_graph,
                "traversal_path": result.traversal_path,
                "confidence_score": result.confidence_score,
                "sources": result.sources,
            }
        elif isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {"raw": str(result)}

        # Apply source blocklist before provenance computation
        result_dict = self._apply_source_blocklist(result_dict, source_blocklist)

        # Compute content hash for provenance
        content_hash = canonical_hash(result_dict)

        # Build source lineage
        source_lineage = self._build_source_lineage(result_dict)

        # Record access
        entity_count = len(result_dict.get("entities", []))
        relationship_count = len(result_dict.get("relationships", []))

        log_entry = {
            "query": query_text,
            "content_hash": content_hash,
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "source_lineage": source_lineage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._access_log.append(log_entry)

        # Emit audit event
        await self._emit_memory_access_audit(
            query=query_text,
            content_hash=content_hash,
            source_lineage=source_lineage,
            entity_count=entity_count,
            relationship_count=relationship_count,
        )

        # Enrich result with provenance metadata
        result_dict["_provenance"] = {
            "content_hash": content_hash,
            "source_lineage": source_lineage,
            "tenant_id": self._tenant_id,
            "agent_id": self._agent_id,
            "trace_id": self._trace_id,
            "retrieved_at": log_entry["timestamp"],
        }

        return result_dict

    async def get_entity_context(
        self,
        entity_id: str,
        hops: int = 2,
        relationship_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Provenance-tracked entity context retrieval.

        Args:
            entity_id: Central entity ID.
            hops: Number of relationship hops.
            relationship_types: Optional relationship type filter.

        Returns:
            Entity context with provenance metadata.
        """
        await self._enforce_policy(
            action="memory.entity_context",
            resource=f"entity:{entity_id}",
            input_data={
                "entity_id": entity_id,
                "hops": hops,
                "relationship_types": relationship_types,
            },
        )

        result = await self._engine.get_entity_context(
            entity_id=entity_id,
            tenant_id=self._tenant_id,
            hops=hops,
            relationship_types=relationship_types,
        )

        content_hash = canonical_hash(result)
        source_lineage = [{"entity_id": entity_id, "type": "entity_context"}]

        log_entry = {
            "query": f"entity_context:{entity_id}",
            "content_hash": content_hash,
            "entity_count": result.get("entity_count", 0),
            "relationship_count": result.get("relationship_count", 0),
            "source_lineage": source_lineage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._access_log.append(log_entry)

        await self._emit_memory_access_audit(
            query=f"entity_context:{entity_id}",
            content_hash=content_hash,
            source_lineage=source_lineage,
            entity_count=result.get("entity_count", 0),
            relationship_count=result.get("relationship_count", 0),
        )

        result["_provenance"] = {
            "content_hash": content_hash,
            "source_lineage": source_lineage,
            "tenant_id": self._tenant_id,
            "agent_id": self._agent_id,
            "trace_id": self._trace_id,
            "retrieved_at": log_entry["timestamp"],
        }

        return result

    def _apply_source_blocklist(
        self,
        result_dict: dict[str, Any],
        override_blocklist: list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        """Filter out entities and relationships from blocked sources."""
        if override_blocklist is not None:
            if isinstance(override_blocklist, str):
                raise TypeError("source_blocklist must be a list or set, not a string")
            blocklist = set(override_blocklist)
        else:
            blocklist = self._source_blocklist
        if not blocklist:
            return result_dict

        allowed_entities = [
            e for e in result_dict.get("entities", [])
            if not self._is_blocked(e, blocklist)
        ]
        allowed_ids = {e.get("id") for e in allowed_entities if e.get("id")}

        allowed_relationships = [
            r for r in result_dict.get("relationships", [])
            if r.get("source") in allowed_ids and r.get("target") in allowed_ids
        ]

        result_dict["entities"] = allowed_entities
        result_dict["relationships"] = allowed_relationships
        return result_dict

    @staticmethod
    def _is_blocked(entity: dict[str, Any], blocklist: set[str]) -> bool:
        """Return True if the entity belongs to a blocked source."""
        source_id = entity.get("source_id") or entity.get("provenance_source")
        return bool(source_id and source_id in blocklist)

    @staticmethod
    def _build_source_lineage(result_dict: dict[str, object]) -> list[dict[str, object]]:
        """Extract source lineage from retrieval results."""
        lineage: list[dict[str, object]] = []

        # Extract from sources list
        for source in result_dict.get("sources", []):
            lineage.append({"source": source, "type": "graph_source"})

        # Extract entity IDs as lineage
        for entity in result_dict.get("entities", [])[:5]:  # Cap at 5
            entity_id = entity.get("id") or entity.get("name", "unknown")
            lineage.append({"entity_id": str(entity_id), "type": "entity"})

        return lineage

    async def _emit_memory_access_audit(
        self,
        query: str,
        content_hash: str,
        source_lineage: list[dict[str, object]],
        entity_count: int,
        relationship_count: int,
    ) -> None:
        """Emit MEMORY_ACCESS audit event."""
        record = MemoryAccessRecord(
            query=query,
            tenant_id=self._tenant_id,
            agent_id=self._agent_id,
            content_hash=content_hash,
            source_lineage=source_lineage,
            entity_count=entity_count,
            relationship_count=relationship_count,
            trace_id=self._trace_id,
        )
        # WARNING: asyncio.create_task() risks silent loss on shutdown.
        # Using await to ensure audit events are reliably committed.
        await emit_audit_event(
            action=AuditAction.MEMORY_ACCESS,
            outcome=AuditOutcome.SUCCESS,
            resource_type="knowledge_graph",
            resource_id=content_hash[:16],
            request_id=self._trace_id,
            details=record.model_dump(),
            chain_id=f"{self._tenant_id}:memory",
        )
