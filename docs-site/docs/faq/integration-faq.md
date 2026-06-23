---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Integration FAQ

## Overview

This page answers common questions about connecting ValuePact to external systems, building custom integrations, and securing webhook traffic.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Admin access to **Integrations** settings.
- API credentials for the external system.
- Understanding of REST APIs and JSON (for custom integrations).

## Frequently asked questions

### 1. Which connectors are available out of the box?

ValuePact provides native connectors for Salesforce, HubSpot, Slack, Microsoft Teams, Jira, and ServiceNow. Additional connectors are available through the integration marketplace. Requests for new connectors can be submitted via the **Feature Request** portal.

### 2. Can I build a custom integration?

Yes. ValuePact exposes a REST API and webhook system documented in the [API section](../api/index.md). You can use the OpenAPI specification to generate client SDKs in Python, TypeScript, Go, or Java. Custom integrations should authenticate using tenant-scoped API keys.

### 3. How do I secure webhook payloads?

Every webhook includes a `X-ValuePact-Signature` header. The signature is an HMAC-SHA256 hash of the payload using your webhook secret. Verify the signature before processing the payload. Rotate secrets from **Administration > Integrations > Webhooks > Rotate Secret**.

### 4. What data does each connector sync?

| Connector | Sync Direction | Entities | Frequency |
|-----------|---------------|----------|-----------|
| Salesforce | Bidirectional | Accounts, Opportunities, Contacts | Every 15 min |
| HubSpot | Bidirectional | Companies, Deals, Contacts | Every 15 min |
| Slack | Outbound | Notifications, Commands | Real-time |
| Teams | Outbound | Notifications, Tabs | Real-time |
| Jira | Bidirectional | Issues, Status, Comments | Every 15 min |
| ServiceNow | Bidirectional | Incidents, CMDB CIs | Every 15 min |

### 5. Can I filter what gets synced?

Yes. Each connector supports field-level and row-level filters. For example, you can limit Salesforce opportunity sync to records where `StageName = 'Closed Won'` or exclude specific HubSpot properties. Filters are configured in **Integrations > [Connector] > Sync Rules**.

### 6. What happens if the external API is down?

Layer 1 (Ingestion) queues sync jobs in Redis. If the external API returns a 5xx or timeout, the job retries with exponential backoff up to 5 times. After the final failure, the job is moved to a dead-letter queue and the admin is notified.

### 7. Do you support event-driven architectures?

Yes. ValuePact emits webhook events for entity creation, updates, and deletions. You can subscribe to specific event types and route them to your own event bus (e.g., AWS EventBridge, Azure Event Grid, or Google Pub/Sub) using a simple forwarder.

### 8. How do I test a webhook endpoint?

1. Go to **Administration > Integrations > Webhooks**.
2. Click **Add Endpoint**.
3. Enter your URL and select event types.
4. Click **Send Test Event**.
5. Inspect the delivery logs for HTTP 200 and signature validation.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage webhooks | Organization |
| Developer | View API keys | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Webhook endpoints: 20 per tenant.
- <span class="vp-badge vp-badge--limit">Limit</span> API rate limit: 1,000 requests per minute per API key.
- <span class="vp-badge vp-badge--limit">Limit</span> Custom connector SDK timeout: 30 seconds.
- <span class="vp-badge vp-badge--limit">Limit</span> Event payload size: 1 MB.

## Troubleshooting

??? question "Issue: Custom integration receives 403 Forbidden"
    **Cause:** The API key lacks the required scope, or the tenant header is missing.
    **Resolution:**
    1. Verify the API key has scopes `initiatives:read` and `benefits:write`.
    2. Include `X-Tenant-ID` in every request header.
    3. Regenerate the key if it was revoked.

??? question "Issue: Webhook signature validation fails"
    **Cause:** The secret was rotated, or the payload was modified in transit.
    **Resolution:**
    1. Copy the latest secret from **Webhooks > Settings**.
    2. Ensure your validator uses raw request body bytes, not parsed JSON.
    3. Verify the timestamp in `X-ValuePact-Timestamp` is within 5 minutes of server time.

## Related pages

- [API Overview](../api/overview.md)
- [Webhooks](../integrations/webhooks.md)
- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Connector or API questions | #valuepact-dev Slack |
| Urgent | Production integration down | support@valuepact.ai |
| Critical | Suspected security issue with a webhook | security@valuepact.ai |
