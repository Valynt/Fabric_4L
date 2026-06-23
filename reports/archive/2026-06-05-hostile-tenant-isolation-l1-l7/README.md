# Hostile Tenant Isolation L1-L7 API Evidence — 2026-06-05

This archive records local hostile tenant isolation evidence for the L1-L7 API matrix.
It is retained because the L7 billing service is now part of the hostile tenant API
coverage set and the repository-owned checks passed for the targeted API evidence.

## Metadata

- UTC date: 2026-06-05
- Command/check name: hostile-tenant-isolation-l1-l7-api
- Commit SHA: recorded in `summary.json`
- Status: pass for targeted L1-L7 hostile API evidence

## Passing evidence

- `python -m pytest --no-mandatory-dep-check tests/security/test_hostile_tenant_e2e_matrix.py tests/security/test_hostile_tenant_journey_contracts.py -v --tb=short`
  - Result: 16 passed in 1.46s.
  - Scope: static hostile API route coverage for L1-L7 plus API gateway, IDOR/RBAC/token abuse markers, safe error contract shape, and denied-action observability hooks.
- `cd services/layer7-billing && python -m pytest tests/test_api_tenant_propagation.py tests/test_cross_tenant_hostile.py tests/test_tenant_isolation.py -v --tb=short`
  - Result: 38 passed, 5 warnings in 1.48s.
  - Scope: L7 billing tenant propagation, hostile read/mutate denial, missing-tenant fail-closed behavior, and repository tenant filters.

## Environment-limited attempts

The full grouped tenant isolation gate was also attempted, but this local environment
could not install or import several full-gate dependencies (`neo4j`, `langgraph`, and
others). The package-index install attempt returned 403 Forbidden for
`pytest-xdist>=3.6.0`. The targeted hostile API evidence above is the retained pass
evidence for this archive.
