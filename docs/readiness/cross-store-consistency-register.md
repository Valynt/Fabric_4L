# Cross-Store Consistency Readiness Register

This register defines which data stores are canonical and which stores are derived projections for production readiness validation. It is the source of truth for cross-store consistency gates and incident triage.

## Store classification

| Store | Classification | Canonical ownership | Replay / rebuild rule | Failure inspection |
| --- | --- | --- | --- | --- |
| PostgreSQL service databases | **Canonical** | Tenant-scoped business metadata, document metadata, job state, and durable outbox events. | PostgreSQL writes must commit the canonical row and a projection/outbox event in the same transaction before derived stores are considered authoritative. | Failed canonical writes must not be masked by successful derived indexing. |
| Layer 1 `event_outbox` | **Canonical event log** | Durable downstream event emission for ingestion artifacts such as `SourceCorpus` and `AccountIntelligencePacket`. | Pending or failed events are replayed by idempotent projection adapters until every required derived target is applied or dead-lettered. | `failed` and `dead_letter` rows are the first inspection surface for missing projections. |
| Neo4j knowledge graph | **Derived projection** | Graph nodes and relationships derived from canonical tenant events and extraction outputs. | Rebuild from canonical PostgreSQL/outbox events; projection writes must be idempotent by tenant, aggregate type, and aggregate ID. | Missing graph writes after a PostgreSQL commit are projection failures, not canonical-data loss. |
| Vector indexes / embedding stores | **Derived projection** | Search embeddings derived from canonical documents, entities, and extraction outputs. | Regenerate embeddings from canonical payloads and replay vector upserts idempotently. | Embedding generation failures remain inspectable as failed projection attempts. |
| Object store document blobs | **Derived binary projection** | Binary payloads referenced by canonical PostgreSQL document metadata. | Re-upload or verify blobs from canonical document events and object keys; object-store state without metadata is orphaned. | Orphaned objects or indexes without canonical metadata must be reported and reconciled. |

## Required consistency scenarios

The `gate-database` target must validate these failure modes:

1. A canonical PostgreSQL write succeeds while Neo4j or vector projection fails; replay must later converge the graph/vector projections without duplicating derived rows.
2. A document upload event is canonicalized while embedding generation fails; object-store projection can succeed, and the embedding failure remains inspectable and replayable.
3. Derived indexing appears before canonical metadata commits; the derived record is treated as an orphan and must not become authoritative until the PostgreSQL metadata event exists.
4. Repeated projection failures move the target attempt to a dead-letter state with a stable error for operator inspection.

## Replay mechanism

The repository provides a shared replay contract in `value_fabric.shared.projections.consistency`:

- `CanonicalEvent` models the durable PostgreSQL/outbox event.
- `ProjectionTarget` is the idempotent adapter boundary for Neo4j, vector, embedding, and object-store projections.
- `CrossStoreProjectionRebuilder.replay_pending()` replays pending or failed target attempts.
- `CrossStoreProjectionRebuilder.rebuild_event()` forces an idempotent rebuild for one canonical event.
- `CrossStoreProjectionRebuilder.inspect_failed_projections()` exposes failed and dead-letter projection attempts.
- `CrossStoreProjectionRebuilder.find_orphaned_derived_projections()` reports derived observations that have no canonical PostgreSQL event key.

Layer-specific adapters may use real databases and queues, but they must preserve this contract: PostgreSQL/outbox events are canonical, derived stores are rebuildable, and every failed projection has an inspectable status.

## Gate wiring

Run the local database production readiness gate with:

```bash
make gate-database
```

The gate runs `tests/integration/test_cross_store_consistency.py`, which covers replay, idempotency, orphan detection, and dead-letter inspection without requiring live infrastructure.
