# Tenant Isolation

Tenant isolation is a first-class security gate for Fabric 4L. The gate covers
database RLS, cross-tenant read/write denial, API tenant-context propagation,
background job tenant context, knowledge graph tenant boundaries, L7 billing
API hostile checks, and cache-key isolation.

## Commands

```bash
# First-class grouped gate used by local validation and CI
pnpm test:isolation

# Marker-based selection for ad hoc investigation
pytest -m tenant_isolation -v --tb=short

# Collection audit for marker coverage
pytest -m tenant_isolation --collect-only -q
```

`pnpm test:isolation` runs `scripts/ci/run_tenant_isolation_gate.py`. The runner
prints failures by group and writes machine-readable evidence to:

```text
artifacts/tenant-isolation/summary.json
artifacts/tenant-isolation/archive/<YYYY-MM-DD>-hostile-tenant-isolation-l1-l7-api/summary.json
```

## Marker Rules

- Use `@pytest.mark.tenant_isolation` for new tests that must be part of the
  first-class gate.
- Existing `tenant_boundary`, `tenant_matrix`, and `cross_tenant_write` tests are
  automatically included in the `tenant_isolation` marker during collection.
- Infrastructure-backed tests should keep their infra markers, such as
  `requires_postgres`, `requires_redis`, or `requires_neo4j`.
- Do not skip tenant isolation tests in CI because infrastructure is absent. CI
  jobs that run the gate must provide PostgreSQL, Redis, and Neo4j where needed.

## Required Coverage

Every tenant-owned data path should have coverage for the relevant scenarios:

- Tenant A cannot read Tenant B data.
- Tenant A cannot mutate Tenant B data.
- Missing tenant context fails closed.
- Request-body or header tenant spoofing cannot override authenticated context.
- Repository, query, cache, graph, or job operations receive tenant context from
  trusted context, not from user-controlled payload fields.

## Where To Add Tests

- PostgreSQL RLS and background jobs: service-local security tests, for example
  `services/layer1-ingestion/tests/security/`.
- Cross-tenant API read/write denial: service-local `test_cross_tenant_hostile.py`
  and `test_api_tenant_propagation.py`.
- Knowledge graph tenant boundaries: `services/layer3-knowledge/tests/` plus
  hostile graph regressions under `tests/security/`.
- Layer 4 workflow, checkpoint, and agent job context: `services/layer4-agents/tests/`.
- Ground Truth, Benchmarks, and Billing repository/API boundaries: the Layer 5,
  Layer 6, and Layer 7 service test packages.
- Cache and rate-limit key isolation: `tests/cache/` or shared identity tests.

When adding a new required file or node-id, update
`scripts/ci/run_tenant_isolation_gate.py` and the auto-marking inventory in root
`conftest.py` so `pnpm test:isolation` and `pytest -m tenant_isolation` remain
aligned.
