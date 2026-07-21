---
title: "ADR-036: Tenant-Bound Graph Query Execution"
category: "architecture"
audience: "advanced"
last-reviewed: "2026-07-20"
freshness: "current"
related: ["../../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy", "../../explanations/adr/ADR-016-neo4j-for-knowledge-graph-storage", "../../explanations/adr/ADR-035-verified-tenant-context-boundary"]
---

# ADR-036: Tenant-Bound Graph Query Execution

**Status:** Proposed

**Date:** 2026-07-20

**Deciders:** Platform Engineering, Security Team

---

## Context

Layer 3 (Knowledge Graph) uses Neo4j as its graph database (ADR-016). All
application-originated Cypher queries flow through
`services/layer3-knowledge/src/db/query_execution.py`, which is a
critical hotspot with cyclomatic complexity 27, 8 bug fixes in 6 months, and
zero test coverage.

ADR-010 established PostgreSQL RLS for relational tenant isolation, but
PostgreSQL RLS cannot protect Neo4j queries. The graph layer requires its own
tenant-boundary mechanism. Currently, tenant scoping in Cypher queries is
implemented through string interpolation and parameter passing, but there is no
structural guarantee that a query is tenant-scoped — a query can contain a
`tenant_id` parameter without using it in a filtering predicate.

This ADR defines the architectural boundary for tenant-safe graph query
execution, independent of PostgreSQL RLS.

## Decision

### Architectural Rule

All application-originated graph operations execute through a tenant-bound
query boundary. Query values are parameterized; structural query elements are
selected only from approved templates or allowlists. The boundary rejects
operations without demonstrable tenant predicates.

### Tenant-Bound Query Boundary

Application code does not submit arbitrary Cypher directly. A query boundary
layer receives a trusted TenantContext (per ADR-035), injects tenant predicates
through structured query construction, and rejects unscoped operations.

The boundary is the single entry point for all application-originated graph
queries. Direct Neo4j driver access from application code outside the boundary
is prohibited.

### Parameterization Scope

Cypher parameters are used for values (literals, IDs, limits, offsets).
Structural elements that cannot be parameterized — labels, relationship types,
property names, structural query fragments — must use:

- **Allowlists:** A predefined set of allowed labels, relationship types, and
  property names. Unlisted elements are rejected.
- **Typed query builders:** Programmatic constructors that produce valid Cypher
  from structured inputs.
- **Predeclared templates:** Parameterized query templates registered with the
  boundary, selected by name with injected parameters.

The statement "parameterized queries only" does not solve every injection path.
Structural elements require separate controls.

### Tenant Predicate Enforcement

The boundary must verify that the graph operation is *scoped* by tenant, not
merely that a `tenant_id` parameter exists. A query like the following is
rejected because the tenant_id is not used in a filtering predicate:

```cypher
MATCH (n) RETURN n, $tenant_id
```

A valid query uses the tenant_id in a `WHERE` clause or pattern match:

```cypher
MATCH (n:Entity {tenant_id: $tenant_id}) RETURN n
```

### Read and Write Enforcement

Tenant scoping applies to all graph operations:

- `MATCH` — read queries must include tenant predicate
- `MERGE` — upsert must include tenant predicate in the match pattern
- `CREATE` — new nodes/relationships must include tenant_id property
- `SET` — property updates must be on tenant-scoped nodes
- `DELETE` — deletions must be on tenant-scoped nodes
- Subqueries — must inherit or re-establish tenant scope
- Procedures — must accept and enforce tenant scope
- Traversals — variable-length paths must not cross tenant boundaries

### Graph Schema Invariant

Every tenant-owned node and relationship carries a `tenant_id` property, backed
by constraints and indexes where Neo4j supports them. This is a schema-level
invariant, not just a query-level convention.

### Restricted Escape Hatch

Administrative cross-tenant queries (migration, repair, analytics) use a
separate interface with:

- Explicit authorization (privileged dependency per ADR-035 endpoint class 4)
- Audit logging of all cross-tenant operations
- No access from standard application code paths

This is not a bypass of the tenant boundary — it is a distinct, audited path
for authorized administrative operations.

### Depth Validation

The boundary controls traversal fanout, variable-length path depth, and nested
query complexity. The specific threats being controlled are:

1. **Traversal fanout:** Unbounded variable-length paths that exhaust memory
2. **Variable-length path depth:** Deep traversals that degrade performance
3. **Nested query complexity:** Deeply nested subqueries or `CALL` clauses

The implementation approach (AST analysis, query DSL, pattern matching) is an
implementation detail, but the boundary must address all three threats.

### Neo4j Enforcement Is Separate from PostgreSQL RLS

PostgreSQL RLS cannot protect a Neo4j query. This ADR scopes its enforcement to
Neo4j graph operations only. PostgreSQL controls are covered by ADR-010 and
ADR-035. The two enforcement mechanisms are independent and complementary.

## Alternatives Considered

### Application-level tenant filtering in Cypher strings

- **Pros:** Simple to implement; no boundary layer needed; full Cypher flexibility.
- **Cons:** String interpolation enables Cypher injection; developer can forget `WHERE` clause; no structural guarantee of scoping; impossible to verify completeness via static analysis.
- **Why rejected:** No structural guarantee of tenant scoping; injection risk from string interpolation; inconsistent application across developers.

### PostgreSQL RLS as sole tenant boundary

- **Pros:** Single enforcement mechanism; well-understood.
- **Cons:** RLS does not apply to Neo4j; graph and relational enforcement are independent storage surfaces.
- **Why rejected:** Architecturally impossible — RLS is a PostgreSQL feature with no jurisdiction over Neo4j queries.

### Parameter presence check only

- **Pros:** Simple to verify; fast runtime check.
- **Cons:** A query can contain `$tenant_id` without using it in a predicate; presence does not imply scoping.
- **Why rejected:** Does not guarantee tenant isolation — a query returning all nodes with a tenant_id column is not tenant-scoped.

### No escape hatch (all queries strictly tenant-scoped)

- **Pros:** Simplest model; no administrative path to audit.
- **Cons:** Administrative operations (migration, repair, cross-tenant analytics) require a controlled path; prohibiting it leads to unsafe workarounds (direct driver access, disabling checks).
- **Why rejected:** Operational reality requires administrative access; a controlled, audited path is safer than prohibition.

### Conditions for revisiting

- If Neo4j introduces native row-level security or tenant isolation features, the boundary implementation may simplify but the architectural rule remains.
- If the platform moves to a different graph database, the boundary abstraction should be portable; the specific Cypher controls would need revision.

## Consequences

### Positive

- **Eliminates injection vectors:** Parameterization for values, allowlists for structural elements.
- **Tenant isolation by construction:** Unscoped operations are rejected at the boundary — no reliance on developer discipline.
- **Administrative operations are auditable:** Cross-tenant queries use a separate, logged interface.
- **Independent of PostgreSQL RLS:** Graph enforcement does not depend on relational database configuration.

### Negative

- **Migration effort:** Existing queries using string interpolation must be rewritten to use the boundary.
- **Reduced flexibility:** Ad hoc Cypher must go through query builder or template registration.
- **Validator false positives:** During migration, the boundary may reject queries that are safe but do not match expected patterns.
- **Additional overhead:** Mandatory tenant predicates and validation add per-query cost.

## Compliance and Migration

### Existing noncompliant paths

`services/layer3-knowledge/src/db/query_execution.py` — all current queries bypass
the tenant-bound query boundary. String interpolation is used for query
construction. Zero test coverage on the current module.

### Migration owner

Platform Engineering

### Enforcement mechanism

- **Runtime:** Query boundary rejects unscoped operations (planned).
- **Static analysis:** Test suite verifying scoped/unscoped query behavior (planned).
- **CI gate:** `mandatory-security-regression` integration (planned).

### Exception process

Administrative cross-tenant queries use the restricted escape hatch with
privileged dependency and audit logging.

### Rollback strategy

The boundary is a new layer; existing query execution remains available until
all queries are migrated. Rollback removes the boundary and restores direct
query execution.

### Evidence required to transition to Accepted

- Tenant-bound query boundary module implemented
- All application-originated queries route through the boundary
- Test suite: unscoped queries rejected, scoped queries pass, parameter-only-without-predicate rejected
- Administrative escape hatch tested with audit log verification
- CI gate integration complete

## Current Enforcement (Exists)

- Neo4j tenant constraints on some node labels (partial)
- `CypherDepthLimitExceeded` exception and `MAX_QUERY_DEPTH` constant (fragile, text-based)

## Planned Enforcement (Not Yet Existing)

- Tenant-bound query boundary module
- Structural query element allowlists
- Test suite for scoped/unscoped query behavior
- CI gate integration with `mandatory-security-regression`

## References

- ADR-010: PostgreSQL RLS for Multi-Tenancy (relational enforcement, separate from this ADR)
- ADR-016: Neo4j for Knowledge Graph Storage
- ADR-035: Verified Tenant Context Boundary (provides the TenantContext this ADR consumes)
- `services/layer3-knowledge/src/db/query_execution.py` (current implementation — motivates this ADR)
