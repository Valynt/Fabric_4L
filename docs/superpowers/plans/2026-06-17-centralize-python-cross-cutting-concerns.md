# Sub-plan C: Centralize Cross-Cutting Python Concerns (#5)

**Goal:** Move duplicated bootstrap, logging, tenant context, and database-session logic into `packages/shared/` so every service consumes a single implementation.

**Canonical home**
- `packages/shared/src/value_fabric/shared/fastapi_framework/` — bootstrap, middleware, health endpoints.
- `packages/shared/src/value_fabric/shared/observability/structured_logging.py` — logging config.
- `packages/shared/src/value_fabric/shared/identity/context.py` — single `RequestContext`.
- `packages/shared/src/value_fabric/shared/database/tenant_validation.py` — single tenant validation/RLS implementation.

**Files to inspect / modify**
- `services/layer2-extraction/src/layer2_extraction/shared_bootstrap.py`
- `services/layer6-benchmarks/src/layer6_benchmarks/shared_bootstrap.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/shared_bootstrap.py`
- `services/layer2-extraction/src/layer2_extraction/logging_config.py`
- `services/layer6-benchmarks/src/layer6_benchmarks/logging_config.py`
- `services/layer3-knowledge/src/logging_config.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py`
- `packages/shared/src/value_fabric/shared/identity/context.py`
- `packages/platform-contract/src/python/canonical/context.py`
- `packages/shared/src/value_fabric/shared/database/tenant_validation.py`
- Per-service `database.py` files in Layer 1, Layer 4, Layer 5, etc.

**Approach**
1. Compare duplicates and extract the superset of behavior into `packages/shared/`.
2. Replace per-service modules with thin re-exports or direct imports from shared.
3. Consolidate the two `RequestContext` definitions; migrate `platform-contract` consumers to the shared one if contract-compatible.
4. Unify tenant validation and RLS session tagging in one module.
5. Update service `main.py`/`api/main.py` to use shared bootstrap.

**Validation**
- `make lint` passes.
- `make typecheck` passes.
- `make test` passes for all layers.
- Tenant-isolation security tests pass.

**Rollback**
Restore per-service modules from git history; switch imports back if a service needs a divergent implementation.

**Risks**
- Subtle differences in bootstrap/logging behavior can break service startup.
- Consolidating tenant context incorrectly could weaken isolation; security tests are mandatory.
