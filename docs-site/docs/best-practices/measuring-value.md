---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Measuring Value

## Overview

Measuring value requires discipline in KPI selection, baseline establishment, and attribution. This page provides a framework for credible, defensible value reporting.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Initiatives created in ValuePact.
- Access to historical data for baseline calculation.
- Agreement from finance on currency and margin assumptions.

## Step-by-step instructions

### 1. Select the right KPIs

1. Limit each initiative to <span class="vp-badge vp-badge--limit">3–5 KPIs</span>.
2. Choose a mix of leading indicators (activity) and lagging indicators (outcome).
3. Ensure every KPI is measurable, time-bound, and tied to a financial or strategic outcome.

### 2. Establish a credible baseline

1. Pull 12 months of historical data before the initiative start date.
2. Calculate the average and standard deviation.
3. Document any known anomalies (seasonality, one-time events) in the initiative description.
4. Lock the baseline at approval time to prevent retroactive moving of the goalposts.

### 3. Choose an attribution model

| Model | Best For | Caution |
|-------|----------|---------|
| Direct | Single initiative with isolated impact | Overstates value in shared environments |
| Holdout | A/B or control group available | Requires statistical power and randomization |
| Incremental | Multiple initiatives overlap | Needs finance sign-off on allocation rules |
| Correlational | Exploratory analysis only | Cannot prove causation |

### 4. Capture actuals with evidence

1. Enter actuals at the same frequency as your reporting cadence.
2. Attach evidence: invoice, system screenshot, or signed attestation.
3. Tag actuals with the data source (Salesforce, manual entry, API).

### 5. Review and reconcile quarterly

1. Compare ValuePact totals to the general ledger.
2. Investigate variances greater than <span class="vp-badge vp-badge--limit">5%</span>.
3. Update assumptions and document the rationale.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Add actuals | Assigned initiatives |
| User | Edit baseline | Own initiatives (before approval) |
| Admin | Lock baseline | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> KPIs per initiative: 5.
- <span class="vp-badge vp-badge--limit">Limit</span> Baseline revision history: 10 versions.
- <span class="vp-badge vp-badge--limit">Limit</span> Evidence attachments per actual: 10.

## Troubleshooting

??? question "Issue: Baseline seems too high or too low"
    **Cause:** An outlier month skewed the average, or the historical period included a structural change.
    **Resolution:**
    1. Remove anomalous months with documented justification.
    2. Use a median instead of mean.
    3. Recalculate with a longer or shorter window.

??? question "Issue: Two initiatives claim the same benefit"
    **Cause:** Attribution was not defined during planning.
    **Resolution:**
    1. Convene initiative owners and finance.
    2. Agree on an incremental split (e.g., 60/40 based on effort).
    3. Document the split in both initiatives.

## Related pages

- [Data Quality](data-quality.md)
- [Reporting Cadence](reporting-cadence.md)
- [Report Discrepancies Troubleshooting](../troubleshooting/report-discrepancies.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | KPI or attribution methodology | Customer Success Manager |
| Urgent | Finance dispute over reported value | support@valuepact.ai |
