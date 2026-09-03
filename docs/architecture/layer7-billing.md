# Billing Capability

> **Runtime owner:** `services/layer4-agents/` (Layer 4)
> **Package:** `layer4_agents.services.billing_service`
> **Contract:** `contracts/openapi/layer7-billing.json`
> **Port:** 8004 (served by Layer 4 Agents)

---

## Purpose

Billing is a **bounded capability owned entirely by Layer 4** (the Agents service). It owns the platform's money-domain runtime behavior:

1. **Usage Event Ingestion** â€” Accept and persist idempotent usage events from all platform services.
2. **Plan Entitlement Checks** â€” Query whether a tenant has remaining quota for a given feature.
3. **Invoice Listing** â€” Provide invoice summaries, charges, and revenue reports for tenant billing portals.
4. **Payment State Tracking** â€” Track subscription status, trial state, grace periods, and balance.
5. **Stripe-facing Control Plane** â€” Verify Stripe webhook signatures and host subscription, checkout, portal, plan, overage, invoice, and usage-sync API surfaces.

Billing is not an additional horizontal core-pipeline layer; it is a domain that lives inside the Layer 4 service. Core services interact with it through the Layer 4 billing routes (`/v1/billing/*`) and the published `layer7-billing.json` OpenAPI contract. Request handlers must not perform synchronous external provider calls except verified webhook or explicitly idempotent callback paths.

## Ownership history

| Path | Ownership | Deployable | Stripe Surface |
|------|-----------|------------|----------------|
| `services/layer4-agents/` (canonical) | Canonical billing runtime, APIs, tenant-scoped persistence, webhook verification, entitlement decisions, usage metering | Yes (Layer 4) | Yes â€” `billing_service.py`, `stripe_client`, webhook verification, checkout/portal/subscription |

The historical `services/billing/` package (non-deployable compatibility code) was removed on 2026-08-27 (COMPAT-BILL-001); it must not be reintroduced or given Docker/Compose/Kubernetes runtime wiring.

The parallel `services/layer7-billing/` service (a Phase-1 stub with zero production consumers) was **removed on 2026-09-01** (see [ADR-023](../explanations/adr/ADR-023-billing-service-extraction.md)). Layer 4 was ratified as the single canonical owner. The `layer7-billing` name is retained **only** as the filename of the canonical OpenAPI contract (`contracts/openapi/layer7-billing.json`), regenerated as a subset export of Layer 4's own billing surface.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Layer 4 Agents (:8004)                  │
│                                                             │
│   api/routes/billing.py (+ usage/overages/webhooks)         │
│         │                                                   │
│         ▼                                                   │
│   services/billing_service.py ── stripe_client              │
│         │                                                   │
│     billing_* tables (RLS)                                 │
└────────────────────────────────────────────────────────────┘
         │
         ├─────────────── Stripe API (webhooks, checkout, portal)
         └─────────────── PostgreSQL (billing_* tables, RLS)
```

The full Stripe/subscription/usage implementation lives in Layer 4 and is the only such implementation in the platform. There is no `layer7-billing` runtime or database.

---

## API Surface

### REST Endpoints (port 8004, prefix `/v1/billing`)

The canonical billing API is declared in `contracts/openapi/layer7-billing.json` (26 `/v1/billing/*` routes, `info.title` = "Layer 4: Billing API", `x-backend-service: layer4-agents`). The Layer 4 billing routers re-register handlers from `layer4_agents.api.routes.billing`; there are **no** forwarding shims to any other service.

Key endpoint families:

| Method | Path family | Purpose |
|--------|-------------|---------|
| GET/POST | `/v1/billing/subscription` | Current subscription status; create/update/cancel subscriptions |
| POST | `/v1/billing/checkout` | Create a Stripe Checkout session (subscription mode) |
| POST | `/v1/billing/portal` | Create a Stripe customer portal session |
| POST | `/v1/billing/webhook` | Receive and verify Stripe billing webhooks (IP + signature) |
| POST | `/v1/billing/events` | Ingest idempotent usage events |
| GET | `/v1/billing/usage` / `overages` | Usage and overage summaries |
| GET | `/v1/billing/invoices` / `charges` / `revenue` / `balance` | Invoice, charge, revenue, and balance reporting |
| GET | `/v1/billing/entitlements` | Plan entitlement / quota decisions |

### Authentication

All endpoints require authentication (JWT or API key) and tenant context. Multi-tenancy is enforced end-to-end: the tenant is taken from authenticated context (never from an unverified request body), and every repository query is scoped by `tenant_id`.

---

## Data Model

Billing state is persisted in `billing_*` tables owned by Layer 4 (10 migrations), with Row-Level Security enforcing tenant isolation. Core entities include subscription state, plan entitlements, usage events, overages, invoices/charges, and revenue/balance records. See the `layer4_agents` migrations for the authoritative schema.

---

## Multi-Tenancy

All billing data is tenant-isolated via PostgreSQL Row-Level Security (RLS). The `tenant_context` middleware derives the tenant from authenticated context and scopes every read/write. Cross-tenant access fails closed (hostile-access tests are enforced in the security suite).

---

## Related

- [ADR-023: Billing Service Extraction](../explanations/adr/ADR-023-billing-service-extraction.md) — extract-then-consolidate record; superseded on 2026-09-01 (L4 canonical, L7 removed)
- [ADR-010: PostgreSQL RLS for Multi-Tenancy](../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy.md) — Tenant isolation
- [Layer Runtime Path Governance](../reference/layer-runtime-path-governance.md) — canonical runtime paths
- [Compatibility Debt Registry](../governance/compatibility-debt-registry.md) — COMPAT-L4-003 resolved/archived

---

*Last updated: 2026-09-01*
