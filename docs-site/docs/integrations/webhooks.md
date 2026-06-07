---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Webhooks

## Overview

Webhooks allow external systems to receive real-time event notifications from ValuePact. This page explains how to configure endpoints, verify signatures, handle retries, and secure payload delivery.

## Who this is for

- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- A publicly accessible HTTPS endpoint.
- Ability to compute HMAC-SHA256 signatures.
- ValuePact Organization Admin role.

## Step-by-step instructions

### 1. Create a webhook endpoint

1. In ValuePact, go to **Administration > Integrations > Webhooks**.
2. Click **Add Endpoint**.
3. Enter the URL (must use HTTPS).
4. Select event types to subscribe to:
   - `initiative.created`
   - `initiative.updated`
   - `initiative.status_changed`
   - `benefit.actual_added`
   - `stakeholder.mentioned`
5. Save. The endpoint is created in **Pending** state.

### 2. Verify the endpoint

1. Click **Send Test Event**.
2. ValuePact sends a `ping` event to your URL.
3. Your endpoint must respond with HTTP 200 within 5 seconds.
4. On success, the endpoint status changes to **Active**.

### 3. Verify signatures

Every delivery includes these headers:

- `X-ValuePact-Signature`: HMAC-SHA256 of the payload
- `X-ValuePact-Timestamp`: Unix timestamp of the request
- `X-ValuePact-Event-ID`: Unique delivery identifier

Verify the signature in your handler:

```python
import hmac, hashlib

secret = b"whsec_..."
payload = request.body
timestamp = request.headers["X-ValuePact-Timestamp"]
signature = request.headers["X-ValuePact-Signature"]

expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, signature):
    raise ValueError("Invalid signature")
```

Reject payloads where the timestamp is older than 5 minutes to prevent replay attacks.

### 4. Handle retries

ValuePact retries failed deliveries with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1 | Immediate |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 4 | 8 seconds |
| 5 | 16 seconds |

After 5 failures, the delivery moves to a dead-letter queue. Admins are notified.

### 5. Rotate secrets

1. In **Webhooks > Settings**, click **Rotate Secret**.
2. A new secret is generated. The old secret remains valid for 24 hours.
3. Update your handler to accept both secrets during the overlap window.
4. Confirm successful deliveries with the new secret.
5. The old secret expires automatically.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Manage webhooks | Organization |
| Admin | Rotate secrets | Organization |
| Developer | View webhook logs | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Webhook endpoints per tenant: 20.
- <span class="vp-badge vp-badge--limit">Limit</span> Event payload size: 1 MB.
- <span class="vp-badge vp-badge--limit">Limit</span> Timeout: 5 seconds per delivery.
- <span class="vp-badge vp-badge--limit">Limit</span> Retries: 5 automatic.

## Troubleshooting

??? question "Issue: Endpoint never receives events"
    **Cause:** The URL is unreachable, the firewall blocks ValuePact IPs, or the endpoint is not verified.
    **Resolution:**
    1. Whitelist the egress IPs listed in **Administration > Security > Egress IPs**.
    2. Verify the endpoint responds to POST with HTTP 200.
    3. Re-send the test event.

??? question "Issue: Signature verification fails intermittently"
    **Cause:** The payload is being parsed before verification, altering whitespace or encoding.
    **Resolution:**
    1. Use the raw request body bytes for HMAC computation.
    2. Do not parse JSON before verifying the signature.
    3. Ensure the secret does not contain leading or trailing whitespace.

??? question "Issue: Duplicate events processed"
    **Cause:** Idempotency is not enforced on the receiver side.
    **Resolution:**
    1. Store processed `X-ValuePact-Event-ID` values for 24 hours.
    2. Skip processing if the ID was seen before.
    3. Return HTTP 200 even for duplicates to stop retries.

## Related pages

- [APIs](apis.md)
- [Integration FAQ](../faq/integration-faq.md)
- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Webhook setup or signature questions | #valuepact-dev Slack |
| P2 | Delivery failures for production endpoints | support@valuepact.ai |
| P1 | Suspected secret compromise or replay attack | security@valuepact.ai |
