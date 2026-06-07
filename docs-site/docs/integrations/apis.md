---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# APIs

## Overview

ValuePact exposes a REST API for programmatic access to initiatives, benefits, stakeholders, dashboards, and integrations. This page covers authentication, rate limits, error handling, and available SDKs.

## Who this is for

- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- ValuePact tenant with API access enabled.
- Ability to generate API keys from **Administration > Security > API Keys**.
- Familiarity with REST conventions and JSON.

## Step-by-step instructions

### 1. Generate an API key

1. Log in to ValuePact as an admin.
2. Go to **Administration > Security > API Keys**.
3. Click **New Key**.
4. Name the key and select scopes:
   - `initiatives:read`
   - `initiatives:write`
   - `benefits:read`
   - `benefits:write`
   - `webhooks:manage`
5. Copy the key immediately. It is shown only once.

### 2. Authenticate requests

Include the API key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer vp_live_xxxxxxxx" \
     -H "X-Tenant-ID: your-tenant-id" \
     https://api.valuepact.ai/v1/initiatives
```

The `X-Tenant-ID` header is mandatory. Requests without it return `400 Bad Request`.

### 3. Understand rate limits

| Tier | Requests per minute | Burst |
|------|---------------------|-------|
| Standard | 1,000 | 100 |
| Enterprise | 5,000 | 500 |

Rate limit headers are included in every response:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

When exceeded, the API returns `429 Too Many Requests`. Retry after the timestamp in `Retry-After`.

### 4. Handle errors

| Status | Meaning | Resolution |
|--------|---------|------------|
| 400 | Bad Request | Check request body and query parameters |
| 401 | Unauthorized | Regenerate or rotate the API key |
| 403 | Forbidden | Verify scopes and tenant isolation |
| 404 | Not Found | Confirm the resource ID and tenant |
| 409 | Conflict | Resource already exists or optimistic lock failure |
| 422 | Validation Error | Review the `errors` array in the response |
| 429 | Rate Limited | Back off and retry with exponential jitter |
| 500 | Server Error | Retry once; if persistent, contact support |

### 5. Use SDKs

ValuePact publishes official SDKs:

- **Python:** `pip install valuepact`
- **TypeScript:** `npm install @valuepact/sdk`
- **Go:** `go get github.com/valuepact/sdk-go`

Each SDK handles authentication, pagination, retries, and error parsing.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Manage API keys | Organization |
| Admin | Configure scopes | Organization |
| Developer | Use API keys | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> API keys per tenant: 50.
- <span class="vp-badge vp-badge--limit">Limit</span> Key lifetime: 365 days (rotation enforced).
- <span class="vp-badge vp-badge--limit">Limit</span> Max page size: 500 records.
- <span class="vp-badge vp-badge--limit">Limit</span> Request payload size: 5 MB.

## Troubleshooting

??? question "Issue: 401 Unauthorized on every request"
    **Cause:** The key was revoked, expired, or the `Authorization` header format is incorrect.
    **Resolution:**
    1. Verify the header is `Authorization: Bearer vp_live_...`.
    2. Check the key status in **Administration > Security > API Keys**.
    3. Generate a new key if needed.

??? question "Issue: 403 Forbidden despite valid key"
    **Cause:** The key lacks the required scope, or the `X-Tenant-ID` does not match the key’s tenant.
    **Resolution:**
    1. Confirm the key has the correct scopes.
    2. Verify the tenant ID from **Administration > Tenant Settings**.
    3. Ensure you are not mixing sandbox and production credentials.

??? question "Issue: Pagination returns duplicate records"
    **Cause:** Cursor-based pagination was interrupted by a write during iteration.
    **Resolution:**
    1. Use `cursor` instead of `offset` for large datasets.
    2. Snapshot the data before export, or retry from the last cursor.

## Related pages

- [Webhooks](webhooks.md)
- [Integration FAQ](../faq/integration-faq.md)
- [API Overview](../api/overview.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | SDK or schema questions | #valuepact-dev Slack |
| P2 | Rate limit or auth issues blocking production | support@valuepact.ai |
| P1 | API security vulnerability suspected | security@valuepact.ai |
