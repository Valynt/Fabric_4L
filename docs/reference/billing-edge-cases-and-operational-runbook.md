# Billing Edge Cases and Operational Runbook

## Overview

This document covers edge cases, failure modes, and operational procedures for the Value Fabric billing and subscription system.

## Dunning (Failed Payment Handling)

### Behavior
- When a subscription payment fails, Stripe enters the subscription into `past_due` state
- The frontend displays a warning badge with "Past Due" status
- Admins can update payment methods via the Stripe Customer Portal

### Current State
- Dunning emails are handled by Stripe (not internally generated)
- No automated dunning workflow exists in Layer 4 or Layer 7
- Subscription remains `past_due` until payment succeeds or grace period expires

### Recommended Actions
1. Monitor `invoice.payment_failed` webhooks
2. Alert admins when subscription enters `past_due`
3. Provide clear payment method update path

## Grace Periods

### Behavior
- Grace period logic is determined by Stripe subscription settings
- During grace period, entitlements remain active
- After grace period expires, subscription moves to `unpaid` or `canceled`

### Current State
- No custom grace-period logic in Layer 4
- No auto-downgrade on grace period expiry
- Frontend shows warning when `cancel_at_period_end` is true

### Recommended Actions
1. Implement grace-period countdown in admin UI
2. Add automated downgrade to "free" plan on expiry
3. Emit audit events on grace-period state transitions

## Webhook Reconciliation

### Behavior
- Stripe webhooks are received at `/billing/webhook`
- Events are persisted to durable inbox before processing
- Processing includes bounded retries (max 5 attempts)

### Supported Events
- `invoice.created` — create invoice record
- `invoice.finalized` — finalize invoice
- `invoice.paid` — record payment
- `invoice.payment_failed` — mark past due
- `customer.subscription.updated` — sync subscription state
- `customer.subscription.deleted` — handle cancellation

### Failure Handling
- Webhook signature is validated using `STRIPE_WEBHOOK_SECRET`
- Invalid signatures return HTTP 400
- Processing failures are retried with exponential backoff
- After max retries, events are sent to dead-letter queue

## Provider Sync Errors

### Stripe API Errors
- Rate limits: back off and retry with jitter
- Network errors: retry up to 3 times
- Invalid requests: log and alert, do not retry

### Data Drift
- Subscription state in Stripe is source of truth
- Layer 4 caches subscription data with TTL
- Sync endpoint (`POST /billing/customer/sync`) forces re-sync

### Recommended Monitoring
1. Track webhook delivery success rate
2. Alert on sync failures > 1% over 5 minutes
3. Monitor Stripe API error rates

## Usage Limits and Overage

### Hard Limits
- `ingest_usage_event` pre-checks limits via `OverageService.validate_request()`
- Returns HTTP 429 when limit is exceeded
- Events are rejected before ingestion

### Soft Limits
- Usage is tracked and surfaced in admin UI
- Warning threshold default: 80%
- Danger threshold: 100%

### Overage Billing
- Overage rate is configured per plan
- Overage charges are calculated during invoice finalization

## Upgrade/Downgrade Flows

### Upgrade
1. Admin selects new plan in UI
2. Frontend calls `POST /billing/checkout` with new plan_id
3. Stripe checkout session is created
4. On success, subscription is updated
5. Audit event `BILLING_PLAN_CHANGED` is emitted

### Downgrade
1. Same flow as upgrade
2. Proration behavior is controlled by Stripe settings
3. Subscription changes take effect at next billing cycle

## Cancellation and Reactivation

### Cancellation
1. Admin clicks cancel in Stripe Portal or admin UI
2. Subscription is marked `cancel_at_period_end`
3. Frontend shows warning badge
4. At period end, subscription becomes `canceled`

### Reactivation
1. Admin calls `POST /billing/subscription/reactivate`
2. Subscription resumes if within grace period
3. Audit event `BILLING_SUBSCRIPTION_REACTIVATED` is emitted

## Known Capability Gaps

The following features are not yet implemented and are tracked for future work:

1. **Automated dunning workflows** — Internal email sequences for failed payments
2. **Grace-period auto-downgrade** — Automatic downgrade to free plan on expiry
3. **Seat limits** — Per-organization user count limits
4. **Billing contact management** — Multiple billing contacts per tenant
5. **Invoice PDF generation** — Native PDF generation (currently relies on Stripe)
6. **Tax calculation** — Automated tax calculation for jurisdictions
7. **Currency conversion** — Multi-currency support beyond USD

## Audit Trail

All billing mutations emit audit events:

| Action | Endpoint | Description |
|--------|----------|-------------|
| `BILLING_SUBSCRIPTION_CREATED` | Checkout success | New subscription |
| `BILLING_SUBSCRIPTION_UPDATED` | Plan change | Upgrade/downgrade |
| `BILLING_SUBSCRIPTION_CANCELED` | Cancel | Cancellation |
| `BILLING_SUBSCRIPTION_REACTIVATED` | Reactivate | Reactivation |
| `BILLING_PLAN_CHANGED` | Plan update | Explicit plan change |
| `BILLING_CHECKOUT_INITIATED` | Checkout | Checkout started |
| `BILLING_PORTAL_OPENED` | Portal | Portal session |
| `BILLING_INVOICE_CREATED` | Create invoice | Invoice creation |
| `BILLING_INVOICE_FINALIZED` | Finalize | Invoice finalized |
| `BILLING_INVOICE_VOIDED` | Void | Invoice voided |
| `BILLING_USAGE_INGESTED` | Usage event | Usage recorded |
| `BILLING_CUSTOMER_SYNCED` | Sync | Provider sync |
| `BILLING_WEBHOOK_RECEIVED` | Webhook | Webhook processed |

## Operational Checklist

### Daily
- [ ] Check Stripe webhook delivery dashboard
- [ ] Review failed payment count
- [ ] Verify usage ingestion is current

### Weekly
- [ ] Run `POST /billing/customer/sync` for high-value accounts
- [ ] Review audit log for anomalies
- [ ] Check for overdue invoices

### Monthly
- [ ] Reconcile Stripe revenue with internal records
- [ ] Review and update plan limits
- [ ] Audit webhook endpoint configuration
