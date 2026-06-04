# Tenancy Readiness Suite

## What This Suite Validates

This suite centralizes tenant-safety coverage across API routes, databases, workers, file storage, search indexes, admin impersonation, and billing boundaries. It is both an aggregation gate and an invariant coverage gate: each domain must point at discoverable pytest coverage and must prove that the expected tenant-isolation controls are represented.

## Production Risks Covered

- Cross-tenant reads or writes through API, graph, cache, worker, or storage paths.
- Tenant IDs trusted from request bodies instead of authenticated context.
- Admin/support impersonation that is not scoped, justified, or audited.
- Billing objects shared across tenants.
- Tenant-isolation coverage drift where detailed tests still exist but no longer prove the required production controls.

## Existing Coverage Aggregated

- `tests/security/test_tenant_isolation.py`
- `tests/security/test_cross_layer_tenant_isolation_matrix.py`
- `tests/security/test_billing_tenant_boundary.py`
- `services/*/tests/test_api_tenant_propagation.py`
- `services/api/app/tests/test_impersonation_security.py`
- `packages/shared/src/value_fabric/shared/storage/tests/test_tenant_scoping.py`

## Invariant Controls

- Positive own-tenant authorization cases exist where reads or writes are allowed.
- Cross-tenant reads and writes are denied or hidden.
- Missing tenant context fails closed on tenant-owned data paths.
- Request body, header, storage metadata, and vector metadata tenant spoofing cannot override authenticated context.
- Worker/job entrypoints carry tenant context and cannot process another tenant's records.
- Admin/support impersonation is permissioned, tenant-scoped, justified, and audited.

## Known Gaps

- LIVE_INFRASTRUCTURE_REPLAY: this suite is intentionally PR-safe and does not require live PostgreSQL, Neo4j, object storage, Stripe, or Celery workers.
- LIVE_MULTI_TENANT_LOAD: noisy-neighbor live load validation is covered by performance workflows, not this PR-safe suite.
- LIVE_SEARCH_INDEX_REBUILD: full rebuild isolation requires environment-specific graph/vector infrastructure.

## How To Run

```bash
pytest tests/tenancy/
pnpm test:tenancy
```

## CI Artifact

CI should publish `artifacts/production-readiness/tenancy/junit.xml`.
