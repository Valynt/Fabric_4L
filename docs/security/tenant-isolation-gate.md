# Tenant Isolation Gate

`pnpm test:isolation` is the first-class repository gate for multi-tenant isolation. It promotes tenant isolation from scattered regression coverage into a single blocking signal for pull requests and release readiness.

## What the gate runs

The gate is implemented by `scripts/ci/tenant_isolation_readiness_gate.sh` and groups output by layer/boundary class. It fails on any pytest failure, skip, or xfail in the selected suites.

Required coverage classes:

1. **PostgreSQL RLS tests** — verifies fail-closed `SET LOCAL app.tenant_id`, RLS policy enforcement, and PostgreSQL-only tenant constraints.
2. **Cross-tenant read/write denial tests** — verifies tenants cannot read, mutate, spoof, or confused-deputy into another tenant's data.
3. **API tenant-context propagation tests** — verifies L1-L6 API entrypoints derive tenant context from authenticated/governed context rather than caller-controlled payload hints.
4. **Background job tenant-context tests** — verifies queued/background work carries tenant ownership and cannot run with missing or stale tenant context.
5. **Knowledge graph tenant boundary tests** — verifies graph reads, writes, vector operations, and cross-layer matrix coverage stay tenant-scoped.
6. **Cache-key tenant isolation tests** — verifies Redis/API-key/session/rate-limit cache keys include tenant scope and cannot cross-pollute tenants.

Run it locally with:

```bash
pnpm test:isolation
```

For marker-based selection or to run a larger local audit, use:

```bash
pytest -m tenant_isolation
```

The marker is normalized at collection time from existing `tenant_boundary`, `tenant_matrix`, `cross_tenant_write`, `tenant_mismatch`, and tenant/RLS-oriented test paths so older suites remain discoverable without losing their original markers.

## Artifacts

The gate writes grouped artifacts under `artifacts/security/`:

- `tenant-isolation-summary.md` — human-readable status, commands, JUnit paths, and final result.
- `junit/*.xml` — one JUnit file per layer/boundary group.
- `junit/*.log` — captured pytest output per group.
- `cross_layer_tenant_isolation_matrix.json` — machine-readable cross-layer tenant matrix artifact.

CI uploads these artifacts from the `Tenant Isolation Gate` job when the gate passes or fails.

## How to add a new tenant isolation test

When adding a query, API route, background job, graph operation, or cache key that touches tenant-owned data:

1. Add the test next to the owning layer/service when possible.
2. Mark it explicitly with `@pytest.mark.tenant_isolation`. Keep narrower markers too, such as `tenant_boundary`, `cross_tenant_write`, `requires_postgres`, or `requires_neo4j`, when they apply.
3. Assert hostile behavior, not only happy paths. At minimum, include a Tenant A/Tenant B case proving Tenant A cannot read or mutate Tenant B data.
4. For APIs, assert body/query/header tenant hints are rejected or ignored in favor of authenticated context.
5. For jobs, assert the enqueued payload persists tenant ownership and the worker fails closed when tenant context is missing or mismatched.
6. For graph/cache code, assert every node/edge/query/cache key includes tenant scope and that same logical IDs under different tenants remain isolated.
7. Add the test file to the appropriate suite list in `scripts/ci/tenant_isolation_readiness_gate.sh` if it covers a new boundary not already represented by an existing gate path.
8. Run `pnpm test:isolation` before opening a PR. If the change is infrastructure-gated, also run the direct focused pytest command and record any required local services.

Do not skip tenant isolation tests in the first-class gate. If a test needs live infrastructure, make the CI job provide that infrastructure or split the deterministic contract portion into a non-infra test that still fails closed.
