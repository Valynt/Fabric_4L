# Tenant Isolation Evidence Summary (Layers 1-6)

Date: 2026-05-18

## Scope

This validation covers:

1. Read/write entrypoints in layer runtime APIs and maintained service wrappers for Layers 1-6.
2. Tenant-context source verification (authenticated request context vs request payload).
3. Hostile tenant-isolation test coverage, with emphasis on:
   - Layer 1 ingestion state
   - Layer 3 retrieval endpoints
   - Layer 4 intelligence routes
   - Layer 6 benchmark usage paths

## Entrypoint Inventory

### Layer runtime API entrypoints

- `value_fabric/layer1/api/routes/` (runtime route module root).
- `value_fabric/layer2/api/routes/` (runtime route module root).
- `value_fabric/layer3/api/routes/` (runtime route module root).
- `value_fabric/layer4/api/routes/` (runtime route module root).
- `services/layer5-ground-truth/src/layer5_ground_truth/api/` (Layer 5 canonical runtime API).
- `value_fabric/layer6/api/routes/` (runtime route module root).

### Maintained service wrapper entrypoints

- Layer 1: `services/layer1-ingestion/src/api/main.py`, `services/layer1-ingestion/src/api/routes/`.
- Layer 2: `services/layer2-extraction/src/layer2_extraction/api/main.py`, `services/layer2-extraction/src/layer2_extraction/api/routes/`.
- Layer 3: `services/layer3-knowledge/src/api/main.py`, `services/layer3-knowledge/src/api/routes/`.
- Layer 4: `services/layer4-agents/src/layer4_agents/api/main.py`, `services/layer4-agents/src/layer4_agents/api/routes/`.
- Layer 5: `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py`, `services/layer5-ground-truth/src/layer5_ground_truth/api/router.py`.
- Layer 6: `services/layer6-benchmarks/src/api/main.py`, `services/layer6-benchmarks/src/api/routes/`.

## Tenant Context Verification

### Priority-path evidence

- Layer 1 ingestion routes are wired through authenticated request context helpers in API wiring (`RequestContext`/request-context dependencies), and tenant-scoped tests exist in service suite.
- Layer 3 retrieval/search routes use context-provided tenant identity and pass tenant scope into retrieval services.
- Layer 4 intelligence/prospect routes use authenticated tenant dependencies (`require_request_context` / verified tenant dependency) and pass tenant IDs into orchestration/service calls.
- Layer 6 benchmark API derives tenant via `_require_tenant_id(ctx)` and forwards tenant scope to repository methods.

### New automated guard

A static hostile regression test was added to fail if priority modules begin sourcing `tenant_id` from request payload fields instead of auth context:

- `tests/security/test_tenant_isolation_priority_paths.py`

## Hostile Cross-Tenant Test Coverage

### Cross-tenant “read/mutate denied” tests present in service suites

- Layer 1: `services/layer1-ingestion/tests/security/test_targets_tenant_isolation.py`, `services/layer1-ingestion/tests/test_cross_tenant_hostile.py`.
- Layer 3: `services/layer3-knowledge/tests/test_cross_tenant_hostile.py`.
- Layer 4: `services/layer4-agents/tests/test_cross_tenant_hostile.py`, plus route/service isolation suites.
- Layer 6: `services/layer6-benchmarks/tests/test_cross_tenant_hostile.py`, `services/layer6-benchmarks/tests/test_repository_tenant_isolation.py`.

### Repo-level security suite additions

- Added priority-path tenant-source guard test in `tests/security/` to enforce auth-context sourcing for highlighted paths.

## Validation commands executed

- `pytest tests/security/test_tenant_isolation_priority_paths.py`

## Residual Risk

- This pass adds a static guard and documents high-value entrypoints; it does not fully enumerate every single route function signature across all API modules.
- Existing dynamic hostile tests in per-service suites remain the primary behavioral proof for cross-tenant read/mutate denial.
