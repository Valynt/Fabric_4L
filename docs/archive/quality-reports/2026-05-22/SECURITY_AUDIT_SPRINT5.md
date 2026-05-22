# Security Audit — Sprint 5

**Date:** 2026-05-18
**Scope:** Auth stacks, tenant isolation, security boundaries, billing posture, provider posture
**Auditor:** Ona (automated + source review)

---

## 1. Auth Stack Comparison

### Layer 4 — Production Auth Path

| Property | Value |
|---|---|
| Middleware | `GovernanceMiddleware` (shared identity) |
| Protocol | OIDC/PKCE |
| Token format | JWT (PyJWT) |
| CSRF protection | Yes (CSRF token in OIDC state) |
| Email verification | Yes (OIDC IdP-managed) |
| Persistence | PostgreSQL (tenant + user records) |
| Canonical path | `packages/shared/src/value_fabric/shared/identity/` |
| Status | **Production path** |

Layer 4 uses `GovernanceMiddleware` for all routes. The `require_authenticated`, `require_content_admin`, and `require_tenant_admin` dependency factories are defined in `value_fabric.shared.identity.dependencies` and used consistently across all Layer 4 route modules.

### services/api — Standalone Risk

| Property | Value |
|---|---|
| Auth mechanism | JWT + bcrypt password hashing |
| Protocol | Simple JWT (no OIDC, no PKCE) |
| Token format | JWT (PyJWT) |
| CSRF protection | None |
| Email verification | None |
| Persistence | PostgreSQL |
| Canonical path | `services/api/app/core/security.py` |
| Status | **Standalone risk — not the production auth path** |

`services/api` was built before the shared identity layer standardised on OIDC/PKCE. It provides a simpler JWT+bcrypt stack with no OIDC integration, no PKCE, and no CSRF protection. It is not the production auth path for Value Fabric.

**Risk classification:** Medium. The service is not exposed as the primary auth endpoint in production. However, its JWT tokens share the same claim shape as Layer 4 tokens, creating a potential confusion risk if both services are deployed behind the same gateway without clear routing.

---

## 2. Cross-Stack Drift

| Dimension | Layer 4 (production) | services/api (standalone) |
|---|---|---|
| JWT library | PyJWT | PyJWT |
| Token claim: user | `sub` | `sub` |
| Token claim: tenant | `tenant_id` | `tenant_id` |
| OIDC | Yes | No |
| PKCE | Yes | No |
| CSRF | Yes | No |
| Role model | `Role` enum (shared identity) | None |
| Tenant enforcement | `GovernanceMiddleware` | `TenantRequired` dependency |

**Token shape compatibility:** Both stacks mint JWTs with `sub`, `tenant_id`, `iss`, `aud`, `exp`, `iat`, `nbf`. A token minted by `services/api` is structurally decodable by the shared identity layer. This is documented and tested in `tests/security/test_cross_stack_jwt_contract.py`.

**Recommendation:** `services/api` should be deprecated in favour of Layer 4 auth in a future sprint. Until then, ensure the two services are not reachable via the same JWT audience without explicit routing controls.

---

## 3. Gaps Identified and Fixed This Sprint

### 3.1 governance_workflows.py — Unauthenticated Routes (FIXED)

**Before:** All routes in `services/layer4-agents/src/api/routes/governance_workflows.py` had no auth dependency. Any unauthenticated caller could create review decisions, read audit exports, and query lineage.

**After:** All GET routes require `require_authenticated` (via `AuthDep`). All POST routes require `require_content_admin` (via `ContentAdminDep`), covering `content_admin`, `tenant_admin`, and `super_admin` roles. Tenant context is extracted from `RequestContext`, never from request body.

**Files changed:** `services/layer4-agents/src/api/routes/governance_workflows.py`

### 3.2 Gate Decision RBAC — No Role Check (FIXED)

**Before:** `POST /v1/harness/gates/{gate_id}/decide` used `AuthCtxDep` (any authenticated user). `decision_by` was set from `ctx.user_id or ctx.tenant_id` but could be influenced by body fields.

**After:** The endpoint uses `ContentAdminCtxDep` (`require_content_admin`). `decision_by` is always set from `ctx.user_id` via a `server_decision_by` variable. Body-supplied `decision_by` is not accepted.

**Files changed:** `services/layer4-agents/src/api/routes/harness.py`

---

## 4. Tenant Isolation

### 4.1 Layer 4 Harness

All harness routes (`/v1/harness/runs`, `/v1/harness/gates`, `/v1/harness/checkpoints`) pass `ctx.tenant_id` to `SqlHarnessRegistry`. The registry raises `KeyError` for resources not owned by the tenant; routes translate this to HTTP 404. Cross-tenant access returns 404, not 200 with another tenant's data.

### 4.2 Layer 5 Ground Truth

All L5 routes use `caller.tenant_id` from `GovernanceMiddleware` context. Queries filter by `tenant_id`. The `get_current_user` dependency fails closed (HTTP 401) in production when no middleware context is present.

### 4.3 Frontend

`TenantRequired` in `services/api` reads `X-Tenant-ID` as a hint but derives the authoritative tenant from the JWT payload (`auth.tenant_id`). A mismatch between header and JWT raises HTTP 403. `TenantContext` is set from the JWT-derived value only.

### 4.4 Test Coverage

New tests in `tests/security/test_harness_tenant_isolation.py` cover:
- Harness run cross-tenant → 404
- Gate cross-tenant → 404
- Checkpoint cross-tenant → 404
- Validation cross-tenant → 403/404
- L5 org mapping scoped to tenant
- Frontend X-Tenant-ID header spoof → 403

---

## 5. Security Smoke Results

All checks in `tests/security/test_sprint5_smoke.py` pass:

| Check | Result |
|---|---|
| Missing tenant context → 401/422 | ✅ Pass |
| Wrong tenant → 404 on resource lookup | ✅ Pass |
| Body tenant_id ignored | ✅ Pass |
| decision_by server-derived | ✅ Pass |
| No secrets in structured log output | ✅ Pass |

---

## 6. Billing Posture

**Status:** Fail-closed.

- `StripeNotConfiguredError` is defined in `stripe_client.py` and raised when `STRIPE_SECRET_KEY` is absent.
- Billing routes are always registered (not conditionally excluded) so callers receive HTTP 402 `{"error": "billing_not_configured"}` rather than HTTP 404.
- A `StripeNotConfiguredError` exception handler is registered in `routers.py`.
- `stripe_client.py` uses `os.environ.get` for `STRIPE_SECRET_KEY` — no `KeyError` on startup.
- Stripe code is not imported at module load time unless the key is present.

---

## 7. Provider Posture

### 7.1 Anthropic

`LAYER4_LLM_PROVIDER=anthropic` raises `ProviderNotImplementedError("anthropic")`, a typed `RuntimeError` subclass defined in `llm_adapter_interfaces.py`. This replaces the previous bare `NotImplementedError`. Callers can catch `ProviderNotImplementedError` specifically and surface a clear configuration error.

### 7.2 Apollo/NewsAPI Enrichment

`_enrich_from_domain` and `_enrich_from_news` in `enrichment_orchestrator.py` now fail closed unless `ENRICHMENT_MOCK_MODE=true` is explicitly set:

- Without `ENRICHMENT_MOCK_MODE=true`: returns `{"success": False, "error": "..._not_configured"}`.
- With `ENRICHMENT_MOCK_MODE=true`: returns placeholder data tagged with `{"mock": True, "source": "mock"}`.

Placeholder data is never returned in production mode.

---

## 8. Definition of Done

| Item | Status |
|---|---|
| Security audit report in `reports/` | ✅ This document |
| Layer 4 auth is clearly the production path | ✅ Documented above |
| Standalone API risk is classified | ✅ Section 1 |
| Cross-stack drift documented | ✅ Section 2 |
| Tenant tests pass | ✅ 46 tests pass |
| No fake billing/enrichment in production mode | ✅ Sections 6 and 7 |
| governance_workflows.py auth gap fixed | ✅ Section 3.1 |
| Gate decision RBAC gap fixed | ✅ Section 3.2 |

---

## 9. Residual Risks and Deferred Items

| Risk | Severity | Disposition |
|---|---|---|
| `services/api` has no OIDC/PKCE | Medium | Deferred — classify and document only this sprint; migration in future sprint |
| `services/api` uses python-jose (legacy) | Low | Now uses PyJWT; no action needed |
| No RBAC on `services/api` routes | Medium | Deferred — `services/api` is not the production auth path |
| Enrichment integration (Apollo/Clearbit, NewsAPI) | Low | Fail-closed; mock mode requires explicit opt-in |
| Anthropic LLM adapter | Low | Raises `ProviderNotImplementedError`; no production impact until configured |
