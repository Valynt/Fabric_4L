# Layer 3 Integrity Audit and Bounded Optimization Design

## Objective

Audit the canonical Layer 3 graph ingestion, schema, retrieval, tenant-isolation,
and boundary surfaces, then fix only defects that can be demonstrated with
focused tests. PostgreSQL remains authoritative and Neo4j remains a rebuildable,
tenant-scoped projection.

## Considered approaches

1. **Targeted integrity hardening (selected).** Preserve the graph model and
   mutation gateway, correct misleading ingestion outcomes, and add regression
   evidence. This has the smallest compatibility and operational risk.
2. **Transactional ingestion rewrite.** Move the complete RDF load into one
   explicit transaction. This would improve atomicity but requires redesigning
   session and transaction protocols and is too broad without live concurrency
   evidence.
3. **Schema and query overhaul.** Consolidate labels, access paths, and indexes.
   This could improve long-term maintainability but risks semantic and contract
   drift and cannot be justified by the available baseline.

## Architecture and data flow

Layer 2 RDF enters `BatchImportOrchestrator`, which validates tenant context,
extracts typed nodes and relationships, attaches embeddings, and delegates to
tenant-aware batch writers. The writers use `AuditedGraphMutation`; that gateway
allowlists interpolated labels and relationship types, scopes endpoint matches
by tenant, performs idempotent `MERGE` operations, and emits audit metadata.
Layer 3 retrieval uses vector search for seeds and bounded, tenant-scoped graph
traversal for context consumed by Layer 4.

The selected change keeps these boundaries intact. Batch mutations will report
the count actually returned by Neo4j rather than the input cardinality, and
writer failures will propagate to the orchestrator instead of being converted
into false zero-success results. This makes missing relationship endpoints and
database failures observable without changing API schemas or graph semantics.

## Correctness and failure behavior

- A batch relationship `MERGE` may match fewer rows than supplied when an
  endpoint is absent. The mutation result must use Neo4j's `merged` count.
- Batch node results likewise use Neo4j's returned count rather than assuming
  every input row was written.
- Neo4j or audited-mutation failures fail the ingestion operation. Logging is
  retained, but exceptions are re-raised so callers can retry and operators do
  not receive a successful response for a partial load.
- Tenant validation, identifier allowlists, relationship direction, provenance
  properties, and public response shapes remain unchanged.

## Testing and evidence

Focused asynchronous tests will first demonstrate that current code reports
input counts and suppresses failures. Tests will then require database-returned
counts and propagated exceptions. Existing idempotency, schema, retrieval,
tenant, and contract suites remain the regression boundary. Live Neo4j tests
and query-plan checks will be run when Docker and the integration environment are
available; mocked tests will not be described as production validation.

## Scope exclusions

This change does not redesign graph labels, introduce migrations, alter Layer 2
or Layer 4, change contracts, or claim full transaction atomicity. Those items
remain audit findings or independently deliverable backlog work.
