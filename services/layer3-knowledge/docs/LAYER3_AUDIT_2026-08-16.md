# Layer 3 Knowledge System Audit — 2026-08-16

## Executive assessment

**Health score: 7.2 / 10.** Layer 3 has substantial defense-in-depth tenant controls,
composite uniqueness constraints, bounded primary retrieval, centralized driver
factories, and broad regression coverage. It is not yet production-proven under
concurrent or partially failing Neo4j workloads. The highest-confidence defects
found in the canonical RDF ingestion path were corrected in this change.

## Architecture and data flow

1. Layer 2 supplies RDF/Turtle plus `source_id`, `extraction_job_id`, and verified
   `tenant_id` to `ingestion/neo4j/orchestrator.py`.
2. `RDFEntityExtractor` and `RDFRelationshipExtractor` map semantic records to
   typed graph nodes and directed ontology relationships. `EmbeddingGenerator`
   attaches vectors to supported node types.
3. `EntityBatchWriter` and `RelationshipBatchWriter` add tenant and lineage
   properties and call `db/audited_mutation.py`.
4. `AuditedGraphMutation` allowlists labels and relationship types, uses
   tenant-scoped endpoint matches and composite `MERGE` keys, and emits audit
   events. `schema/constraints.py` is the canonical constraint/index registry;
   `schema/initializer.py` applies it.
5. `retrieval/vector_store.py` supplies semantic seeds. `retrieval/graph_rag.py`
   expands them with bounded, tenant-filtered traversals and serializes the
   entity/relationship context consumed by Layer 4.

PostgreSQL is authoritative; Neo4j is a rebuildable projection. Graph ingestion,
storage, and retrieval are separated, but entity resolution has two owned
implementations (`schema/entity_resolution.py` and
`services/entity_resolution.py`) and should be consolidated only after contract
and runtime-call analysis.

## Findings by severity

### Critical

No new critical issue was demonstrated in the audited canonical path. This does
not certify production safety because live Neo4j, concurrency, and recovery tests
were unavailable in this environment.

### High

1. **Fixed — ingestion failures were reported as success.**
   `ingestion/neo4j/writers.py` caught database/gateway exceptions and returned
   zero, allowing the orchestrator to finish with a normal result after partial
   writes. Both batch writers and the native compatibility writer now log and
   re-raise storage failures.
2. **Fixed — batch counts always echoed requested rows.**
   `AuditedGraphMutation.write_relationships_batch` returned `len(triples)` even
   when tenant-scoped endpoint `MATCH` clauses eliminated rows. Node and
   relationship batch mutations now consume Neo4j's processed-row count, and
   relationship audit details retain both processed and requested counts. This
   does not distinguish created from matched elements or deduplicate input rows.
3. **Open — the complete RDF import is not one explicit transaction.**
   `BatchImportOrchestrator.load_rdf_graph` shares a session, while each mutation
   and audit call is independently executed. Re-raising failures prevents false
   success but does not roll back earlier entity types if a later batch fails.
   A transaction refactor requires live deadlock/retry and audit-atomicity tests.
4. **Open — several legacy analytics/agent Cypher strings appear unscoped at the
   source level.** Examples include `agents/whitespace_analysis.py`,
   `agents/roi_calculation.py`, `analytics/similarity.py`, and GDS projections in
   `analytics/centrality.py` and `analytics/communities.py`. Runtime query guards
   provide protection on canonical execution seams, but static source ambiguity
   raises bypass and maintainability risk. Do not remove or rewrite these paths
   until callers and compatibility commitments are proven.
5. **Open — relationship endpoint matches omit labels.**
   `AuditedGraphMutation.write_relationships_batch` matches endpoints by
   `(id, tenant_id)` without labels, while uniqueness is guaranteed only per
   label. Same-ID nodes across labels can multiply matches and create unintended
   relationships, and per-label composite indexes cannot serve the unlabeled
   lookup. A safe fix requires validated source/target labels in the ingestion
   contract or a proven global tenant/id invariant.
6. **Open — source deletion does not scope the relationship target.**
   `AuditedGraphMutation.delete_by_source` scopes source node `n` but deletes
   `(n)-[r]->(m)` without requiring `m.tenant_id = $tenant_id`. Legacy or corrupt
   cross-tenant edges could therefore be deleted. A hostile integration fixture
   should precede a query change so reconciliation semantics are explicit.

### Medium

1. **Relationship provenance is mutable rather than append-only.** Reingestion
   updates the `MERGE`d relationship's `source_id`, `extraction_job_id`, and
   `loaded_at`; `RelationshipVersion` and `AuditEvent` preserve history, but
   consumers reading only the material relationship see only the latest lineage.
2. **Audit/version writes are separate from the material mutation.** A failure
   after the relationship `MERGE` can leave a material edge without its audit or
   version record. This is part of the explicit-transaction backlog.
3. **Schema application has multiple historical surfaces.** The canonical
   registry and initializer coexist with migrations 028–030 and standalone
   composite-index scripts. Their intended reconciliation is documented but
   should be verified against a populated upgrade fixture.
4. **Broad traversals are bounded but can still expand rapidly.** Primary
   GraphRAG limits hops to three for entity context and applies tenant predicates
   to every path node. Graph visualization and provenance paths allow larger
   bounds and lack a shared result-cardinality budget.
5. **Duplicate access and model paths remain.** `ingestion/neo4j/connection.py`
   and `db/driver.py` both manage Neo4j connectivity for different callers;
   `schema/entity_resolution.py` and `services/entity_resolution.py` overlap in
   naming and responsibility. Consolidation needs lifecycle and caller evidence.

### Low

1. Ingestion uses `loaded_at` and audited mutations use `updated_at`, both ISO
   strings, while other modules use Neo4j temporal values. The mixed timestamp
   representation increases query and serialization complexity.
2. Requested-versus-processed counts are now retained for relationship audits, but
   there is no dedicated duplicate/missing-endpoint metric or alert.
3. Large route and analytics modules make complete Cypher review difficult even
   though identifier allowlists and execution guards reduce injection risk.

## Implemented changes

- Batch node and relationship mutation responses now report Neo4j's returned
  processed-row cardinality rather than unconditionally echoing input size.
- Relationship batch audit details now expose `count` (processed) and
  `requested_count`, making dropped endpoint matches explainable.
- Entity and relationship writers now fail closed on mutation errors instead of
  returning a normal zero count.
- Regression tests cover reduced database counts and exception propagation.

No API, JSON Schema, graph label, relationship direction, migration, Layer 2
payload, or Layer 4 response contract was changed.

## Cypher and performance evidence

The write whose result is now consumed is:

```cypher
UNWIND $triples AS triple
MATCH (src {id: triple.src_id, tenant_id: $tenant_id})
MATCH (tgt {id: triple.tgt_id, tenant_id: $tenant_id})
MERGE (src)-[r:ALLOWED_TYPE]->(tgt)
SET r += coalesce(triple.properties, {})
RETURN count(r) AS merged
```

The change adds no round trip: it consumes the result already returned by the
existing query. However, the endpoint lookup omits labels, so it cannot rely on
the per-label composite `(id, tenant_id)` indexes and may multiply rows when IDs
overlap across labels. A live `EXPLAIN`/`PROFILE` was not available because this
environment has no Docker/Neo4j runtime; therefore no database-hit or latency
improvement is claimed. The demonstrated improvement is narrower: a two-row
request with one unmatched endpoint now reports one processed relationship row
rather than unconditionally reporting two. Duplicate inputs can still count the
same material element more than once.

Recommended live comparison must profile both the shipped unlabeled lookup and a
candidate validated-label lookup such as:

```cypher
EXPLAIN
UNWIND $triples AS triple
MATCH (src:Capability {id: triple.src_id, tenant_id: $tenant_id})
MATCH (tgt:UseCase {id: triple.tgt_id, tenant_id: $tenant_id})
MERGE (src)-[r:enables]->(tgt)
RETURN count(r) AS merged;
```

Acceptance for a future endpoint-label fix requires index seeks backed by the
composite constraints, no all-node scan, and hostile same-ID/different-label
fixtures that produce exactly one intended edge.

## Validation record

- `make lint-layer3`: passed before the change.
- Canonical `make test-layer3`: initially blocked because the system interpreter
  lacked `pytest_asyncio`; the locked service environment was then installed via
  `uv run --frozen --extra dev`.
- Focused red phase: four intended failures demonstrated suppressed exceptions
  and input-derived counts.
- Focused green phase: all writer and audited-mutation tests passed.
- Targeted ingestion, mutation, tenant-isolation, secured-driver, query-guard,
  retrieval, and migration selection: 118 passed.
- The broad non-live suite completed with 829 passed and one skipped, but 13
  environment/dependency failures remained: two embedding tests could not
  download `sentence-transformers/all-MiniLM-L6-v2` through the restricted
  proxy, and eleven observability checks lacked `prometheus_client` in the
  locked Layer 3 development environment.
- Static Layer 3 OpenAPI/graph contract selection: 32 passed and 16 live-service
  cases skipped after bypassing only the root repository's unrelated mandatory
  dependency preflight.
- Strict mypy of the two changed runtime modules reached imported configuration
  code and was blocked by missing `types-PyYAML` and `types-toml` stubs; no
  changed-module diagnostic was emitted.
- Live Neo4j schema, migration, idempotency, `EXPLAIN`/`PROFILE`, concurrency,
  recovery, pool saturation, and startup checks remain environment-limited
  because the Docker command/runtime is unavailable.

## Small enhancement backlog

| Priority | Classification | Scope | Expected impact | Effort | Risk | Dependencies | Acceptance criteria |
|---|---|---|---|---|---|---|---|
| P0 | Integrity | One explicit transaction per RDF import, including audits | Prevent partial graph/audit state | M | Medium | Neo4j integration fixture; retry policy | Injected mid-batch failure leaves zero material and audit changes; retry succeeds idempotently |
| P0 | Security | Static inventory and migration of unscoped legacy/GDS Cypher | Prove every read and projection is tenant-bound | M | Medium | Runtime caller inventory; GDS tenant projection design | Every active query uses the strict executor; hostile cross-tenant tests pass |
| P0 | Integrity/performance | Carry validated endpoint labels or establish global tenant/id uniqueness | Prevent ambiguous cross-label edges and enable index seeks | M | Medium | Layer 2 boundary compatibility decision | Same-ID nodes across labels create only the intended edge; PROFILE uses composite indexes |
| P0 | Tenant safety | Scope and reconcile `delete_by_source` relationship targets | Prevent deletion across corrupt tenant boundaries | S | Medium | Hostile legacy-data fixture | Cross-tenant edge is preserved or explicitly quarantined; same-tenant source data is deleted |
| P1 | Observability | Missing-endpoint and requested-versus-processed metrics | Detect Layer 2/L3 drift quickly | S | Low | Metrics naming review | Counter and alert fire when processed count is lower than requested |
| P1 | Recovery | Transient Neo4j retry classification at transaction boundary | Safe recovery without duplicate graph state | M | Medium | P0 transaction work | Retryable errors retry with bounded backoff; permanent errors fail once; tests prove both |
| P1 | Migration | Populated upgrade fixture for migrations 028–030 and initializer | Reduce schema drift and rollout risk | M | Low | Neo4j Community and Enterprise CI services | Upgrade is repeatable; constraints/indexes match registry; duplicates produce actionable failure |
| P1 | Performance | Representative `EXPLAIN`/`PROFILE` corpus with budgets | Prevent scans and traversal regressions | M | Low | Seed dataset and live Neo4j CI | Plans use expected indexes and stay within recorded DB-hit/cardinality budgets |
| P2 | Provenance | Append-only assertion-source associations | Preserve multi-source lineage without overwriting latest properties | M | Medium | Provenance contract decision | Reingesting from two sources preserves both trace paths and material assertion remains idempotent |
| P2 | Maintainability | Resolve the two entity-resolution ownership paths | One canonical resolution API | M | Medium | Caller/contract map | All callers use one implementation; behavior and vector-resolution contracts remain green |

## Deferred cross-layer findings

- Layer 2 callers should treat a raised Layer 3 ingestion error as retryable only
  when the classified Neo4j error is transient. No Layer 2 code was modified.
- Layer 4 should continue consuming the existing serialized GraphRAG contract;
  no response-shape issue requiring an adjacent-layer change was demonstrated.
- The `src/agents/` directory contains behavior whose ownership resembles Layer
  4 orchestration. It was recorded, not moved, because compatibility and callers
  were not established.

## Residual production-readiness risks

The service is not certified production-ready by this audit alone. Remaining
evidence gaps are live query plans, populated migration execution, concurrent
upserts, explicit transaction rollback, Neo4j outage/recovery, pool saturation,
cache/graph consistency, and full service startup against production-equivalent
configuration. The corrected failure propagation improves safety immediately but
also makes previously hidden storage failures visible to callers; operators must
confirm retry and alert behavior before rollout.
