---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Report Discrepancies

## Overview

Numbers in dashboards and exported reports may diverge from expectations due to timezone math, aggregation logic, or stale cache. This page shows you how to audit a discrepancy and find the authoritative value.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Access to the dashboard or report showing the discrepancy.
- Knowledge of the source system’s timezone and currency settings.
- Permission to view **Audit Logs** and **Data Explorer**.

## Step-by-step instructions

### 1. Confirm the comparison baseline

1. Identify the exact number you are comparing against (source system, prior report, or manual calculation).
2. Note the date range, currency, and filters applied in both systems.
3. Screenshot both values for reference.

### 2. Check timezone alignment

1. Open **Administration > Configuration > Regional Settings**.
2. Verify the tenant default timezone.
3. Compare with the source system timezone.
4. If they differ, re-run the report using **UTC** as a neutral reference.

### 3. Review aggregation logic

1. Hover over the metric name in the dashboard.
2. Click the **i** icon to open the metric definition.
3. Confirm whether the metric uses **sum**, **average**, **weighted average**, or **latest value**.
4. Reconcile with the source system’s aggregation method.

### 4. Validate filter scope

1. Open the report filters panel.
2. Check for hidden defaults such as **Active Only**, **My Initiatives**, or **Fiscal Year**.
3. Apply identical filters in the source system.
4. If the discrepancy disappears, document the filter difference for your team.

### 5. Clear cache and re-export

1. Hard refresh the dashboard (**Ctrl+Shift+R**).
2. Click **Export > CSV** and open the file.
3. Compare the raw export against the UI total.
4. If the export matches the source but the UI does not, cache invalidation is needed.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure regional settings | Organization |
| Admin | Invalidate cache | Organization |
| User | View dashboards | Assigned initiatives |
| User | Export reports | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> CSV export: max 100,000 rows per file.
- <span class="vp-badge vp-badge--limit">Limit</span> Cache TTL: 5 minutes for dashboard tiles, 1 hour for exports.
- <span class="vp-badge vp-badge--limit">Limit</span> Historical re-aggregation: available for the last 90 days only.

## Troubleshooting

??? question "Issue: Dashboard total is lower than source system total"
    **Cause:** Tenant or initiative filters are narrowing the dataset, or archived records are excluded.
    **Resolution:**
    1. Remove all optional filters.
    2. Toggle **Include Archived** in the filter panel.
    3. Re-compare the totals.

??? question "Issue: Monthly average does not match manual calculation"
    **Cause:** The metric uses a weighted average or excludes null months, while your manual math includes them.
    **Resolution:**
    1. Open the metric definition tooltip.
    2. Note the exact denominator (e.g., "months with data" vs. "calendar months").
    3. Recalculate using the documented logic.

??? question "Issue: Currency conversion differs by a few cents"
    **Cause:** ValuePact uses daily midpoint rates, while the source may use end-of-day or contract rates.
    **Resolution:**
    1. Check **Administration > Configuration > Currency** for the conversion policy.
    2. If precision is critical, export raw values and apply your own rates.

## Related pages

- [Missing Data](missing-data.md)
- [Measuring Value Best Practices](../best-practices/measuring-value.md)
- [Reporting Cadence Best Practices](../best-practices/reporting-cadence.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Single metric mismatch, explainable | #valuepact-support Slack |
| P2 | Widespread discrepancies across dashboards | support@valuepact.ai |
| P1 | Financial reporting impact, audit deadline | On-call page with subject "P1 Reporting Discrepancy" |
