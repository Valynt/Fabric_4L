---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Exporting & Sharing Reports

Generate PDF exports, schedule recurring reports, and manage sharing permissions for dashboards and deliverables. This guide covers exports from business cases, dashboard views, and scheduled report administration.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An approved business case or dashboard view.
- Export permissions for the initiative or portfolio.
- Reviewed [Dashboards & Reporting Overview](index.md).

## Step-by-step instructions

### PDF export from a business case

1. Open the business case detail page.
2. Click **Export PDF** from the action bar.
3. Wait for the export job. A spinner indicates progress.
4. When ready, a **Download** button appears. Click it to save the file.
5. The download link expires after **72 hours**.

### PDF export from a dashboard

1. Open any dashboard: Executive, Portfolio, Team, or Individual.
2. Click **Export** in the top-right corner.
3. Choose **Current View** or **Full Report**.
4. The export includes all visible filters and date ranges.

### Scheduled reports

1. Open any dashboard and click **Schedule Report**.
2. Configure the schedule:

| Setting | Options |
|---------|---------|
| Frequency | Daily, Weekly, Monthly |
| Day | For weekly/monthly: select the day of week or date |
| Time | UTC hour for delivery |
| Format | PDF or HTML |
| Recipients | Email addresses or user groups |

3. Click **Save**. The report is queued and sent at the scheduled time.
4. Manage schedules from **Workspace Settings → Governance → Audit Log**.

### Sharing permissions

1. Open the share dialog from any deliverable or dashboard.
2. Set visibility:
   - **Team** — all users in the tenant.
   - **Restricted** — only assigned users.
3. Generate a shareable link with an optional expiration date.
4. Copy the link and send it via email or chat.
5. To revoke, return to the share dialog and:
   - Remove a user from the list, or
   - Click **Disable Link** to invalidate the URL.

!!! warning "Warning: Export blocked cases cannot be shared externally"
    Business cases with **Export Blocked** status are restricted to internal draft viewing. Resolve validation failures before sharing.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Export / Share own | Assigned initiatives |
| Admin | Schedule / Revoke / Share any / Configure report templates | Tenant-wide |
| Executive | Export portfolio / Share with board | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Scheduled reports are limited to **10 per tenant**.
<span class="vp-badge vp-badge--limit">Limit</span> Shareable links expire after **30 days** by default.
<span class="vp-badge vp-badge--limit">Limit</span> PDF exports are capped at **50 pages** per generation.
<span class="vp-badge vp-badge--limit">Limit</span> Export file size is limited to **25 MB**.

## Troubleshooting

??? question "Issue: Export button is disabled"
    **Cause:** The case is not approved, or the document has not been generated.
    **Resolution:** Approve the case and trigger regeneration, then retry the export. Verify the trust state is **Export Ready**.

??? question "Issue: Scheduled report did not arrive"
    **Cause:** The tenant has reached the scheduled report limit, or the recipient list is invalid.
    **Resolution:** Check the report queue in **Workspace Settings → Governance → Audit Log** and remove inactive schedules. Verify recipient email addresses.

??? question "Issue: Share link returns 403"
    **Cause:** The link expired, or the recipient lacks tenant access.
    **Resolution:** Generate a new link with a longer expiration, or invite the user to the tenant first.

??? question "Issue: Export contains blank pages"
    **Cause:** The business case has sections with no generated content.
    **Resolution:** Open the case detail, review section generation status, and regenerate missing sections.

## Related pages

- [Executive Dashboard](executive-dashboard.md)
- [Building a Business Case](../end-user-guides/building-a-business-case.md)
- [Core Concepts: Business Cases](../core-concepts/business-cases.md)
- [Dashboards & Reporting Overview](index.md)

## Escalation path

For export generation failures lasting more than 10 minutes, open a support ticket with severity **P2** and the case or dashboard ID.
