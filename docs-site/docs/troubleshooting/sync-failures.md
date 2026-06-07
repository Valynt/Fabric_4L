---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Sync Failures

## Overview

Integration syncs can fail due to expired credentials, API rate limits, or malformed webhooks. This page explains how to diagnose the failure, apply retries, and prevent recurrence.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Admin access to **Integrations** settings.
- Credentials for the external system (Salesforce, HubSpot, etc.).
- Ability to view webhook delivery logs.

## Step-by-step instructions

### 1. Identify the failure mode

1. Open **Administration > Integrations**.
2. Select the failing connector.
3. Review the **Sync History** table.
4. Note the error category: **Auth**, **Rate Limit**, **Validation**, or **Timeout**.

### 2. Resolve authentication expiry

1. Click **Reconnect** on the connector card.
2. Complete the OAuth flow or re-enter API keys.
3. Verify the **Connection Test** returns green.
4. Trigger a manual sync to confirm.

### 3. Handle API rate limits

1. Check the external platform's rate limit dashboard (e.g., Salesforce Setup > API Usage).
2. In ValuePact, open the connector settings.
3. Reduce the **Batch Size** or increase the **Sync Interval**.
4. Enable **Adaptive Backoff** to let Layer 1 automatically slow requests.

### 4. Retry failed webhooks

1. Navigate to **Administration > Integrations > Webhooks**.
2. Find the webhook with a red **Delivery Status**.
3. Click **View Details** and inspect the HTTP response code.
4. If the payload is valid but the receiver timed out, click **Retry**.
5. For persistent 4xx errors, update the endpoint URL or payload mapping.

### 5. Verify network and firewall rules

1. Confirm the external system allows requests from ValuePact egress IPs.
2. Whitelist the IPs listed in **Administration > Security > Egress IPs**.
3. Test connectivity with `curl` or the built-in **Ping Endpoint** button.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage webhooks | Organization |
| Developer | View webhook logs | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Webhook retries: 5 automatic retries with exponential backoff (2^n seconds).
- <span class="vp-badge vp-badge--limit">Limit</span> Manual retry rate: max 20 per minute per webhook.
- <span class="vp-badge vp-badge--limit">Limit</span> Salesforce API: 100,000 calls per 24 hours per connected app.
- <span class="vp-badge vp-badge--limit">Limit</span> HubSpot API: 100 calls per 10 seconds per app.

## Troubleshooting

??? question "Issue: Sync fails with 'Invalid Grant' or 401"
    **Cause:** OAuth refresh token expired or was revoked by the admin on the external platform.
    **Resolution:**
    1. Re-authorize the connector.
    2. Ensure the connected app in the external system is not in "Blocked" state.
    3. Re-run the sync.

??? question "Issue: Webhook deliveries show 410 Gone"
    **Cause:** The endpoint URL no longer exists or the subscription was deleted.
    **Resolution:**
    1. Verify the endpoint URL in **Webhooks > Settings**.
    2. If the URL changed, update it and regenerate the webhook secret.
    3. Re-subscribe to the desired event types.

??? question "Issue: Sync partially succeeds with validation errors"
    **Cause:** Field mapping mismatch or required fields missing in the source.
    **Resolution:**
    1. Download the error report from **Sync History**.
    2. Map missing fields or mark them as optional in the connector schema.
    3. Re-run the sync.

## Related pages

- [Missing Data](missing-data.md)
- [Integration FAQ](../faq/integration-faq.md)
- [Webhooks](../integrations/webhooks.md)
- [APIs](../integrations/apis.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Intermittent failures, single connector | #valuepact-support Slack |
| P2 | All connectors failing for one tenant | support@valuepact.ai |
| P1 | Platform-wide webhook delivery failure | On-call page with subject "P1 Sync Outage" |
