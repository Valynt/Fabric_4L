# Test Inventory

Generated: 2026-05-23 (Autonomous Test Assurance Agent - Phase 1)

## Backend Tests

| Layer | Test Files | Est. Tests | Key Markers |
|-------|-----------|------------|-------------|
| Layer 1 (Ingestion) | 805 files | ~102 | `unit`, `integration`, `performance` |
| Layer 2 (Extraction) | 324 files | ~95 | `unit`, `integration` |
| Layer 3 (Knowledge) | 1,956 files | ~68 | `unit`, `integration`, `tenant_boundary` |
| Layer 4 (Agents) | 1,622 files | ~163 | `unit`, `integration`, `security` |
| Layer 5 (Ground Truth) | 25 files | ~58 | `unit`, `integration` |
| Layer 6 (Benchmarks) | 79 files | ~29 | `unit`, `integration` |
| Root tests/ | 328 files | ~670 | `mandatory`, `security`, `contract_static`, `tenant_boundary`, `auth_boundaries`, `cross_tenant_write` |
| Packages | 22 files | ~45 | `unit`, `contract` |

## Frontend Tests

| Category | Files | Framework |
|----------|-------|-----------|
| Unit/Component | 149 | Vitest |
| E2E (Playwright) | 82 | Playwright |
| Accessibility | ~8 | Playwright + axe-core |

## CI Gates

| Gate | Status | Command |
|------|--------|---------|
| `verify` | Active | `make verify` |
| `security-smoke` | Active | `make security-smoke` |
| `contract-tests` | Active | `make contract-tests` |
| `gate-security` | Active | `make gate-security` |
| `gate-arch` | Active | `make gate-arch` |
| `gate-state` | Active | `make gate-state` |
| `gate-config` | Active | `make gate-config` |

## Key Test Markers

| Marker | Count | Description |
|--------|-------|-------------|
| `security` | ~91 files | OWASP / tenant-boundary / auth tests |
| `tenant_boundary` | ~20+ files | Cross-tenant isolation regression |
| `contract_static` | ~43 files | Deterministic contract tests |
| `mandatory` | Core subset | Must pass in CI |
| `backend_integrated` | ~8 files | Live stack validation |

## Auth & Boundary Enforcement Points

| Layer | Auth Mechanism | Middleware | Key Files |
|-------|----------------|------------|-----------|
| L3 | API Key (Bearer/X-API-Key) | `AuthenticationMiddleware` | `services/layer3-knowledge/src/auth/middleware.py` |
| L4 | JWT + API Key | `GovernanceMiddleware` | `services/layer4-agents/src/tenants/...` |
| API Gateway | JWT (OIDC) | Auth router | `services/api/app/routers/auth.py` |
| Shared | Rate limiting | `RedisRateLimiter` | `value_fabric/shared/identity/rate_limiter.py` |

## RLS & Database Boundaries

| Layer | RLS Policies | Key Migration | DB Session |
|-------|-------------|---------------|------------|
| L1 | Yes | `004_add_rls_policies.py` | `get_db()` |
| L4 | Yes | `007_add_rls_policies.py`, `013_add_missing_rls_policies.py` | `database.py` |
| L5 | Yes | `002_add_rls_policies.py`, `005_add_rls_to_model_registry.py` | `database.py` |

## Discovery Notes

- All 12 P0 gaps and 11 P1 gaps marked resolved (2026-05-19 TEST_AUDIT)
- Previous autonomous execution (2026-05-22) focused on L3 graph_viz security boundaries
- Strong tenant isolation patterns across L3-L6
- Extensive hostile test patterns for cross-tenant access prevention
- Fail-closed behavior well-tested across all layers
- Security tests conftest patches rate limiters to prevent test contamination
