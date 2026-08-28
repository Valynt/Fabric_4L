# Layer 7 Billing Service

Layer 7 Billing is the canonical deployable billing runtime for Value Fabric.
It owns tenant-scoped usage metering, entitlement decisions, invoice/payment
state, Stripe webhook verification, and the billing API surface that Layer 4
billing routes now proxy during migration.

## Ownership Boundary

| Path | Role | Deployable |
|------|------|------------|
| `services/layer7-billing/` | Canonical billing runtime and production API owner | Yes |

The legacy `services/billing/` compatibility package was removed on
2026-08-27 (COMPAT-BILL-001); it had zero production consumers. The Stripe
customer/subscription/webhook domain is owned by
`services/layer4-agents/src/layer4_agents/services/billing_service.py`, while
plans, usage metering, invoices, and payment state belong here. Do not
reintroduce a `services/billing/` package. New billing runtime behavior belongs
in this service and must preserve tenant isolation and contract compatibility.

## API Surface

Layer 7 exposes billing endpoints under `/v1/billing`, including:

- `POST /v1/billing/plans`
- `GET /v1/billing/entitlements/{plan_id}/decision`
- `POST /v1/billing/usage-events`
- `GET /v1/billing/usage-aggregates`
- `GET /v1/billing/invoices`
- `GET /v1/billing/payment-state`
- `POST /v1/billing/webhook`
- Migrated subscription, checkout, portal, overage, and usage-sync routes
  mounted from the extracted Layer 4 billing routers.

## Validation

```bash
python -m pytest services/layer7-billing/tests -v --tb=short
python -m pytest tests/contract/test_billing_contracts.py -v --tb=short
```
