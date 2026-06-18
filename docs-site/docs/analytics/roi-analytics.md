---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# ROI Analytics

ROI Analytics surface return-on-investment metrics, sensitivity analysis, and what-if scenarios so you can stress-test value models before committing to a business case. The analytics are powered by the Layer 4 ROI Calculator workflow, which evaluates value driver formulas using prospect data and industry benchmarks.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A populated value model with formulas and variables.
- Completed ROI calculation in the **ROI Calculator** tab.
- Reviewed [Core Concepts: ROI Calculations](../core-concepts/roi-calculations.md).

## Step-by-step instructions

### 1. Open the ROI Calculator

1. In **Value Studio**, select the **ROI Calculator** tab.
2. The calculator loads the current value driver formulas and substituted variables.

### 2. Review core metrics

The aggregated results display:

| Metric | Description | Formula context |
|--------|-------------|-----------------|
| **Total Annual Value** | Sum of evaluated value drivers | Sum of all driver results |
| **Simple ROI Percent** | Annual return divided by investment | `(total_annual_value - investment) / investment * 100` |
| **3-Year NPV** | Net present value using a 10% discount rate | `-investment + Σ(value / (1 + 0.10)^year)` |
| **Payback Period** | Months to break even | `investment / (total_annual_value / 12)` |
| **Average Confidence** | Mean confidence across all drivers | Sum of driver confidences / driver count |

### 3. Run sensitivity analysis

1. Adjust key variables using the sliders:
   - **annual_revenue**
   - **employee_count**
   - **implementation_cost**
   - **hourly_rate**
2. Observe how metrics change in real time.
3. Note which variables have the largest impact on NPV and payback.

### 4. Create what-if scenarios

1. Click **Save Scenario** after adjusting variables.
2. Name the scenario (for example, `Pessimistic Q3`).
3. Create additional scenarios:
   - **Base Case** — current assumptions.
   - **Optimistic Case** — best-case assumptions.
   - **Pessimistic Case** — conservative assumptions.
4. Compare scenarios side by side in the scenario table.

### 5. Compare benchmarks

If benchmarks are available, the calculator shows:

- **Peer Median** — the p50 value for your industry and segment.
- **Your Percentile** — where your metric ranks among peers.
- **Assessment** — `top_performer`, `above_average`, `average`, `below_average`, or `needs_improvement`.

### 6. Export results

1. Click **Model Impact** to send the scenario to the **Action Plan** or **Narrative** tab.
2. Alternatively, click **Export** to download a CSV of all driver results.

=== "Base Case"
    ```
    Investment:        $250,000
    Annual Value:      $450,000
    Simple ROI:        80.0%
    Payback:           6.7 months
    3-Year NPV:        $868,182
    Average Confidence: 75%
    ```

=== "Pessimistic Case"
    ```
    Investment:        $250,000
    Annual Value:      $320,000
    Simple ROI:        28.0%
    Payback:           9.4 months
    3-Year NPV:        $545,455
    Average Confidence: 60%
    ```

=== "Optimistic Case"
    ```
    Investment:        $250,000
    Annual Value:      $600,000
    Simple ROI:        140.0%
    Payback:           5.0 months
    3-Year NPV:        $1,240,000
    Average Confidence: 85%
    ```

!!! tip "Tip: Watch confidence levels"
    Drivers with low confidence highlight assumptions that need more evidence. Focus validation efforts there first. A driver with confidence below 30% should not be used in an external business case without additional proof.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Create scenarios | Assigned accounts |
| Admin | Edit default variables / Configure benchmarks / Set confidence thresholds | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> What-if scenarios are limited to **10 per account**.
<span class="vp-badge vp-badge--limit">Limit</span> Sensitivity sliders allow ±**50%** adjustment from the base value.
<span class="vp-badge vp-badge--limit">Limit</span> Formula evaluation is capped at **25 value drivers** per account.

## Troubleshooting

??? question "Issue: ROI shows infinity or negative payback"
    **Cause:** Total annual value is zero or negative, or investment is missing.
    **Resolution:** Verify that value drivers have formulas and that **implementation_cost** is greater than zero. Check for division-by-zero in driver formulas.

??? question "Issue: Benchmark comparison is missing"
    **Cause:** No benchmark dataset matches the account industry and segment.
    **Resolution:** Ask an admin to upload or enable the relevant benchmark dataset in **Governance → Benchmarks**. Verify Layer 6 service health.

??? question "Issue: Scenario save fails"
    **Cause:** The account has reached the 10-scenario limit.
    **Resolution:** Delete an old scenario before saving a new one. Admins can increase the limit via configuration.

??? question "Issue: Confidence is 0% for all drivers"
    **Cause:** The graph query for variables failed, or no prospect data is available.
    **Resolution:** Check the account enrichment status and verify that **annual_revenue** and **employee_count** are populated.

## Related pages

- [Forecast Analytics](forecast-analytics.md)
- [Benchmarking](benchmarking.md)
- [Interpreting Analytics](interpreting-analytics.md)
- [Core Concepts: ROI Calculations](../core-concepts/roi-calculations.md)
- [Building a Business Case](../end-user-guides/building-a-business-case.md)

## Escalation path

For formula evaluation errors or benchmark sync issues, open a support ticket with severity **P3** and the account ID.
