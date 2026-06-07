---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Value Metrics

Value metrics are the measurable indicators that define what "good" looks like in a value model. They include KPIs, formulas, baselines, and targets that ground forecasts and outcomes in numbers.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A ValuePact account with a configured value pack
- At least one identified [value driver](roi-calculations.md) or [opportunity](opportunities.md)
- Baseline data from the customer or from ingested sources

## Overview

Value metrics connect abstract value drivers to concrete numbers. They appear in driver trees, feed ROI calculations, and provide the basis for [benefits tracking](benefits-tracking.md) and [actuals](actuals.md) reconciliation.

## Types of metrics

| Type | Description | Example |
|------|-------------|---------|
| Efficiency | Output per unit of input | FTE hours saved per week |
| Financial | Monetary value | Annual cost avoidance |
| Quality | Error or defect rate | Scrap percentage |
| Speed | Time-based performance | Sales cycle days |
| Risk | Probability-weighted exposure | Fraud incidents prevented |
| Throughput | Volume processed | Additional patients per year |

## KPI definitions

A KPI (key performance indicator) in ValuePact includes:

- **Name** — human-readable label
- **Unit** — such as `USD`, `hours`, `percentage`, `count`
- **Formula** — optional computed expression
- **Baseline** — the starting value before intervention
- **Target** — the goal value at project completion
- **Data source** — manual entry, CRM, ERP, or API integration
- **Frequency** — how often the metric is measured (daily, weekly, monthly, quarterly)

## Baselines and targets

Baselines establish the "before" state. Targets establish the "after" state. Together they define the value delta that drives ROI.

To set a baseline:

1. Open the account's **Value Studio** workspace.
2. Navigate to the **Value Model** tab.
3. Select a driver and expand its metric panel.
4. Click **Set Baseline**.
5. Enter the value, source, and date.
6. Click **Save**.

To set a target, repeat the process with **Set Target**.

!!! tip "Best practice"
    Baselines should be validated with the customer before a business case is approved. Unvalidated baselines are flagged with a warning icon.

## Formulas

Metrics can be simple values or computed formulas. For example:

```yaml
metric: annual_savings
formula: affected_fte_count * hours_saved_per_fte_weekly * 52 * fully_loaded_cost_per_hour
inputs:
  - affected_fte_count
  - hours_saved_per_fte_weekly
  - fully_loaded_cost_per_hour
output_unit: USD
```

When any input changes, the platform recalculates the metric and propagates the update to linked forecasts and ROI calculations.

## Tracking metric health

The metric health dashboard shows:

- **Current value** — latest actual or computed value
- **Progress to target** — percentage of target achieved
- **Trend** — direction over the last four periods
- **Variance** — deviation from forecast for the current period

### Metric calibration

Calibrated metrics are more defensible in board-level discussions. Calibration involves:

1. **Baseline validation** — confirm the baseline with the customer or source system
2. **Measurement protocol** — document how the metric is collected and who owns the data
3. **Review cadence** — schedule periodic reviews to confirm the metric remains relevant

To mark a metric as calibrated:

1. Open the metric panel in **Value Studio**.
2. Click **Calibration**.
3. Upload validation evidence or enter reviewer name and date.
4. Click **Mark Calibrated**.

Calibrated metrics display a checkmark icon. Uncalibrated metrics trigger a warning in business case exports.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure metric templates and units | Organization |
| User | Set baselines and targets | Assigned accounts |
| User | Edit metric values | Assigned accounts |
| Executive | View metric health across initiatives | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `metrics:write` to edit; `metrics:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 200 metrics per account.

<span class="vp-badge vp-badge--limit">Limit</span> Formula evaluation depth is limited to 5 nested expressions to prevent circular references.

<span class="vp-badge vp-badge--limit">Limit</span> Baselines cannot be modified after a business case using them is approved. Create a revision instead.

## Troubleshooting

??? question "Issue: Metric shows 'computation error'"
    **Cause:** A formula references a missing input, or a division by zero occurred.
    **Resolution:** Inspect the formula in **Value Studio > Metrics**. Add the missing input or adjust the expression to handle zero denominators.

??? question "Issue: Baseline cannot be edited"
    **Cause:** The baseline is locked because an approved business case depends on it.
    **Resolution:** Create a new baseline revision in **Metric History**, or contact an admin to unlock.

??? question "Issue: Metric value does not update after actuals ingestion"
    **Cause:** The actuals row is not mapped to the correct metric ID.
    **Resolution:** Open **Actuals > Reconciliation**, find the unmapped row, and link it to the metric.

??? question "Issue: Calibrated metric icon disappeared after forecast revision"
    **Cause:** Calibration is tied to a specific baseline. When the baseline changes, calibration must be reconfirmed.
    **Resolution:** Re-open the metric panel, review the new baseline, and re-apply calibration if the measurement protocol still applies.

## Related pages

- [ROI Calculations](roi-calculations.md)
- [Forecasts](forecasts.md)
- [Actuals](actuals.md)
- [Outcomes](outcomes.md)

## Escalation path

For formula or template configuration issues, contact your value pack admin. For computation errors that persist after validation, open a support ticket with the metric ID and formula text.
