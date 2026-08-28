# Adjacent Service: Billing

> **Service:** `services/layer7-billing/`
> **Port:** 8008
> **Package:** `layer7_billing`

---

## Purpose

Billing is the **canonical deployable billing service** and a bounded capability adjacent to the six-layer core pipeline. It owns billing runtime behavior for the platform and handles:

1. **Usage Event Ingestion** — Accept and persist usage events from all platform services.
2. **Plan Entitlement Checks** — Query whether a tenant has remaining quota for a given feature.
3. **Invoice Listing** — Provide invoice summaries for tenant billing portals.
4. **Payment State Tracking** — Track subscription status, trial state, and grace periods.
5. **Stripe-facing Control Plane** — Verify Stripe webhooks and host subscription, checkout, portal, plan, overage, and usage-sync API surfaces as the Layer 4 billing routes migrate to thin proxies.

Billing remains outside the core L1-L6 pipeline layer count. Core services must interact with it through entitlement, usage-event, and webhook contracts; request handlers must not perform synchronous external provider calls except verified webhook or explicitly idempotent callback paths.

`services/layer7-billing/` is the only deployable billing service. The historical `services/billing/` package (non-deployable compatibility code) was removed on 2026-08-27 (COMPAT-BILL-001); it must not be reintroduced or given Docker/Compose/Kubernetes runtime wiring.

| Path | Ownership | Deployable | Stripe Surface |
|------|-----------|------------|----------------|
| `services/layer7-billing/` (this doc) | Canonical billing runtime, APIs, tenant-scoped persistence, webhook verification, entitlement decisions, usage metering | Yes | Yes — webhook verification and future checkout/portal/subscription adapters live here |

The legacy `services/billing/` package was removed 2026-08-27 (COMPAT-BILL-001). The Stripe customer/subscription/webhook domain is owned by `services/layer4-agents/src/layer4_agents/services/billing_service.py`; plans, usage, invoices, and payment state belong here.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Platform Services                        │
│  L1 Ingestion  L2 Extraction  L3 Graph  L4 Agents  L5 GT   │
│       │              │            │          │         │    │
└───────┼──────────────┼────────────┼──────────┼─────────┼────┘
        │              │            │          │         │
        └──────────────┴────────────┴──────────┴─────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Billing (port 8008)            │
                    │  ┌─────────────────────────┐  │
                    │  │  Usage Event Ingestion   │  │
                    │  │  Plan Entitlement Check  │  │
                    │  │  Invoice Listing         │  │
                    │  │  Payment State Tracking  │  │
                    │  └─────────────────────────┘  │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              PostgreSQL       Redis           Stripe API
              (events,         (caching,       (via Billing
               invoices,       rate limits)     adapters/webhooks)
               entitlements)
```

---

## API Surface

### REST Endpoints (port 8008)

Canonical endpoints are exposed under `/v1/billing`. Layer 4 billing routes remain temporary forwarding shims while callers migrate directly to Billing.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/billing/plans` | Upsert a tenant-scoped billing plan and entitlement list |
| GET | `/v1/billing/entitlements/{plan_id}/decision` | Check whether a feature is allowed for a plan |
| POST | `/v1/billing/usage-events` | Ingest a single idempotent usage event |
| GET | `/v1/billing/usage-aggregates` | List tenant usage aggregates |
| GET | `/v1/billing/invoices` | List tenant invoices |
| GET | `/v1/billing/payment-state` | Get current tenant payment state |
| POST | `/v1/billing/webhook` | Receive and verify Stripe billing webhooks |
| GET | `/v1/billing/subscription` | Get current subscription status for a customer |
| POST | `/v1/billing/checkout` | Create a checkout session once the Stripe adapter is configured |
| POST | `/v1/billing/portal` | Create a customer portal session once the Stripe adapter is configured |
| GET | `/health` | Service health check |
| GET | `/ready` | Readiness checks, including database probe |

### Authentication

All endpoints require:
- `Authorization: Bearer <token>` header (JWT or API key)
- `X-Tenant-ID: <tenant>` header (RLS-enforced multi-tenancy)

---

## Service Structure

```
services/layer7-billing/
  src/layer7_billing/
    api/
      main.py              # FastAPI app entrypoint
    models.py              # SQLAlchemy ORM models
    repository.py          # Data access layer
    database.py            # Async SQLAlchemy session factory with RLS
    logging_config.py      # Structured logging
    webhook_security.py    # Webhook signature verification helpers
  tests/                   # Unit & integration tests
  Dockerfile
  pyproject.toml
  pytest.ini
```

---

## Data Model

### Core Entities

| Entity | Table | Description |
|--------|-------|-------------|
| `UsageEvent` | `usage_events` | Individual usage events (tenant-scoped, timestamped) |
| `PlanEntitlement` | `plan_entitlements` | Feature quotas per plan tier |
| `TenantQuota` | `tenant_quotas` | Current consumption vs. limit per tenant |
| `Invoice` | `invoices` | Invoice header records |
| `InvoiceLineItem` | `invoice_line_items` | Per-event-type line items |
| `SubscriptionState` | `subscription_states` | Current subscription status per tenant |

### Key Fields (UsageEvent)

```
id: UUID (PK)
tenant_id: str (FK, RLS filter)
event_type: str       # e.g. "ingestion_job", "llm_call", "agent_run"
quantity: int         # Units consumed (default 1)
metadata: JSONB       # Free-form event metadata
created_at: datetime  # Event timestamp
```

---

## Dependencies

| Dependency | Purpose |
|------------|---------|
| PostgreSQL (asyncpg) | Primary persistence with RLS |
| Redis | Caching entitlement checks and rate limiting |
| FastAPI + Uvicorn | HTTP API |
| Alembic | Database migrations |
| structlog | Structured logging |
| prometheus-client | Metrics exposure |
| sentry-sdk | Error tracking |

---

## Operational Notes

### Startup

```bash
# Run migrations
uv run --package layer7-billing alembic upgrade head

# Start service
uv run --package layer7-billing uvicorn layer7_billing.api.main:app --port 8008
```

### Health Check

```bash
curl http://localhost:8008/health
```

### Testing

```bash
# Run all Billing tests
pytest services/layer7-billing/tests/ -v

# With coverage (≥80% required)
pytest services/layer7-billing/tests/ --cov=src/layer7_billing --cov-report=term-missing
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | — | Redis connection string |
| `JWT_SECRET` | — | Shared JWT secret for auth |
| `API_PORT` | 8008 | Service listen port |
| `STRIPE_WEBHOOK_SECRET` | — | Stripe webhook signing secret used by `/v1/billing/webhook` |
| `STRIPE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS` | 300 | Maximum accepted Stripe webhook timestamp skew |
| `STRIPE_WEBHOOK_RATE_LIMIT_PER_MINUTE` | 100 | Per-source-IP webhook rate limit |
| `BILLING_USAGE_EVENT_RATE_LIMIT_PER_MINUTE` | 1000 | Per-tenant usage event ingestion rate limit |

---

## Entitlement Check Flow

```
1. L4 Agent calls POST /api/v1/workflows
2. API Gateway intercepts, injects X-Tenant-ID
3. Before executing, L4 calls Billing:
   GET /v1/billing/entitlements/{plan_id}/decision?feature=agent_runs
4. Billing checks tenant-scoped entitlement state:
   - If quota/policy allows the feature → HTTP 200 with `allowed: true`, proceed
   - If quota/policy blocks the feature → HTTP 200 with `allowed: false`; callers enforce the gate
5. After workflow completes, L4 emits usage event:
   POST /v1/billing/usage-events {metric: "agent_run", quantity: 1, ...}
```

---

## Multi-Tenancy

All data is tenant-isolated via PostgreSQL Row-Level Security (RLS):

```sql
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON usage_events
  USING (tenant_id = current_setting('app.current_tenant')::text);
```

The `tenant_context` middleware sets the RLS variable from the `X-Tenant-ID` header on every request.

---

## Related

- [ADR-023: Billing Service Extraction](../explanations/adr/ADR-023-billing-service-extraction.md) — superseded extraction record; current ownership is consolidated in Billing
- [ADR-010: PostgreSQL RLS for Multi-Tenancy](../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy.md) — Tenant isolation
- [Compatibility Debt Registry](../governance/compatibility-debt-registry.md) — active L4 billing proxy/shim retirement tracking

---

*Last updated: 2026-08-27*
