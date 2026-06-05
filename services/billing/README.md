# Legacy Billing Service

Stripe-integrated subscription billing compatibility code for Value Fabric.

> Status: legacy, non-deployable. Canonical deployable billing behavior now
> lives in `services/layer7-billing/`. This package remains in the tree only
> for compatibility tests and historical Stripe migration coverage until the
> registered compatibility debt is retired.

## Overview

This package covers historical Stripe-integrated billing logic:
- Subscription management (create, cancel, update)
- Customer sync with Stripe
- Webhook idempotency processing
- Invoice and usage tracking

See [ADR-023](../../docs/explanations/adr/ADR-023-billing-service-extraction.md) for the original extraction decision and
`docs/governance/compatibility-debt-registry.md` for the current retirement
tracking.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/customers` | Create or sync a billing customer |
| POST | `/v1/subscriptions` | Create a subscription |
| GET | `/v1/subscriptions/active` | Get active subscription for a user |
| DELETE | `/v1/subscriptions/{id}` | Cancel a subscription |
| POST | `/v1/webhooks/stripe` | Receive Stripe webhook events |
| GET | `/health` | Liveness probe |

## Running Tests

```bash
pip install -e ".[dev]" aiosqlite
pytest
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BILLING_DATABASE_URL` | Yes | PostgreSQL async connection string |
| `STRIPE_SECRET_KEY` | Production | Stripe secret API key |
| `STRIPE_WEBHOOK_SECRET` | Production | Stripe webhook signing secret |
