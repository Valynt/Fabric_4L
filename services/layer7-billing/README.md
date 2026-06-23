# Layer 7 Billing Service

Layer 7 Billing is the canonical deployable billing runtime for Value Fabric.
It owns tenant-scoped usage metering, entitlement decisions, invoice/payment
state, Stripe webhook verification, and the billing API surface that Layer 4
billing routes now proxy during migration.

## Ownership Boundary

| Path | Role | Deployable |
|------|------|------------|
| `services/layer7-billing/` | Canonical billing runtime and production API owner | Yes |
| `services/billing/` | Legacy compatibility package retained for historical Stripe migration tests | No |

Do not add Docker Compose, Kubernetes, or production routing for
`services/billing/`. New billing runtime behavior belongs in this service and
must preserve tenant isolation and contract compatibility.

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
