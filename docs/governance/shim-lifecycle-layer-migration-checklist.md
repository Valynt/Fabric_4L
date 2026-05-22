# Shim Lifecycle Layer Migration Checklist

This checklist makes compatibility-shim retirement enforceable per layer migration.

## Per-layer migration plan

| Layer | Owner | Target PR milestone | Completion criteria | Hostile-case validation |
|---|---|---|---|---|
| L1 | layer1-ingestion | PR milestone: L1 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer1-ingestion` (or equivalent layer-targeted hostile tests) |
| L3 | layer3-knowledge | PR milestone: L3 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer3-knowledge` |
| L5 | layer5-ground-truth | PR milestone: L5 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer5-ground-truth` |
| L6 | layer6-benchmarks | PR milestone: L6 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer6-benchmarks` |
| L2 | layer2-extraction | PR milestone: L2 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer2-extraction` |
| L4 | layer4-agents | PR milestone: L4 TenantContext migration | (1) all tenant resolution via `TenantContext`; (2) no direct `api_key.tenant_id`; (3) no fallback from request body/query/path tenant values | `pytest -m "tenant_boundary" services/layer4-agents` |

## CI enforcement phases

1. **Phase 1 (warn):** report every legacy `api_key.tenant_id` usage immediately.
2. **Phase 2 (fail-new):** fail PRs that add new non-allowlisted legacy usage.
3. **Phase 3 (fail-all):** fail PRs for any non-allowlisted legacy usage.

Control via `SHIM_LEGACY_ACCESS_PHASE` in CI (`warn`, `fail-new`, `fail-all`).

## PR requirement

When a layer migration is completed, the PR must:

- remove that layer's allowlist entries in `config/ci/legacy_tenant_access_shim_allowlist.yaml`, and
- include hostile-case test evidence for tenant-boundary checks.
