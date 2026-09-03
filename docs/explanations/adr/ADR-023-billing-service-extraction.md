# ADR-023: Billing Service Extraction

**Status:** Superseded by Layer 7 billing ownership rationalization (2026-06-05); `services/billing/` removed 2026-08-27 (COMPAT-BILL-001)
**Date:** May 29, 2026
**Authors:** Architecture Lead, Backend Lead
**Reviewers:** Platform Architecture Committee

---

## Context

The Stripe billing logic in `services/layer4-agents/` (`services/billing_service.py`, 1063 lines; `api/routes/billing.py`) is co-located with the LangGraph agentic workflow engine. These two concerns have fundamentally different:

- **Change velocity:** Billing changes quarterly (compliance, Stripe API versions); workflow engine changes daily.
- **Scaling profile:** Billing is CPU-light HTTP + DB; LangGraph is CPU/memory-heavy with state checkpoints.
- **External API boundary:** Stripe is a well-defined external boundary; moving it to a dedicated service reduces blast radius.
- **Team ownership:** Billing is owned by the Platform team; workflow engine by the Agents team.

A separate `services/layer7-billing/` service handles internal usage-event tracking (usage metering, plan entitlements), but Stripe-integrated subscription management, customer sync, webhooks, and invoice charging remains inside L4.

This ADR records the historical decision to extract the Stripe billing subsystem from L4 into a standalone `services/billing/` service, consistent with the decomposition plan in ADR-022. That ownership model was superseded on 2026-06-05: canonical deployable billing behavior is now consolidated in `services/layer7-billing/`, and the `services/billing/` compatibility package was deleted on 2026-08-27 (COMPAT-BILL-001) after confirming zero production consumers. Billing ownership today: plans/usage/invoices/payment-state in `services/layer7-billing/`; Stripe customer/subscription/webhook domain in `services/layer4-agents/src/layer4_agents/services/billing_service.py`.

## Decision

The original decision was to create **`services/billing/`** as a standalone FastAPI service that:

1. Owns all Stripe-integrated billing logic: subscription management, customer sync, webhook idempotency, and invoice tracking.
2. Exposes a versioned HTTP API consumed by L4 (and eventually by other services).
3. Has its own `Dockerfile`, Alembic migration chain, and `pytest` coverage gate (≥80%).
4. Shares Pydantic-only schemas through `packages/shared/billing_schemas/` — no SQLAlchemy models cross service boundaries.

This is no longer the production ownership model. L4 billing routes now forward to `services/layer7-billing/`, and `services/billing/` must not regain Docker, Compose, Kubernetes, or production routing ownership.

### Historical shared schemas proposal

The original proposal placed Pydantic-only billing schemas in
`packages/shared/billing_schemas/`. Current Layer 7 ownership keeps the
canonical deployable API in `services/layer7-billing/` and its OpenAPI contract
in `contracts/openapi/layer7-billing.json`; any shared schemas must be added
only when there is an active cross-service caller that cannot consume the
OpenAPI-generated contract.

### Current ownership layout

```
services/layer7-billing/
├── Dockerfile
├── README.md
├── pyproject.toml
├── pytest.ini
├── src/
│   └── layer7_billing/
│       ├── api/
│       │   ├── main.py
│       │   └── routes/         # Extracted billing, overage, usage, webhook routes
│       ├── database.py         # Async SQLAlchemy session factory with tenant context
│       ├── models.py           # Tenant-scoped billing models
│       ├── repository.py       # Tenant-filtered data access layer
│       └── webhook_security.py # Stripe signature verification helpers
└── tests/

services/billing/               # non-deployable legacy compatibility package
├── README.md
├── pyproject.toml              # [tool.value_fabric].deployable = false
├── src/billing/
└── tests/
```

## Rationale

### Why Now?

The Sprint 7 plan identifies L4 billing extraction as a P0 blocker for GA. The key risks of deferral are:

- A Stripe API upgrade or webhook security issue would require redeploying the entire workflow engine.
- Billing scaling cannot be independently tuned until it is a separate deployment unit.
- ADR-022 (L4 Internal Decomposition) commits to Billing as the pilot extraction; this ADR provides the concrete implementation record.

### Supersession: why Layer 7 now owns billing runtime

The split between an internal metering service and a separate Stripe service created ambiguous runtime ownership. Current architecture consolidates deployable billing behavior in `services/layer7-billing/` so there is one billing API owner, one Docker/Compose deployable, and one tenant-isolated persistence boundary for usage, entitlement, invoice, payment-state, webhook, and subscription-control-plane behavior.

| Path | Concern | Deployable | Stripe |
|------|---------|------------|--------|
| `services/layer7-billing/` | Canonical billing runtime: usage metering, entitlements, invoice/payment state, webhook verification, subscription-control-plane API | Yes | Yes, through Layer 7 webhook and adapter surfaces |
| `services/billing/` | Historical Stripe migration and webhook-idempotency compatibility tests | No | Historical compatibility code only |

### Why avoid cross-service ORM sharing?

Cross-service communication must not import SQLAlchemy models. Current callers should consume Layer 7 through HTTP/OpenAPI contracts or narrowly scoped Pydantic DTOs; database internals stay inside `services/layer7-billing/`.

## Trade-offs

### Positive
- Independent deployment and scaling for billing through Layer 7
- Stripe-related outages do not affect workflow execution
- Smaller, focused Layer 7 and compatibility test suites
- Stripe API version upgrades scoped to the canonical billing service

### Negative
- Additional network hop for billing calls from L4
- Shared PostgreSQL instance initially (split deferred to future ADR)
- Proxy routes in L4 during migration add temporary complexity

## Mitigations

| Risk | Mitigation |
|---|---|
| Network latency L4→Layer 7 | Internal service call; remove proxy once callers migrate directly to Layer 7 |
| Shared DB migration conflicts | Keep Layer 7 tenant-scoped persistence as the canonical billing data boundary |
| Contract drift | `contracts/openapi/layer7-billing.json` maintained; Layer 4 proxy contracts remain temporary compatibility surfaces |
| Tenant isolation regression | Cross-tenant hostile tests required in `services/layer7-billing/tests/`; `services/billing/tests/` remains compatibility-only |

## Compatibility Notes

- **COMPAT-L4-003:** L4 billing routes act as proxies to Layer 7 during migration (removal target: 2026-10-31).
- Legacy path `from layer4_agents.services.billing_service import BillingService` remains importable during migration but is deprecated.
- `services/billing/` is non-deployable compatibility code. It intentionally has no Dockerfile and no Compose/Kubernetes ownership.

## Acceptance Criteria

- [x] Historical: `docker build -f services/billing/Dockerfile .` succeeded before this ADR was superseded. The Dockerfile is now retired because `services/billing/` is non-deployable.
- [x] `pytest services/billing/` passes with compatibility coverage
- [x] `grep -r "from app.billing" services/` returns 0 (no direct service-internal imports)
- [x] Layer 7 OpenAPI contract exists at `contracts/openapi/layer7-billing.json`
- [x] ADR-023 (this document) merged to `main`; superseded ownership note added 2026-06-05

## Related Decisions

- ADR-010: PostgreSQL RLS for Multi-Tenancy
- ADR-017: JWT/API-Key Hybrid Authentication
- ADR-022: Layer 4 Internal Decomposition
- `docs/governance/compatibility-debt-registry.md`
- `EXECUTION_PLAN_V2.md` — P0-4

---

**Last Updated:** June 5, 2026
