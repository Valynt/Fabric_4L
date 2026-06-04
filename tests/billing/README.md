# Billing Readiness Suite

## What This Suite Validates

This suite centralizes billing, subscription, webhook, entitlement, trial, and tenant-scope readiness checks without calling Stripe or any paid external service.

## Production Risks Covered

- Subscription lifecycle changes that are not tenant-scoped.
- Billing webhooks that are not idempotent or replay-safe.
- Entitlement decisions drifting from billing usage and plan contracts.
- Trial or payment states that are not represented in schemas and tests.

## Existing Coverage Aggregated

- `services/billing/tests/`
- `tests/contract/test_billing_contracts.py`
- `tests/integration/billing_entitlements/`
- `services/layer4-agents/tests/test_billing_service.py`
- `services/layer4-agents/tests/test_billing_webhook_security_consistency.py`
- `tests/recovery/test_restore_billing_state.py`

## Known Gaps

- CHECKOUT_PROVIDER_SANDBOX: checkout provider redirects are not exercised here because this suite cannot require Stripe credentials.
- PAYMENT_FAILURE_PROVIDER_EVENT: payment failure provider payloads are policy-gated but do not yet have a full local end-to-end fixture.
- TRIAL_EXPIRATION_CLOCK_DRIVEN_JOB: trial status is modeled, but the scheduled expiration job still needs a deterministic local seam.

## How To Run

```bash
pytest tests/billing/
pnpm test:billing
```

## CI Artifact

CI should publish `artifacts/production-readiness/billing/junit.xml`.

