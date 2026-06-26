# API Monetization Design

**Date:** 2026-06-26  
**Scope:** Turn the `services/api/` gateway into the paid, versioned, metered system of record described in the product concept.  
**Status:** Design draft — pending review before implementation planning.

---

## 1. Context & Goal

The product concept treats the public API as the contract customers pay for. The API must therefore handle:

- Tenant authentication and API-key access
- Usage metering, quotas, and rate limits
- Billing-event generation
- Audit logging
- Customer-specific benchmark access
- Versioned endpoints
- Contract/SLA enforcement
- Private customer data boundaries

Usage-based pricing (API calls, tokens, compute hours, outcomes) is the primary monetization model.

**Goal of this design:** define a concrete, phased architecture that maps the existing codebase onto that concept without rewriting the platform. The gateway remains the customer-facing entry point; Layer 4, Layer 6, and Layer 7 services remain the implementation back-ends.

---

## 2. Current State

### 2.1 Gateway (`services/api/`)

- FastAPI app created with `create_fabric_app`.
- Auth: JWT bearer or `vf_session` cookie. **API keys are explicitly rejected** (`reject_api_key_unsupported`).
- Tenant enforcement: `GovernanceMiddleware` + `TenantRequired`; `X-Tenant-ID` must match the JWT `tenant_id` claim.
- Middleware: idempotency, tenant rate limit, audit, Prometheus metrics.
- Routes under `/v1`: accounts, auth, clerk auth/webhooks, intelligence, hypotheses, drivers, evidence, calculator, realization, value cases, context-engine, governance, reviews, versioning, privacy, agents.
- **No usage metering or billing-event emission** from the gateway itself.
- Benchmarks are exposed only as an empty stub at `/v1/context-engine/benchmarks`.

Key files:

- `services/api/app/main.py`
- `services/api/app/core/security.py`
- `services/api/app/core/tenant_context.py`
- `services/api/app/core/tenant_enforcement.py`
- `services/api/app/core/audit.py`
- `services/api/app/core/metrics.py`

### 2.2 Shared infrastructure (`packages/shared/`)

- Identity: `RequestContext`, `GovernanceMiddleware`, resolution order (Bearer JWT → session cookie → `X-API-Key` if configured → service auth).
- Dependencies: `require_authenticated`, `require_tenant`, `require_role`, `require_permission`.
- Rate limiting: `TenantRateLimiter`, `TenantRateLimitMiddleware`, tier-based defaults.

Key files:

- `packages/shared/src/value_fabric/shared/identity/middleware.py`
- `packages/shared/src/value_fabric/shared/identity/context.py`
- `packages/shared/src/value_fabric/shared/identity/dependencies.py`
- `packages/shared/src/value_fabric/shared/rate_limiting/tenant_rate_limiter.py`
- `packages/shared/src/value_fabric/shared/rate_limiting/middleware.py`

### 2.3 Billing & metering

**Layer 4 (production-ready Stripe implementation)**

- Models: `BillingCustomer`, `BillingSubscription`, `BillingPlanVersion`, `BillingUsageEvent`, `BillingInvoice`, etc.
- Services: customer/subscription/checkout/portal/webhooks, usage ingestion, overage checks, invoice lifecycle.
- Routes under `/v1/billing/*`.
- API-key model/routes with per-key rate limits and tier-based key quotas.

Key files:

- `services/layer4-agents/src/layer4_agents/models/billing.py`
- `services/layer4-agents/src/layer4_agents/services/billing_service.py`
- `services/layer4-agents/src/layer4_agents/services/usage_service.py`
- `services/layer4-agents/src/layer4_agents/services/overage_service.py`
- `services/layer4-agents/src/layer4_agents/tenants/models/api_key.py`
- `services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py`

**Layer 7 (canonical scaffold)**

- FastAPI service with RBAC, Postgres RLS, usage-event ingestion, Stripe webhook security.
- Checkout/portal/subscription lifecycle endpoints are currently stubs.

Key files:

- `services/layer7-billing/src/layer7_billing/api/main.py`
- `services/layer7-billing/src/layer7_billing/api/routes/billing.py`
- `services/layer7-billing/src/layer7_billing/models.py`
- `services/layer7-billing/src/layer7_billing/repository.py`

### 2.4 Benchmarks (`services/layer6-benchmarks/`)

- Full implementation: `GET /v1/benchmarks/datasets`, `POST /v1/benchmarks/datasets`, `GET /v1/benchmarks/datasets/{id}`, `PUT ...`, `POST /v1/benchmarks/compare`, `POST /v1/benchmarks/validate`, `GET /v1/benchmarks/industries`.
- Tenant isolation: datasets are either `tenant` or `global_system`; queries filter `tenant_id = $tenant_id OR ownership_mode = 'global_system'`.
- No plan/tier-based entitlement gating yet.

Key files:

- `services/layer6-benchmarks/src/layer6_benchmarks/api/routes/benchmarks.py`
- `services/layer6-benchmarks/src/layer6_benchmarks/models/benchmark_dataset.py`
- `services/layer6-benchmarks/src/layer6_benchmarks/repositories/benchmark_repository.py`

### 2.5 OpenAPI contracts

- `contracts/openapi/fabric-4l-api.json` — gateway contract.
- `contracts/openapi/layer6-benchmarks.json` — benchmark contract.
- `contracts/openapi/layer7-billing.json` — billing contract.
- `contracts/openapi/layer4-agents.json` — Layer 4 contract (includes billing and API keys).

### 2.6 Missing pieces

| Capability | Status |
|---|---|
| Gateway API-key auth | Missing — API keys only exist in Layer 4 |
| Gateway usage metering | Missing — gateway emits no billing events |
| Quota enforcement at the gateway | Partial — rate limits only |
| `/v1/benchmarks` on gateway | Stub only |
| `/v1/value-drivers/map` | Not implemented |
| `/v1/value-models/generate`, `/validate`, `/qa` | Not implemented |
| `/v1/assumptions/score` | Not implemented |
| `/v1/evidence/extract-value-signals` | Not implemented as named route |
| `/v1/cfo-narratives/generate` | Not implemented as named route |
| `/v1/realization/compare` | Not implemented as named route |
| SLA/contract enforcement middleware | Missing except DSAR deadline tracking |
| Customer-specific benchmark entitlement gating by plan | Missing — only tenant/global isolation exists |

---

## 3. Target Public API Surface

The gateway should expose a single, versioned, metered surface. Downstream services (L4, L6, L7) remain the implementation layer.

```text
/v1/auth/*
  POST /v1/auth/api-keys            # create/revoke/list (gateway-owned, backed by L4 or gateway DB)
  POST /v1/auth/api-keys/{id}/revoke

/v1/usage
  GET  /v1/usage                    # current-period usage for tenant
  GET  /v1/usage/quotas             # remaining quota by product

/v1/benchmarks                      # proxy to L6 (or gateway cache)
  GET  /v1/benchmarks
  POST /v1/benchmarks/compare
  POST /v1/benchmarks/validate

/v1/value-drivers
  POST /v1/value-drivers/map        # new — orchestrated via L4

/v1/value-models
  POST /v1/value-models/generate
  POST /v1/value-models/validate
  POST /v1/value-models/qa

/v1/assumptions
  POST /v1/assumptions/score

/v1/evidence
  POST /v1/evidence/extract-value-signals

/v1/cfo-narratives
  POST /v1/cfo-narratives/generate

/v1/realization
  POST /v1/realization/compare
```

All routes are tenant-scoped, metered, audited, and subject to rate limits and quotas.

---

## 4. Architecture

### 4.1 High-level flow

```text
Customer request
      │
      ▼
┌─────────────────┐
│  Gateway /v1    │  ← API-key or JWT auth, tenant resolution, rate limit, quota check
│                 │  ← emit usage event, audit log
└────────┬────────┘
         │
         ├──────────────► Layer 6 benchmarks
         ├──────────────► Layer 4 agents / billing / orchestration
         ├──────────────► Layer 7 billing (future canonical owner)
         └──────────────► Other layer services
```

### 4.2 Components

| Component | Responsibility | Primary location |
|---|---|---|
| Gateway public routers | Customer-facing routes, request validation, response shaping | `services/api/app/routers/` |
| API-key resolver | Authenticate `Authorization: Bearer vk_...` or `X-API-Key` and resolve tenant/permissions | `services/api/app/core/api_key_auth.py` |
| Usage meter | Record per-request consumption (unit, quantity, outcome) | `services/api/app/core/usage_meter.py` |
| Quota enforcer | Reject requests that would exceed plan quota | `services/api/app/core/quota_enforcer.py` |
| Billing event publisher | Emit normalized billing events to L4/L7 usage ingestion | `services/api/app/core/billing_events.py` |
| SLA/contract middleware | Attach SLA metadata, track latency, enforce contract-tier limits | `services/api/app/core/sla_middleware.py` |
| Downstream clients | Typed HTTP/gRPC clients to L4/L6/L7 | `services/api/app/clients/` |
| OpenAPI contract | Source-of-truth API spec | `contracts/openapi/fabric-4l-api.json` |

---

## 5. Design Details

### 5.1 API-key authentication at the gateway

- Add a gateway-level API key model/table (tenant-scoped, HMAC-SHA256 hashed, prefix `vf_` or `vk_`).
- Alternatively, reuse Layer 4's API key store via an internal client and cache resolution in Redis.
- The shared `GovernanceMiddleware` already supports an injected `api_key_resolver`; replace `reject_api_key_unsupported` with a resolver that calls the gateway or L4 store.
- On resolution, set `RequestContext.auth_source = "api_key"`, `tenant_id`, and derived roles/permissions.
- API keys should carry scopes (e.g., `benchmarks:read`, `value-models:write`) enforced by `require_permission`.

### 5.2 Tenant auth

- Keep JWT/session as the human-user path.
- API keys become the machine-to-machine path.
- Continue to enforce `X-Tenant-ID` matches the resolved tenant context.
- Do not trust request-body `tenant_id`.

### 5.3 Usage metering

- Every metered request passes through a `UsageMeter` dependency/middleware.
- Record:
  - `tenant_id`, `api_key_id` (if applicable), `endpoint`, `method`, `product_code`
  - `units`: number of calls, tokens, compute-seconds, records processed, or outcome count
  - `request_id`, `timestamp`, `plan_id`
- Persist to a gateway-local queue/table and flush asynchronously to Layer 4 `usage_service` or Layer 7 usage ingestion.
- For compute-heavy endpoints (value-model generation), accept a `usage_estimate` from the downstream service and record actuals on response.

### 5.4 Quotas

- Store per-plan quotas in Layer 4 `BillingPlanVersion` or Layer 7 `BillingPlan`.
- Gateway fetches plan/entitlements at request time (cached in Redis, TTL 60s).
- Quota check happens **after** auth, **before** business logic:
  - If quota exceeded → `429` with `QuotaExceeded` error code and `Retry-After`.
- Distinguish hard quota from soft quota with overage billing.

### 5.5 Rate limits

- Continue using `TenantRateLimitMiddleware` for request-per-window limits.
- Add per-API-key rate limits (Layer 4 already supports this; extend to gateway-level keys).
- Exempt health/readiness/docs/metrics.

### 5.6 Billing events

- Use the same event schema as Layer 4 `BillingUsageEvent` / Layer 7 `UsageEvent`.
- Emit events asynchronously via a Redis stream or background task; avoid blocking the response path.
- For Stripe usage-based pricing, have Layer 4/7 push meter events to Stripe.

### 5.7 Audit logs

- Existing `AuditMiddleware` already logs mutating requests and sensitive reads.
- Extend it to log:
  - API-key usage
  - Quota/rate-limit enforcement actions
  - SLA violations
  - Cross-tenant denial events
- Redact secrets, tokens, and customer data.

### 5.8 Customer-specific benchmark access

- Keep Layer 6 as the source of truth for datasets.
- Add entitlement check before proxying to Layer 6:
  - Plan includes `benchmarks:advanced` or customer-specific dataset IDs.
  - Deny access to private datasets not owned by or shared with the tenant.
- Store dataset sharing/entitlements in gateway DB or Layer 4 billing entitlements.

### 5.9 Versioned endpoints

- Keep the existing `/v1/` prefix.
- Introduce an optional `API-Version` header (default `v1`) so future `/v2/` can coexist.
- Each public route version maps to a downstream client version.
- Update the existing `contracts/openapi/fabric-4l-api.json` for v1; add `contracts/openapi/fabric-4l-api-v2.json` only when a v2 surface is created.

### 5.10 Contract/SLA enforcement

- Add `SLAMiddleware` that:
  - Reads contract tier from tenant plan.
  - Tracks p50/p95/p99 latency per endpoint.
  - Enforces max latency SLAs by returning `503` or degraded response when SLA cannot be met.
  - Emits audit events on SLA breach.
- Add per-tier feature flags (e.g., `feature.value_models_qa`).

### 5.11 Private customer data boundaries

- All gateway queries scoped by `tenant_id`.
- API keys are tenant-scoped; no cross-tenant key resolution.
- Response payloads must not include other tenants' data; rely on downstream RLS/tenant filters.
- Cache keys include tenant id.
- Ensure API-key auth is treated as a production auth mechanism and does not trigger `ProductionSafetyValidator` dev-auth-bypass guards.

---

## 6. Data Flow Examples

### 6.1 `GET /v1/benchmarks` with API key

1. Client sends `Authorization: Bearer vk_abc123`, `X-Tenant-ID: tenant_42`.
2. Gateway resolves API key → tenant_42, scopes `benchmarks:read`.
3. Rate-limit check for key/tenant.
4. Quota check for `benchmarks` product.
5. Gateway calls Layer 6 `GET /v1/benchmarks/datasets` with service auth + tenant context.
6. Layer 6 returns tenant-visible datasets.
7. Gateway records usage event (`product=benchmarks`, `units=1`).
8. Audit middleware logs the read.
9. Response returned to client.

### 6.2 `POST /v1/value-models/generate`

1. Auth, rate limit, quota as above.
2. Gateway calls Layer 4 orchestration endpoint.
3. Layer 4 returns generated model and usage metadata (`tokens_in`, `tokens_out`, `compute_seconds`).
4. Gateway records usage event with actual units.
5. If quota would be exceeded by actuals, mark for overage billing rather than fail.

---

## 7. Implementation Phases

### Phase 1 — Foundation (gateway auth + metering)

- Add API-key model and resolver in gateway.
- Add `UsageMeter` and billing-event publisher.
- Wire `/v1/benchmarks` to Layer 6 with auth + metering.
- Update `contracts/openapi/fabric-4l-api.json`.
- Tests: API-key auth, tenant isolation, usage event emission, quota enforcement.

### Phase 2 — Product endpoints

- Add `/v1/value-drivers/map`, `/v1/value-models/*`, `/v1/assumptions/score`, `/v1/evidence/extract-value-signals`, `/v1/cfo-narratives/generate`, `/v1/realization/compare`.
- Each route proxies/orchestrates through L4/L6 with metering.
- Define product codes and units for each endpoint.

### Phase 3 — Entitlements & SLA

- Add plan-based feature entitlements and benchmark access controls.
- Add SLA middleware and contract-tier enforcement.
- Move billing canonical ownership toward Layer 7 once its Stripe lifecycle is complete.

### Phase 4 — Polish

- Versioning strategy, SDK generation, public docs, runbooks.

---

## 8. Testing Strategy

- **Unit:** API-key hash/resolution, quota math, usage event schema validation.
- **Integration:** gateway → downstream clients with mocked L4/L6/L7.
- **Contract:** OpenAPI spec drift check against route handlers.
- **Tenant isolation:** hostile cross-tenant API-key usage, body/header spoofing.
- **Security:** missing/invalid keys, expired keys, revoked keys, scope violations.
- **Load:** rate-limit and quota behavior under concurrency.

---

## 9. Open Questions

1. Should the gateway own API keys, or should it proxy to Layer 4's existing key store?
2. Should usage events be written to a gateway-local table first, or sent directly to Layer 4/7?
3. Which plan/entitlement source is authoritative — Layer 4 `BillingPlanVersion` or Layer 7 `BillingPlan`?
4. Should the missing product endpoints be implemented as thin proxies in the gateway, or as new orchestration workflows in Layer 4?

---

## 10. Recommendation

Start with **Phase 1**: add API-key authentication and usage metering to the gateway, and expose `/v1/benchmarks` as the first metered public endpoint. This creates the paid-system-of-record foundation before filling in the remaining product surface.
