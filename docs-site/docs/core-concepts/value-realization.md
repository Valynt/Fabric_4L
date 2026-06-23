---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Value Realization

Value realization is the end-to-end lifecycle that tracks forecasted value from first signal through to realized outcome. It ensures the promises made in business cases and ROI models become measurable, attributable results.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A ValuePact account with at least one business case or ROI calculation
- [Forecasts](forecasts.md) and [actuals](actuals.md) configured for the account
- Access to the account's [projects](projects.md) and [initiatives](initiatives.md)

## Overview

Value realization connects four layers:

1. **Forecasted value** — predicted from driver trees and ROI scenarios
2. **Committed value** — approved in business cases and project charters
3. **In-flight value** — tracked during project execution via benefits monitoring
4. **Realized value** — confirmed by actuals and measured outcomes

The platform computes realization rates by comparing actuals to forecasts over time. This gives executives a single view of whether value is materializing as planned.

## How it works

### Signal to forecast

During intelligence gathering, the platform extracts signals from documents, transcripts, and web sources. These signals map to [value drivers](roi-calculations.md), which feed formula-based [forecasts](forecasts.md). Each forecast carries a confidence score and a scenario label (conservative, expected, optimistic).

Signals pass through the Ground Truth validation state machine before they influence forecasts:

| Ground Truth Status | Forecast impact |
|---------------------|----------------|
| Extracted | Flagged for review; not used in default forecasts |
| Supported | Included in optimistic scenarios only |
| Corroborated | Included in expected and optimistic scenarios |
| Approved | Included in all scenarios |

### Forecast to commitment

Forecasts are packaged into [business cases](business-cases.md). When a business case is approved, its value claims become committed targets. The approval workflow records the reviewer, timestamp, and any caveats.

Committed value is locked at the moment of approval. Subsequent forecast revisions do not automatically update committed targets unless the business case is explicitly regenerated and re-approved.

### Commitment to outcome

Approved business cases spawn [projects](projects.md). Projects carry milestones, resource assignments, and [benefits tracking](benefits-tracking.md) baselines. As projects execute, [actuals](actuals.md) are ingested from CRM, ERP, or manual entry sources.

### Outcome to realization

[Outcomes](outcomes.md) are validated results achieved by projects. The realization engine matches outcomes to the original forecast drivers and computes:

- **Realization rate** = realized value / forecasted value
- **Variance** = forecasted value - realized value
- **Trend** = realization rate trajectory over quarters

### Realization stages

Value realization moves through four maturity stages:

| Stage | Trigger | Typical duration |
|-------|---------|-----------------|
| Projected | Forecast published | Pre-sales |
| Committed | Business case approved | Sales cycle |
| In-flight | Project active with actuals | Implementation |
| Realized | Outcomes validated and attributed | Post-implementation |

## Value realization dashboard

The dashboard displays:

- **Realization summary** — total forecasted, committed, and realized value for the selected period
- **Trend line** — realization rate over quarters
- **Variance heatmap** — projects and initiatives color-coded by variance severity
- **Drill-down** — click any initiative to see project-level realization rates

### Realization reporting cadence

| Report type | Frequency | Audience |
|-------------|-----------|----------|
| Project status | Weekly | Project owner |
| Initiative review | Monthly | Initiative sponsor |
| Portfolio review | Quarterly | Executive team |
| Board summary | Annually | Board of directors |

## Example

An account forecasts $2.4M in annual savings from a procurement automation project:

| Quarter | Forecast | Actual | Realization Rate | Variance |
|---------|----------|--------|-----------------|----------|
| Q1 | $600K | $420K | 70% | -$180K |
| Q2 | $600K | $590K | 98% | -$10K |
| Q3 | $600K | $610K | 102% | +$10K |
| Q4 | $600K | $650K | 108% | +$50K |

The project ends with a 95% full-year realization rate and a positive $130K cumulative variance in Q3-Q4.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure realization rules | Organization |
| User | View realization dashboards | Assigned accounts |
| Executive | View rollup across initiatives | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `account:read` to view realization data.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Realization calculations refresh every 15 minutes. Manual refresh is available once per minute.

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 50 actuals rows can be bulk-imported per request.

<span class="vp-badge vp-badge--limit">Limit</span> Variance alerts trigger only when variance exceeds 10% of forecast or $10K, whichever is larger.

## Troubleshooting

??? question "Issue: Realization rate shows zero despite existing actuals"
    **Cause:** The actuals are not mapped to the correct forecast driver or time period.
    **Resolution:** Open the account's **Value Model** tab, click **Map Actuals**, and link each actual row to the matching driver and quarter.

??? question "Issue: Forecasted value does not match the business case"
    **Cause:** The business case was approved after a forecast revision, or the scenario selected in the business case differs from the default forecast scenario.
    **Resolution:** Check the business case's linked scenario label. If needed, regenerate the business case from the current forecast.

??? question "Issue: Realization dashboard is missing an initiative"
    **Cause:** The initiative status is `archived` or the user lacks tenant-scoped access.
    **Resolution:** Confirm the initiative status in **Initiatives** and verify role permissions.

??? question "Issue: Realization rate exceeds 100% but variance is negative"
    **Cause:** The forecast was revised downward after the business case was approved, creating a denominator smaller than the committed target.
    **Resolution:** Check the forecast revision history. If the revision was intentional, create a business case amendment to realign committed value with the new forecast.

## Related pages

- [Forecasts](forecasts.md)
- [Actuals](actuals.md)
- [Benefits Tracking](benefits-tracking.md)
- [Outcomes](outcomes.md)
- [Business Cases](business-cases.md)

## Escalation path

For persistent data mismatches, contact your ValuePact admin. If the issue involves cross-tenant data, escalate to Platform Support with severity `medium`.