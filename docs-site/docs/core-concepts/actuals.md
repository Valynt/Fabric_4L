---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Actuals

Actuals are realized historical values that ground forecasts in real data. They are ingested from source systems, reconciled against forecasts, and used to compute variance and realization rates.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A ValuePact account with active [projects](projects.md) or [initiatives](initiatives.md)
- Defined [value metrics](value-metrics.md) with baselines and targets
- Access to a data source or permission to enter data manually

## Overview

Actuals close the loop between forecast and reality. Without accurate actuals, [benefits tracking](benefits-tracking.md), [value realization](value-realization.md), and executive dashboards cannot function.

## Data sources

Actuals can be ingested from multiple sources:

| Source | Integration type | Frequency |
|--------|-----------------|-----------|
| Salesforce | Native integration | Hourly sync |
| HubSpot | Native integration | Hourly sync |
| Jira | Native integration | Daily sync |
| ServiceNow | Native integration | Daily sync |
| ERP / CSV | Manual upload or SFTP | On demand |
| API | Custom push via ValuePact API | Real time |

To configure a source:

1. Navigate to **Administration > Integrations**.
2. Select the source system.
3. Authenticate with least-privilege credentials.
4. Map source fields to ValuePact metrics.
5. Set sync frequency and start the connection.

## Ingestion

### Automatic ingestion

Connected systems push data on their configured schedule. The platform validates each row:

- Tenant ownership
- Metric ID existence
- Value type compatibility
- Date range validity

Invalid rows are quarantined in **Actuals > Reconciliation** for manual review.

### Manual entry

1. Open the account's **Actuals** tab.
2. Click **Add Actual**.
3. Select the metric, date, and value.
4. Enter the source (such as "Q3 financial review") and optional notes.
5. Click **Save**.

### Bulk upload

Upload a CSV with columns: `metric_id`, `date`, `value`, `unit`, `source`, `notes`. The system validates `metric_id` against the account's value model and rejects unknown IDs.

## Reconciliation

Reconciliation matches actuals to forecast periods and computes variance:

1. Open **Actuals > Reconciliation**.
2. Review unmapped rows and map them to metrics.
3. Review mapped rows with variance flags.
4. Accept, edit, or reject each row.
5. Click **Commit** to publish actuals to benefits tracking.

Reconciliation status indicators:

| Status | Meaning |
|--------|---------|
| Matched | Actual is linked to a forecast period |
| Unmapped | Metric ID is missing or unknown |
| Out of range | Value exceeds 200% of forecast |
| Stale | Actual is older than 90 days |

## Variance analysis

Once reconciled, actuals trigger variance analysis:

- **Period variance** = actual - forecast for the period
- **Cumulative variance** = sum of period variances to date
- **Variance %** = period variance / forecast

Variances exceeding 10% or $10K trigger alerts to project owners and initiative sponsors.

## Example

Actuals for the "Labor Efficiency" metric in Q2:

| Date | Source | Value | Forecast | Variance | Status |
|------|--------|-------|----------|----------|--------|
| Apr 2026 | Payroll system | $95K | $100K | -$5K | On track |
| May 2026 | Payroll system | $102K | $100K | +$2K | On track |
| Jun 2026 | Payroll system | $110K | $100K | +$10K | Alert triggered |

The positive drift in May and June suggests the project may exceed its annual target.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations and mapping rules | Organization |
| User | Enter and edit actuals | Assigned accounts |
| User | Reconcile and commit rows | Assigned accounts |
| Executive | View variance dashboards | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `actuals:write` to enter or reconcile; `actuals:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 50 rows per bulk upload request.

<span class="vp-badge vp-badge--limit">Limit</span> Actuals older than 12 months are archived automatically but remain queryable.

<span class="vp-badge vp-badge--limit">Limit</span> Reconciliation must be completed within 7 days of ingestion to avoid stale-data warnings.

## Troubleshooting

??? question "Issue: Actuals ingestion shows 'tenant mismatch'"
    **Cause:** The integration credentials belong to a different tenant, or the source record lacks a tenant identifier.
    **Resolution:** Verify the integration connection in **Administration > Integrations**. Ensure the source system tags records with the correct tenant ID.

??? question "Issue: Reconciliation shows many 'unmapped' rows"
    **Cause:** The source field names do not match the metric IDs in ValuePact.
    **Resolution:** Update the field mapping in the integration settings, or rename the CSV columns to match metric IDs exactly.

??? question "Issue: Variance alert fires for a known seasonal dip"
    **Cause:** The forecast does not model seasonality.
    **Resolution:** Edit the forecast in **Value Studio > Forecasts** and apply a seasonal adjustment factor, or add a note to the variance explaining the seasonality.

## Related pages

- [Forecasts](forecasts.md)
- [Benefits Tracking](benefits-tracking.md)
- [Value Realization](value-realization.md)
- [Value Metrics](value-metrics.md)

## Escalation path

For integration or sync issues, contact your admin or integration owner. For persistent variance anomalies, escalate to Value Engineering via your customer success manager.
