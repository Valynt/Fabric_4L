# Billing Readiness Suite

## What This Suite Validates

This suite centralizes billing, subscription, webhook, entitlement, trial, and tenant-scope readiness checks without calling Stripe or any paid external service.

## Production Risks Covered

- Subscription lifecycle changes that are not tenant-scoped.
- Billing webhooks that are not idempotent or replay-safe.
- Entitlement decisions drifting from billing usage and plan contracts.
- Trial or payment states that are not represented in schemas and tests.
- Failed payments not moving subscriptions into a restricted or dunning state.
- Cancellation grace periods granting or revoking paid access at the wrong time.
- Billing state changes missing durable audit or structured log evidence.

## Existing Coverage Aggregated

- `services/layer4-agents/tests/` — canonical billing service tests (layer7-billing service removed 2026-09-01; L4 is the sole billing owner)
- `services/layer4-agents/tests/test_billing_service.py` + `tests/billing/` — membership/subscription/webhook readiness (legacy `services/billing/` package removed 2026-08-27, COMPAT-BILL-001)
- `tests/contract/test_billing_contracts.py`
- `tests/integration/billing_entitlements/`
- `services/layer4-agents/tests/test_billing_service.py`
- `services/layer4-agents/tests/test_billing_webhook_security_consistency.py`
- `tests/recovery/test_restore_billing_state.py`
- `tests/audit/test_billing_changes_logged.py`

## Lifecycle Policy Locked By This Suite

- Checkout uses provider-managed subscription Checkout Sessions; local tests do not require Stripe credentials.
- Subscription creation, updates, and cancellation are tenant-scoped and replay-safe.
- Failed payment webhooks mark the subscription `past_due`; provider dunning/retry policy remains outside local tests.
- Cancellation at period end is the grace-period path: paid entitlement remains until period end, while immediate cancellation downgrades to free.
- Replayed webhooks must not duplicate processed event rows, invoice/credit side effects, usage entries, or entitlement grants.
- Billing state changes must emit structured audit/log evidence until the dedicated audit-ledger fixture is implemented.

## Known Gaps

- CHECKOUT_PROVIDER_SANDBOX: checkout provider redirects are not exercised here because this suite cannot require Stripe credentials.
- PAYMENT_FAILURE_PROVIDER_EVENT: local tests cover `invoice.payment_failed` handling and the `past_due` result; live provider dunning payload replay remains a sandbox test.
- TRIAL_EXPIRATION_CLOCK_DRIVEN_JOB: trial status is modeled, but the scheduled expiration job still needs a deterministic local seam.
- BILLING_AUDIT_EVENT_FIXTURE: billing changes emit structured evidence today; a dedicated append-only billing audit fixture is still tracked in the audit suite.
- CANCELLATION_GRACE_PERIOD_PROVIDER_CLOCK: local tests cover `cancel_at_period_end`; provider-clock period-end transition remains a sandbox replay scenario.

## How To Run

```bash
pytest tests/billing/
pnpm test:billing
pnpm billing:webhooks:replay-test
```

## CI Artifact

CI should publish `artifacts/production-readiness/billing/junit.xml` and `artifacts/production-readiness/billing/summary.md`.
