---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Trend Analysis

Visualize time-series data, detect anomalies, and apply seasonal adjustments to understand how value drivers behave over time. Trend Analysis helps you distinguish between signal and noise in your value data.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Multiple periods of actuals or forecast data.
- Reviewed [Core Concepts: Forecasts](../core-concepts/forecasts.md).
- Reviewed [Core Concepts: Value Metrics](../core-concepts/value-metrics.md).

## Step-by-step instructions

### 1. Open Trend Analysis

1. Navigate to **Analytics → Trends**.
2. Select a tenant, portfolio, or specific account.

### 2. Select a driver

1. Choose a value driver or aggregate metric from the dropdown.
2. Available options include all drivers with at least 2 periods of data.

### 3. Choose a view

| View | What it shows | Best used when |
|------|---------------|----------------|
| **Time-Series** | Raw actuals and forecasts on a shared timeline | You need to spot directional shifts |
| **Anomaly Detection** | Points that deviate beyond expected bounds | You suspect data entry errors or one-time events |
| **Seasonal Adjustment** | Underlying trend after removing repeating patterns | Your data has quarterly or annual cycles |

### 4. Set the window

1. Use the date range controls to focus on specific quarters or years.
2. Preset ranges: Last 3 Months, Last 6 Months, Last Year, All Time.
3. Custom ranges are supported for up to 24 months.

### 5. Interpret anomalies

1. Hover over flagged points to see:
   - Expected range (mean ± 2 standard deviations)
   - Actual value
   - Deviation percentage
2. Click a flagged point to open the **Realization Plan** for that period.

### 6. Export the chart

1. Click **Download PNG** for presentations.
2. Click **Download CSV** for further analysis in Excel or Python.

=== "Time-Series"
    Displays raw actuals and forecasts on a shared timeline. Useful for spotting directional shifts. Forecasts are shown as dashed lines; actuals as solid lines.

=== "Anomaly Detection"
    Flags points outside ±2 standard deviations. Useful for catching data entry errors or one-time events. Anomalies are red diamonds; normal points are blue circles.

=== "Seasonal Adjustment"
    Applies a decomposition model to isolate trend, seasonality, and residual. Useful for recurring benefits. The adjusted series removes seasonal peaks and troughs.

!!! tip "Tip: Combine with Benchmarking"
    Overlay peer median data from the **Benchmarking** module to see if your trend aligns with industry patterns. If your cost reduction trend is flat while peers are declining, you may have a hidden opportunity.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Export | Assigned initiatives |
| Admin | Configure detection sensitivity / Seasonal models / Set cycle lengths | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Anomaly detection requires at least **6 data points**.
<span class="vp-badge vp-badge--limit">Limit</span> Seasonal adjustment requires at least **2 full cycles** of data.
<span class="vp-badge vp-badge--limit">Limit</span> Trend data is retained for **24 months**.

## Troubleshooting

??? question "Issue: Anomaly detection flags every point"
    **Cause:** The sensitivity threshold is too low, or the data has high natural variance.
    **Resolution:** Increase the sensitivity threshold in **Analytics → Trends → Settings**, or smooth the data with a moving average. Check if a driver was redefined mid-series.

??? question "Issue: Seasonal adjustment looks flat"
    **Cause:** The data does not contain a strong seasonal pattern, or the cycle length is misconfigured.
    **Resolution:** Verify the cycle length (for example, 4 for quarterly, 12 for monthly) and ensure you have at least 2 full cycles. Try the Time-Series view first to visually confirm seasonality.

??? question "Issue: Trend data stops at a certain date"
    **Cause:** Actuals were not entered for recent periods, or the account was archived.
    **Resolution:** Enter missing actuals in the **Realization Plan** tab, or check the account status in the **Accounts** list.

??? question "Issue: Export CSV has missing columns"
    **Cause:** Some periods have no forecast or actual value for the selected driver.
    **Resolution:** This is expected. Fill missing cells with your own interpolation if needed.

## Related pages

- [Forecast Analytics](forecast-analytics.md)
- [Benchmarking](benchmarking.md)
- [Value Realization Analytics](value-realization-analytics.md)
- [Interpreting Analytics](interpreting-analytics.md)
- [Core Concepts: Forecasts](../core-concepts/forecasts.md)

## Escalation path

For calculation errors or missing trend data, open a support ticket with severity **P4**.
