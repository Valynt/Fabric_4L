# Tenant Isolation

Tenant isolation is a first-class security gate for Value Fabric. The gate proves
that tenant context is extracted once, propagated through API routes, repository
queries, background jobs, graph operations, and cache keys, and enforced by the
persistence layer where possible.

## First-class gate

Run the full tenant isolation gate from the repository root:

```bash
pnpm test:isolation
```

The command delegates to `scripts/ci/tenant_isolation_readiness_gate.sh`, writes
JUnit/log/summary artifacts under `artifacts/security/`, and groups failures by
control surface:

1. **Platform/API** — cross-tenant read/write denial and tenant-context propagation.
2. **Layer 1 PostgreSQL** — RLS, `SET LOCAL app.tenant_id`, and fail-closed database access.
3. **Layer 1 background jobs** — tenant context propagation through Celery/job handlers.
4. **Layer 3 knowledge graph** — tenant-scoped Cypher query and write enforcement.
5. **Shared cache/rate limits** — tenant-prefixed cache keys and tenant-scoped invalidation.

The marker-equivalent profile is also available:

```bash
pytest -m tenant_isolation
```

Use `pytest -m tenant_isolation` for local selection and focused debugging. Use
`pnpm test:isolation` for merge/release evidence because it enforces required
suite presence, grouped output, no skipped/xfail tests in the gate JUnit, and the
cross-layer tenant-isolation matrix artifact.

## Required invariant

A test belongs in the tenant isolation gate when a regression could allow any of
the following:

- A query returns rows, documents, graph nodes, benchmark records, truth objects,
  or agent state owned by another tenant.
- An API route trusts a request body/header tenant ID over authenticated context.
- A repository/service method omits `tenant_id` filtering or accepts an unscoped
  session for tenant-owned data.
- A background job runs without the tenant context required to scope reads and
  writes.
- A graph read/write uses unscoped Cypher or permits spoofed `tenant_id`
  parameters.
- A Redis/cache/session/rate-limit key can be read, poisoned, or invalidated
  across tenants.

## PostgreSQL RLS model

Tenant-owned PostgreSQL tables must fail closed and use row-level security where
applicable:

```sql
CREATE POLICY tenant_isolation_policy ON tenant_owned_table
FOR ALL
USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

The application must set the tenant inside the transaction before tenant-scoped
queries:

```sql
SET LOCAL app.tenant_id = '<authenticated-tenant-uuid>';
```

Tests should cover missing tenant context, invalid tenant context, same-tenant
success, cross-tenant read denial, cross-tenant write denial, and transaction
context persistence.

## How to add a new tenant isolation test

1. Put the test next to the control surface it protects:
   - API/auth propagation: `tests/security/` or `tests/context/`
   - Layer 1 RLS/jobs: `services/layer1-ingestion/tests/security/`
   - Layer 3 graph boundaries: `tests/security/` or `tests/layer3/`
   - Cache-key isolation: `tests/cache/`
   - Layer-specific repository/API hostile cases: the service's `tests/` tree
2. Mark it with at least one of these markers:
   - `@pytest.mark.tenant_isolation` for all first-class gate tests.
   - `@pytest.mark.tenant_boundary` for hostile cross-tenant read/write tests.
   - `@pytest.mark.tenant_matrix` when it contributes to the cross-layer matrix.
   - `@pytest.mark.cross_tenant_write` for hostile write attempts.
   - Add infra markers such as `requires_postgres`, `requires_redis`, or
     `requires_neo4j` only when the test truly requires live infrastructure.
3. Seed data for at least two tenants in the same persistence/cache/graph scope.
4. Assert both sides of the invariant: same-tenant access succeeds and
   cross-tenant access fails or returns no data.
5. If the test is required in `pnpm test:isolation`, add its file to the matching
   suite array in `scripts/ci/tenant_isolation_readiness_gate.sh` so output stays
   grouped by layer/control surface.
6. Run:

```bash
pnpm test:isolation
pytest -m tenant_isolation
```

Do not weaken or skip tenant-isolation tests to make CI pass. If local
infrastructure is missing, start the documented test stack or run the hermetic
subset while clearly reporting the omitted infra-backed coverage.
