---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Audit Logs

Audit logs provide an immutable record of actions taken in your tenant. They support compliance investigations, security reviews, and operational troubleshooting.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Security Overview](index.md)
- Understanding of your compliance retention requirements

## What is logged

ValuePact logs the following event categories:

| Category | Events | Example |
|----------|--------|---------|
| Authentication | Login, logout, failed login, MFA enrollment | `user@example.com logged in` |
| User management | Invite, deactivate, delete, role change | `Alice invited Bob as Analyst` |
| Role management | Create role, assign permission, clone | `Finance Analyst role created` |
| Configuration | Workflow publish, field change, branding | `Custom field "region" added` |
| Record actions | Create, update, transition, approve | `Initiative #1234 approved` |
| Security | SSO change, MFA reset, password policy | `SSO certificate updated` |
| API | Key created, revoked, rate limit hit | `API key "integration-1" created` |

## Retention

| Tier | Default retention | Max retention | Cost |
|------|-------------------|---------------|------|
| Standard | 90 days | 1 year | Included |
| Compliance | 1 year | 7 years | Additional |

### Step-by-step: change retention

1. Go to **Admin** > **Security** > **Audit Logs**.
2. Click **Retention Settings**.
3. Select a **Retention Tier**.
4. Choose the **Max Retention Period**.
5. Click **Save**.

!!! warning "Retention reduction"
    Reducing retention deletes logs older than the new threshold immediately. Export data before reducing retention.

## Search

The audit log search supports filtering by user, event type, date range, and resource.

1. Open **Security** > **Audit Logs**.
2. Enter a keyword in the search bar.
3. Use filters:
   - **Date Range**
   - **User**
   - **Event Category**
   - **Resource Type**
4. Click **Search**.
5. Click an event to expand details.

## Export

You can export audit logs for external analysis or compliance submissions.

1. Run a search to define the export scope.
2. Click **Export**.
3. Choose a format: **CSV** or **JSON**.
4. Select **Delivery**: Download or email.
5. Click **Generate**.

<span class="vp-badge vp-badge--limit">Limit</span> Exports are limited to 100,000 events per request. For larger ranges, use date filters to chunk the export.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Search, export, and configure retention | Organization |
| Tenant Admin | Search, export, and configure retention | Organization |
| Content Admin | View audit logs | Organization |
| Analyst | View own audit events | Own user |
| Viewer | View own audit events | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Audit logs are immutable. Admins cannot edit or delete individual entries.

<span class="vp-badge vp-badge--limit">Limit</span> Search queries timeout after 30 seconds. Narrow filters for large tenants.

<span class="vp-badge vp-badge--limit">Limit</span> Export generation may take up to 10 minutes. You receive a notification when ready.

## Troubleshooting

??? question "Issue: expected event is missing"
    **Cause:** The event is outside the retention window, or the action was performed by a system process not captured in user audit.
    **Resolution:** Check the retention settings. Verify the event timestamp. System processes may log to separate operational logs.

??? question "Issue: export fails or is empty"
    **Cause:** The search filters returned no results, or the export exceeded the event limit.
    **Resolution:** Broaden the search filters. If the result set is large, export in smaller date ranges.

??? question "Issue: cannot view audit logs"
    **Cause:** Your role lacks audit log permission, or the feature is restricted in your tenant tier.
    **Resolution:** Ask a Tenant Admin to verify your role permissions. Upgrade the tenant tier if audit logs are not included.

## Related pages

- [Security Overview](index.md)
- [Authentication](authentication.md)
- [SSO](sso.md)
- [MFA](mfa.md)

## Escalation path

For audit log integrity concerns or export failures:

1. Verify the retention settings and search filters.
2. Retry the export with a smaller date range.
3. File a support ticket with the search criteria and expected event details.
4. Escalate to `#security-ops` if log tampering is suspected.
