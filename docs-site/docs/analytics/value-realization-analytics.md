---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Value Realization Analytics

Measure how much forecasted value has been realized, decompose variance by driver, and attribute outcomes to specific initiatives. Value Realization Analytics answer the critical question: "Did we achieve the value we promised?"

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An approved business case converted to realization tracking.
- Baselines and at least one period of actuals entered.
- Reviewed [Core Concepts: Value Realization](../core-concepts/value-realization.md).

## Step-by-step instructions

### 1. Open Value Realization Analytics

1. Navigate to **Analytics → Realization**.
2. Select the portfolio, account, or initiative to analyze.

### 2. Review realization rate

The top KPI panel shows:

| KPI | Formula | Interpretation |
|-----|---------|----------------|
| **Realization Rate** | `realized value / forecasted value * 100` | 100% means on target; above 100% means over-performing |
| **Variance** | `actual - forecast` | Positive is favorable; negative is unfavorable |
| **Attribution** | Driver-level contribution to total realized value | Shows which initiatives and drivers delivered |

### 3. Decompose variance

1. Open the **Variance Decomposition** chart.
2. Each bar represents a value driver.
3. Green bars show positive variance (actual exceeded forecast).
4. Red bars show negative variance (actual fell short).
5. Hover over a bar to see the absolute and percentage contribution.

### 4. Inspect attribution

1. Open the **Attribution Table**.
2. See which business cases and value drivers contributed most to the realized total.
3. Sort by realized value, variance, or confidence.
4. Click any row to open the source business case.

### 5. Drill to evidence

1. Click any driver in the variance chart.
2. The system opens the **Evidence** tab for that driver.
3. Verify the data source and audit trail for the actual value.

### 6. Export for reporting

1. Click **Export Summary** to download a PDF.
2. The export includes:
   - Realization rate trend
   - Variance decomposition chart
   - Attribution table
   - Evidence reference list

!!! warning "Warning: Negative variance is not always bad"
    Under-forecasting can produce positive surprises. Always inspect the driver-level decomposition before labeling an initiative as failing. A negative variance on a cost driver may actually be favorable if costs were lower than expected.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Enter actuals | Assigned initiatives |
| Admin | Edit baselines / Reallocate attribution / Configure periods | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Attribution models are recalculated nightly.
<span class="vp-badge vp-badge--limit">Limit</span> Variance decomposition requires at least **2 periods** of actuals.
<span class="vp-badge vp-badge--limit">Limit</span> Realization summaries are retained for **36 months**.

## Troubleshooting

??? question "Issue: Realization rate exceeds 100%"
    **Cause:** Actuals were entered incorrectly, or the forecast was conservative.
    **Resolution:** Verify actuals in the **Realization Plan** tab. If the forecast was intentionally conservative, document the rationale in the value model notes.

??? question "Issue: Attribution table shows gaps"
    **Cause:** An initiative was deleted or its business case was not linked to realization tracking.
    **Resolution:** Re-link the business case using **Convert to Value Realization** on the case detail page. Wait for the next nightly recalculation.

??? question "Issue: Variance decomposition sums to more than total variance"
    **Cause:** Rounding or interaction effects between drivers.
    **Resolution:** This is expected in multi-driver models. Use the attribution table for exact numbers.

??? question "Issue: Realization rate drops after a forecast update"
    **Cause:** The forecast was revised upward, making the same actuals represent a lower percentage.
    **Resolution:** Review the forecast change history in **Governance → Traces** and communicate the revision to stakeholders.

## Related pages

- [Tracking Benefits](../end-user-guides/tracking-benefits.md)
- [Trend Analysis](trend-analysis.md)
- [Forecast Analytics](forecast-analytics.md)
- [Core Concepts: Value Realization](../core-concepts/value-realization.md)
- [Core Concepts: Actuals](../core-concepts/actuals.md)

## Escalation path

For attribution calculation errors or missing realization links, open a support ticket with severity **P3**.
