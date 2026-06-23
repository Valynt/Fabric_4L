---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Missing Data

## Overview

Data that appears incomplete or absent in dashboards usually traces back to ingestion delays, pipeline failures, or cache staleness. This page helps you identify the root cause and restore visibility quickly.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Access to the **Administration > Integrations** panel.
- Permission to view **Audit Logs**.
- Familiarity with your organization's data sources and sync schedules.

## Step-by-step instructions

### 1. Verify the sync schedule

1. Navigate to **Administration > Integrations**.
2. Select the connector that owns the missing data.
3. Check the **Last Sync** timestamp.
4. If the timestamp is older than the expected interval, click **Run Sync Now**.

### 2. Check ingestion job status

1. Open **Administration > Audit Logs**.
2. Filter by **Service: Layer 1 Ingestion** and **Status: Error**.
3. Look for recent failures tied to your tenant.
4. Note the error code and timestamp for support.

### 3. Inspect indexing lag

1. Go to **Dashboards & Reporting > Executive Dashboard**.
2. Hover over the data freshness indicator in the header.
3. If the lag exceeds <span class="vp-badge vp-badge--limit">15 minutes</span>, the search index may be behind.
4. Wait five minutes and refresh. Persistent lag requires a manual index rebuild.

### 4. Clear stale cache

1. Open the affected dashboard.
2. Press **Ctrl+Shift+R** (or **Cmd+Shift+R** on macOS) to hard reload.
3. If data still appears missing, append `?cache_bust=1` to the URL.
4. As an admin, you can also trigger **Invalidate Cache** from **Administration > Configuration > Cache**.

### 5. Validate tenant isolation

1. Confirm you are viewing the correct tenant context.
2. Check the tenant selector in the top navigation bar.
3. Data from Tenant A never appears in Tenant B. Switching tenants is the most common cause of "missing" records.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Invalidate cache | Organization |
| User | View audit logs | Own tenant |
| User | View dashboards | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Cache invalidation: max 10 times per hour per tenant.
- <span class="vp-badge vp-badge--limit">Limit</span> Manual sync: max 5 concurrent jobs per connector.
- <span class="vp-badge vp-badge--limit">Limit</span> Index rebuild window: scheduled during off-peak hours only.

## Troubleshooting

??? question "Issue: Records exist in the source but not in ValuePact"
    **Cause:** Ingestion filtered the records due to schema validation failures or missing required fields.
    **Resolution:**
    1. Open **Administration > Integrations > [Connector] > Sync History**.
    2. Download the latest validation report.
    3. Fix the source data or update the field mapping.
    4. Re-run the sync.

??? question "Issue: Recent records appear after a long delay"
    **Cause:** Layer 1 (Ingestion) succeeded, but Layer 2 (Extraction) or Layer 3 (Knowledge Graph) is backlogged.
    **Resolution:**
    1. Check **Audit Logs** for Layer 2 and Layer 3 job status.
    2. If either layer shows a queue depth alert, wait for the backlog to clear.
    3. Escalate to support if queue depth exceeds 10,000 messages.

??? question "Issue: Graph search returns no results for known entities"
    **Cause:** Neo4j index lag or a failed subgraph build.
    **Resolution:**
    1. Verify the entity exists in PostgreSQL via the **Data Explorer**.
    2. If present in PostgreSQL but absent from graph search, request an index rebuild.
    3. Contact support with the entity ID and tenant name.

## Related pages

- [Sync Failures](sync-failures.md)
- [Report Discrepancies](report-discrepancies.md)
- [Integration FAQ](../faq/integration-faq.md)
- [Data Quality Best Practices](../best-practices/data-quality.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Delay under 1 hour, isolated connector | #valuepact-support Slack |
| P2 | Delay over 1 hour or multiple connectors | support@valuepact.ai |
| P1 | Complete data loss suspicion, all connectors down | On-call page via support@valuepact.ai with subject "P1 Data Outage" |
