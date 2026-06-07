---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Analytics

ValuePact analytics turn raw value data into actionable intelligence. Use them to validate assumptions, compare against peers, forecast outcomes, and communicate confidence to stakeholders. Analytics are available across the Value Studio, Dashboards, and Layer 6 Benchmark Service.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Analytics capabilities

| Capability | What it does | Where to find it | Key output |
|------------|--------------|------------------|------------|
| [ROI Analytics](roi-analytics.md) | ROI dashboards, sensitivity analysis, what-if scenarios | Value Studio → Calculator | Simple ROI, NPV, payback, confidence |
| [Forecast Analytics](forecast-analytics.md) | Forecast accuracy, scenario comparison, trend extrapolation | Analytics → Forecasts | MAPE, bias, tracking signal |
| [Value Realization Analytics](value-realization-analytics.md) | Realization rate, variance decomposition, attribution | Analytics → Realization | Realization rate, variance by driver |
| [Trend Analysis](trend-analysis.md) | Time-series views, anomaly detection, seasonal adjustment | Analytics → Trends | Trend lines, anomaly flags, adjusted series |
| [Benchmarking](benchmarking.md) | Peer comparison, percentile rankings, industry benchmarks | Layer 6 Benchmark Service | Percentile, peer median, assessment |
| [Interpreting Analytics](interpreting-analytics.md) | How to read charts, common misinterpretations, confidence levels | Analytics → Help | Confidence thresholds, best practices |

## How analytics fit the workflow

1. **During modeling** — Use **ROI Analytics** and **Benchmarking** to ground assumptions in peer data.
2. **During validation** — Use **Forecast Analytics** to compare scenarios and test robustness.
3. **During execution** — Use **Value Realization Analytics** and **Trend Analysis** to track actuals against plan.
4. **During reporting** — Use **Interpreting Analytics** to explain confidence and avoid miscommunication.

## Analytics data flow

```
Value Model (formulas + variables)
  ├── ROI Calculator → ROI Analytics
  ├── Forecasts → Forecast Analytics
  ├── Actuals → Value Realization Analytics
  └── Time Series → Trend Analysis

Layer 6 Benchmark Service
  ├── Datasets → Benchmarking
  └── Peer Data → ROI Calculator (context)
```

## Role-based entry points

=== "End User"
    Start with [ROI Analytics](roi-analytics.md) to validate your value model. Then move to [Benchmarking](benchmarking.md) to see how your assumptions compare to peers.

=== "Admin"
    Review [Forecast Analytics](forecast-analytics.md) and [Trend Analysis](trend-analysis.md) to configure tolerances, seasonal models, and anomaly sensitivity for the tenant.

=== "Executive"
    Focus on [Value Realization Analytics](value-realization-analytics.md) and [Interpreting Analytics](interpreting-analytics.md) to understand portfolio performance and communicate results to the board.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Create scenarios | Assigned initiatives |
| Admin | Configure benchmarks / Edit tolerances / Manage datasets | Tenant-wide |
| Executive | View all analytics / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Analytics queries time out after **60 seconds**.
<span class="vp-badge vp-badge--limit">Limit</span> Benchmark comparisons are capped at **1,000 peer records** per query.
<span class="vp-badge vp-badge--limit">Limit</span> Scenario storage is limited to **10 per account**.

## Troubleshooting

??? question "Issue: Analytics page shows no data"
    **Cause:** The initiative has no approved value model, or actuals have not been entered.
    **Resolution:** Complete the value model in **Value Studio** and enter baseline and actual values. Verify the account has at least one approved business case.

??? question "Issue: Benchmarking returns no datasets"
    **Cause:** Layer 6 Benchmark Service is unavailable, or no datasets match your industry.
    **Resolution:** Check **Governance → Health** for Layer 6 status. Ask an admin to upload a custom dataset if needed.

??? question "Issue: Forecast accuracy metrics are blank"
    **Cause:** Fewer than 3 data points exist for the selected driver.
    **Resolution:** Enter at least 3 periods of actuals in the **Realization Plan** tab before running forecast analytics.

## Related pages

- [ROI Analytics](roi-analytics.md)
- [Forecast Analytics](forecast-analytics.md)
- [Value Realization Analytics](value-realization-analytics.md)
- [Trend Analysis](trend-analysis.md)
- [Benchmarking](benchmarking.md)
- [Interpreting Analytics](interpreting-analytics.md)
- [Dashboards & Reporting Overview](../dashboards-reporting/index.md)

## Escalation path

For analytics query timeouts or benchmark sync failures, open a support ticket with severity **P3** and the account or dataset ID.
