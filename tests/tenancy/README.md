# Tenancy Readiness Suite

## What This Suite Validates

This suite centralizes tenant-safety coverage across API routes, databases, workers, file storage, search indexes, admin impersonation, and billing boundaries.

## Production Risks Covered

- Cross-tenant reads or writes through API, graph, cache, worker, or storage paths.
- Tenant IDs trusted from request bodies instead of authenticated context.
- Admin/support impersonation that is not scoped, justified, or audited.
- Billing objects shared across tenants.

## Existing Coverage Aggregated

- `tests/security/test_tenant_isolation.py`
- `tests/security/test_cross_layer_tenant_isolation_matrix.py`
- `tests/security/test_billing_tenant_boundary.py`
- `services/*/tests/test_api_tenant_propagation.py`
- `services/api/app/tests/test_impersonation_security.py`
- `packages/shared/src/value_fabric/shared/storage/tests/test_tenant_scoping.py`

## Known Gaps

- LIVE_MULTI_TENANT_LOAD: noisy-neighbor live load validation is covered by performance workflows, not this PR-safe suite.
- LIVE_SEARCH_INDEX_REBUILD: full rebuild isolation requires environment-specific graph/vector infrastructure.

## How To Run

```bash
pytest tests/tenancy/
pnpm test:tenancy
```

## CI Artifact

CI should publish `artifacts/production-readiness/tenancy/junit.xml`.

