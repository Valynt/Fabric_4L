---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Forecast Analytics

Measure forecast accuracy, compare scenarios, and extrapolate trends to improve the reliability of your value predictions. Forecast Analytics help you answer: "How good are our predictions, and what happens if conditions change?"

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Approved business case with baseline forecasts.
- At least one period of actuals entered in the **Realization Plan**.
- Reviewed [Core Concepts: Forecasts](../core-concepts/forecasts.md).

## Step-by-step instructions

### 1. Open Forecast Analytics

1. Navigate to **Analytics → Forecasts**.
2. Select an account and initiative from the dropdown.

### 2. Review accuracy metrics

The dashboard shows three primary metrics:

| Metric | Description | Healthy range |
|--------|-------------|---------------|
| **MAPE** | Mean Absolute Percentage Error — average forecast error | Below 20% |
| **Bias** | Tendency to over-forecast or under-forecast | Near 0% |
| **Tracking Signal** | Cumulative error trend | Between -4 and +4 |

### 3. Compare scenarios

1. Select two saved scenarios from the dropdown.
2. The chart overlays both forecast curves on the same timeline.
3. The table below shows period-by-period differences.
4. Use this to answer questions like: "What is the revenue gap between our base case and pessimistic case in Q4?"

### 4. Extrapolate trends

1. Choose a trend method:

| Method | Best for | Requirements |
|--------|----------|--------------|
| **Linear** | Stable, predictable growth | 3+ data points |
| **Moving Average** | Noisy data with no strong seasonality | 3+ data points |
| **Seasonal Adjustment** | Recurring quarterly or annual cycles | 2+ full cycles |

2. Set the extrapolation window: 1 to 12 future periods.
3. Review the projected curve and confidence bands.

### 5. Adjust the forecast

1. If actuals diverge, return to the **Value Model** tab.
2. Update formula variables or assumptions.
3. Recalculate in the **ROI Calculator**.
4. Save the updated scenario and document the reason.

### 6. Export the analysis

1. Click **Export Chart** to download a PNG.
2. Click **Export Data** to download a CSV of forecasts, actuals, and errors.
3. Use these in stakeholder presentations or quarterly reviews.

!!! tip "Tip: Use seasonal adjustment for recurring benefits"
    If your value drivers include quarterly or annual cycles, seasonal adjustment produces more accurate extrapolations. For example, retail cost savings may spike during holiday seasons.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Create scenarios | Assigned initiatives |
| Admin | Edit tolerances / Configure methods / Set default horizons | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Forecast analytics require at least **3 data points** per driver.
<span class="vp-badge vp-badge--limit">Limit</span> Extrapolation is limited to **12 future periods**.
<span class="vp-badge vp-badge--limit">Limit</span> Scenario comparisons are limited to **2 scenarios** at a time.

## Troubleshooting

??? question "Issue: MAPE is extremely high"
    **Cause:** Baselines were set incorrectly, or a one-time event distorted actuals.
    **Resolution:** Review the **Realization Plan** for data entry errors, or exclude outlier periods from the analysis. Check for duplicate actuals.

??? question "Issue: Scenario comparison shows identical curves"
    **Cause:** The scenarios use the same variable set, or one scenario was not saved correctly.
    **Resolution:** Re-create the scenarios with distinct variable values in the **ROI Calculator**. Ensure you click **Save Scenario** after each change.

??? question "Issue: Seasonal adjustment is grayed out"
    **Cause:** Insufficient data cycles exist for the selected driver.
    **Resolution:** Enter actuals for at least 2 full cycles (for example, 8 quarters for quarterly seasonality) before using seasonal adjustment.

??? question "Issue: Tracking signal is outside ±4"
    **Cause:** The forecast model is systematically biased and needs recalibration.
    **Resolution:** Update the forecast assumptions in the **Value Model** tab and review the bias direction. Positive bias means you are under-forecasting; negative bias means over-forecasting.

## Related pages

- [ROI Analytics](roi-analytics.md)
- [Trend Analysis](trend-analysis.md)
- [Value Realization Analytics](value-realization-analytics.md)
- [Core Concepts: Forecasts](../core-concepts/forecasts.md)

## Escalation path

For forecast calculation errors or missing scenario data, open a support ticket with severity **P3**.
