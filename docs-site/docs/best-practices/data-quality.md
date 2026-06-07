---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Data Quality

## Overview

Poor data quality destroys trust in value reporting. This page describes how to validate inputs, maintain source credibility, and trace data lineage so every number is defensible.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Access to **Administration > Integrations** and **Data Explorer**.
- Understanding of source systems (CRM, ERP, spreadsheet).
- Defined data owners for each integration.

## Step-by-step instructions

### 1. Validate at the point of entry

1. Enable required field validation on custom fields.
2. Set data-type rules (numeric, date, enum) to prevent free-text pollution.
3. Use dropdowns instead of open text where possible.

### 2. Assign data owners

1. For each integration, name a business owner and a technical owner.
2. Document the owner in the connector settings description field.
3. Review ownership quarterly during portfolio reviews.

### 3. Monitor freshness

1. Set a freshness SLA for each source: daily, weekly, or real-time.
2. Configure alerts in **Administration > Integrations > Health** when a source exceeds its SLA.
3. Treat stale data as a P2 incident if it blocks month-end reporting.

### 4. Maintain lineage

1. Ensure every actual includes a source system reference.
2. For manual entries, require an evidence link or attestation.
3. Use the **Lineage** tab in the initiative detail view to trace a number back to its origin.

### 5. Run periodic quality audits

1. Quarterly, export a sample of 20 initiatives.
2. Check for null required fields, duplicate records, and orphaned actuals.
3. Score each initiative red, amber, or green.
4. Publish the scorecard to initiative owners.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure validation rules | Organization |
| Admin | View data health | Organization |
| User | Edit data in assigned initiatives | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Custom validation rules per entity: 20.
- <span class="vp-badge vp-badge--limit">Limit</span> Freshness SLA minimum: 1 hour.
- <span class="vp-badge vp-badge--limit">Limit</span> Lineage depth displayed: 5 hops.

## Troubleshooting

??? question "Issue: Duplicate records after a sync"
    **Cause:** The source system changed a unique identifier, or the deduplication key was too narrow.
    **Resolution:**
    1. Identify the duplicate set in **Data Explorer**.
    2. Update the deduplication key to include a composite of `email + source_id`.
    3. Merge duplicates and re-run the sync.

??? question "Issue: Manual actuals lack evidence links"
    **Cause:** Users skipped the field because it was optional.
    **Resolution:**
    1. Make the evidence link required for manual entries.
    2. Train users that an attestation is acceptable when a system link is unavailable.

## Related pages

- [Missing Data Troubleshooting](../troubleshooting/missing-data.md)
- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)
- [Measuring Value](measuring-value.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Data quality coaching | Customer Success Manager |
| Urgent | Source system corruption affecting many records | support@valuepact.ai |
