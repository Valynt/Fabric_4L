# Layer 7: Billing

> **Service:** `services/layer7-billing/`
> **Port:** 8008
> **Package:** `layer7_billing`

---

## Purpose

Layer 7 is the **internal usage-event tracking and entitlement service**. It handles:

1. **Usage Event Ingestion** — Accept and persist usage events from all platform services
2. **Plan Entitlement Checks** — Query whether a tenant has remaining quota for a given feature
3. **Invoice Listing** — Provide invoice summaries for tenant billing portals
4. **Payment State Tracking** — Track subscription status, trial state, and grace periods

Layer 7 does **not** integrate directly with Stripe. Stripe-integrated subscription management lives in `services/billing/` per ADR-023. The two services are complementary:

| Service | Concern | Stripe Integration |
|---------|---------|-------------------|
| `services/layer7-billing/` (this doc) | Usage metering, entitlements, invoice listing | No (internal accounting) |
| `services/billing/` | Subscriptions, customers, webhooks | Yes (Stripe API) |

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
                    │  Layer 7: Billing (port 8008)  │
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
              PostgreSQL       Redis          (services/billing/)
              (events,         (caching,        Stripe integration
               invoices,       rate limits)      for subscriptions)
               entitlements)
```

---

## API Surface

### REST Endpoints (port 8008)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/events` | Ingest a usage event |
| GET | `/api/v1/events` | List usage events for tenant |
| GET | `/api/v1/entitlements` | Check plan entitlements |
| GET | `/api/v1/entitlements/{feature_key}` | Check specific feature quota |
| POST | `/api/v1/entitlements/{feature_key}/consume` | Consume one unit of quota |
| GET | `/api/v1/invoices` | List invoices for tenant |
| GET | `/api/v1/invoices/{invoice_id}` | Get invoice details |
| GET | `/api/v1/subscription` | Get current subscription state |
| GET | `/health` | Service health check |

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
# Run all Layer 7 tests
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
| `BILLING_SERVICE_URL` | `http://billing:8000` | Stripe billing service URL (ADR-023) |

---

## Entitlement Check Flow

```
1. L4 Agent calls POST /api/v1/workflows
2. API Gateway intercepts, injects X-Tenant-ID
3. Before executing, L4 calls L7:
   GET /api/v1/entitlements/agent_runs
4. L7 checks Redis cache (TTL 60s), falls back to DB:
   - If quota remaining → HTTP 200, proceed
   - If quota exhausted → HTTP 429, block with Retry-After
5. After workflow completes, L4 emits usage event:
   POST /api/v1/events {event_type: "agent_run", quantity: 1}
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

- [ADR-023: Billing Service Extraction](../explanations/adr/ADR-023-billing-service-extraction.md) — Stripe billing separation
- [ADR-010: PostgreSQL RLS for Multi-Tenancy](../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy.md) — Tenant isolation
- `services/billing/` — Stripe-integrated subscription management

---

*Last updated: 2026-06-04*
