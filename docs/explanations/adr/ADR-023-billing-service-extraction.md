# ADR-023: Billing Service Extraction

**Status:** Accepted
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

This ADR records the decision to extract the Stripe billing subsystem from L4 into a standalone `services/billing/` service, consistent with the decomposition plan in ADR-022.

## Decision

We will create **`services/billing/`** as a standalone FastAPI service that:

1. Owns all Stripe-integrated billing logic: subscription management, customer sync, webhook idempotency, and invoice tracking.
2. Exposes a versioned HTTP API consumed by L4 (and eventually by other services).
3. Has its own `Dockerfile`, Alembic migration chain, and `pytest` coverage gate (≥80%).
4. Shares Pydantic-only schemas through `packages/shared/billing_schemas/` — no SQLAlchemy models cross service boundaries.

L4 will call `services/billing/` via an internal HTTP client. During the migration period, the existing L4 billing routes may act as thin proxies.

### Shared schemas location

```
packages/shared/billing_schemas/
├── __init__.py
├── plans.py          # PlanId, SubscriptionStatus enums
├── customers.py      # CustomerRead, CustomerCreateRequest
├── subscriptions.py  # SubscriptionRead, SubscriptionCreateRequest
└── webhooks.py       # WebhookEvent, WebhookPayload
```

### Service layout

```
services/billing/
├── Dockerfile
├── pyproject.toml
├── pytest.ini
├── migrations/
│   └── billing/       # Alembic migration chain (tagged billing/)
├── src/
│   └── billing/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── main.py         # FastAPI app, GovernanceMiddleware
│       ├── database.py         # Async SQLAlchemy session factory
│       ├── models.py           # SQLAlchemy ORM models (billing_customers, etc.)
│       ├── schemas.py          # Service-local Pydantic schemas (extends shared)
│       └── service.py          # BillingService class
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_billing_service.py
```

## Rationale

### Why Now?

The Sprint 7 plan identifies L4 billing extraction as a P0 blocker for GA. The key risks of deferral are:

- A Stripe API upgrade or webhook security issue would require redeploying the entire workflow engine.
- Billing scaling cannot be independently tuned until it is a separate deployment unit.
- ADR-022 (L4 Internal Decomposition) commits to Billing as the pilot extraction; this ADR provides the concrete implementation record.

### Why `services/billing/` and not `services/layer7-billing/`?

`services/layer7-billing/` handles internal metering (usage events, plan entitlements, invoice listing) without direct Stripe integration. `services/billing/` will own the Stripe-integrated payment lifecycle. The two services are complementary:

| Service | Concern | Stripe |
|---------|---------|--------|
| `services/layer7-billing/` | Usage metering, entitlements | No (internal accounting) |
| `services/billing/` | Subscriptions, customers, webhooks | Yes (Stripe API) |

### Why `packages/shared/billing_schemas/`?

Cross-service communication must not import SQLAlchemy models. Pydantic schemas enforce a typed, serialisable API contract that both L4 (as a caller) and `services/billing/` (as a provider) can share without binding to database internals.

## Trade-offs

### Positive
- Independent deployment and scaling for billing
- Stripe-related outages do not affect workflow execution
- Smaller, focused test suite per service (billing ≥80%, not testing all of L4)
- Stripe API version upgrades scoped to one service

### Negative
- Additional network hop for billing calls from L4
- Shared PostgreSQL instance initially (split deferred to future ADR)
- Proxy routes in L4 during migration add temporary complexity

## Mitigations

| Risk | Mitigation |
|---|---|
| Network latency L4→billing | Internal K8s ClusterIP service; gRPC upgrade path documented |
| Shared DB migration conflicts | Alembic revisions tagged `billing/`; separate `migrations/billing/` chain |
| Contract drift | `contracts/openapi/billing.yaml` maintained; CI drift gate via `check_workflow_targets_and_artifacts.py` |
| Tenant isolation regression | Cross-tenant hostile tests required in `services/billing/tests/` |

## Compatibility Notes

- **COMPAT-L4-004:** L4 billing routes act as proxies during migration (removal target: 2026-12-31)
- Legacy path `from layer4_agents.services.billing_service import BillingService` remains importable during migration but is deprecated.

## Acceptance Criteria

- [x] `docker build -f services/billing/Dockerfile .` succeeds
- [x] `pytest services/billing/` passes with ≥80% line coverage
- [x] `grep -r "from app.billing" services/` returns 0 (no direct service-internal imports)
- [x] Shared schemas exist at `packages/shared/billing_schemas/`
- [x] ADR-023 (this document) merged to `main`

## Related Decisions

- ADR-010: PostgreSQL RLS for Multi-Tenancy
- ADR-017: JWT/API-Key Hybrid Authentication
- ADR-022: Layer 4 Internal Decomposition
- `docs/governance/compatibility-debt-registry.md`
- `EXECUTION_PLAN_V2.md` — P0-4

---

**Last Updated:** May 29, 2026
