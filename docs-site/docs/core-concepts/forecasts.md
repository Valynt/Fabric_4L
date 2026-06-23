---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Forecasts

Forecasts are predicted future values derived from driver trees, formulas, and scenario assumptions. They set expectations for stakeholders and provide the baseline against which actuals are compared.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- A ValuePact account with identified value drivers
- At least one [value metric](value-metrics.md) with a baseline
- A configured value pack with formulas

## Overview

Forecasts in ValuePact are scenario-driven and evidence-backed. They are not static spreadsheets; they update dynamically when inputs, baselines, or formulas change.

## Forecast methods

The platform supports two primary methods:

| Method | Description | Best for |
|--------|-------------|----------|
| Formula-driven | Baseline + formula + assumptions = forecast | Quantitative drivers with known inputs |
| Benchmark-informed | Industry peer data informs the target range | New initiatives without historical baseline |

Formula-driven forecasts are computed by the Layer 3 formula engine. Benchmark-informed forecasts pull percentile ranges from Layer 6 datasets.

## Scenario planning

Every forecast is computed across three scenarios:

| Scenario | Assumption adjustment | Use case |
|----------|----------------------|----------|
| Conservative | 80% of expected benefit, 120% of expected cost | Risk-averse planning, board reporting |
| Expected | Baseline assumptions from value model | Standard planning, most likely case |
| Optimistic | 120% of expected benefit, 90% of expected cost | Best-case planning, upside communication |

To configure scenario assumptions:

1. Open the account's **Value Studio** workspace.
2. Click **Forecasts**.
3. Select a driver.
4. Edit the scenario multipliers or input overrides.
5. Click **Recalculate**.

## Confidence intervals

Forecasts display confidence intervals based on:

- **Input variance** — standard deviation of historical actuals (if available)
- **Model confidence** — derived from evidence quality and source count
- **Benchmark spread** — p25 to p75 range from Layer 6 peer data

A forecast with high evidence quality and low input variance shows a narrow confidence band. A forecast with limited data shows a wide band and is flagged for review.

## Time horizons

Forecasts can span:

- **Short-term** — 3 to 6 months, tied to project milestones
- **Medium-term** — 1 to 2 years, tied to initiative targets
- **Long-term** — 3 to 5 years, tied to strategic planning

The default time horizon is pulled from the value pack. Users can override it per account.

## Forecast revision history

Forecasts are versioned. Each revision captures:

- **Revision number** — auto-incremented
- **Author** — who made the change
- **Change summary** — auto-generated diff of variables and assumptions
- **Timestamp** — when the revision was saved

To view history:

1. Open **Value Studio > Forecasts**.
2. Click **Revision History** next to the driver name.
3. Select a revision to preview or restore.

Restoring a revision creates a new revision with the old values, preserving the audit trail.

### Locking forecasts

Once a business case is approved, its underlying forecast is automatically locked. Locked forecasts display a padlock icon. To modify a locked forecast, you must create an amendment or a new forecast branch.

## Example

A forecast for "Labor Efficiency" across three scenarios:

| Scenario | Annual Savings | Confidence Interval | NPV (3yr) |
|----------|---------------|---------------------|-----------|
| Conservative | $480K | $420K–$540K | $1.1M |
| Expected | $600K | $540K–$660K | $1.4M |
| Optimistic | $720K | $660K–$780K | $1.7M |

The business case is built on the Expected scenario, with the Conservative scenario used for risk disclosure.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure forecast templates and scenarios | Organization |
| User | Create and edit forecasts | Assigned accounts |
| Executive | View forecast comparisons across accounts | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `forecasts:write` to edit; `forecasts:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 20 forecast revisions per account per month.

<span class="vp-badge vp-badge--limit">Limit</span> Forecast time horizons cannot exceed 5 years.

<span class="vp-badge vp-badge--limit">Limit</span> Confidence intervals are hidden if fewer than 3 historical data points exist for the metric.

## Troubleshooting

??? question "Issue: Forecast does not update after changing a variable"
    **Cause:** The variable is not linked to the forecast driver, or the forecast is locked.
    **Resolution:** Verify the variable mapping in **Value Studio > Driver Tree**. If the forecast is locked, create a revision.

??? question "Issue: Confidence interval is extremely wide"
    **Cause:** The metric has high historical variance or low evidence quality.
    **Resolution:** Add more evidence sources, tighten the baseline measurement, or reduce the scenario multiplier range.

??? question "Issue: Benchmark-informed forecast shows 'no data'"
    **Cause:** The account industry does not match a Layer 6 benchmark dataset.
    **Resolution:** Verify the account industry in **Account Settings**, or switch the forecast method to formula-driven.

??? question "Issue: Restored revision does not update linked business case"
    **Cause:** Business cases reference forecast snapshots, not live forecasts.
    **Resolution:** Regenerate the business case from the restored forecast revision and submit it for re-approval.

## Related pages

- [ROI Calculations](roi-calculations.md)
- [Actuals](actuals.md)
- [Value Metrics](value-metrics.md)
- [Business Cases](business-cases.md)

## Escalation path

For scenario configuration issues, contact your value pack admin. For forecast computation errors, open a support ticket with the account ID and driver name.
