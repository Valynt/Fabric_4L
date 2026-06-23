---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Benchmarking

Compare your value metrics against peer datasets using the Layer 6 Benchmark Service. See percentile rankings, peer medians, and industry baselines to ground your assumptions in real market data.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An approved value model with calculated metrics.
- Benchmark datasets available for your industry and segment.
- Reviewed [Core Concepts: Value Metrics](../core-concepts/value-metrics.md).

## Step-by-step instructions

### 1. Open Benchmarking

1. Navigate to **Analytics → Benchmarks**.
2. Alternatively, use the **Compare Benchmarks** tool in the **ROI Calculator**.

### 2. Select a dataset

1. Choose from available datasets filtered by industry and segment.
2. Default datasets include:
   - Manufacturing
   - SaaS B2B
   - Healthcare
   - Financial Services

### 3. Choose a metric

Common metrics include:

| Metric | Unit | Typical use |
|--------|------|-------------|
| `roi_percent` | Percent | Compare investment return |
| `cost_reduction` | USD or percent | Compare efficiency gains |
| `time_to_value_months` | Months | Compare implementation speed |

### 4. Run comparison

The system returns:

| Field | Description |
|-------|-------------|
| **Percentile** | Your rank among peers (5, 17, 37, 62, 82, 95) |
| **Peer Median** | The p50 value |
| **Peer Range** | p10 to p90 |
| **Sample Size** | Number of peers in the dataset |
| **Confidence** | high (1000+), medium (500+), or low (<500) |
| **Assessment** | `top_performer`, `above_average`, `average`, `below_average`, `needs_improvement` |

### 5. Validate a value

1. Use the validation tool to check if your metric falls within the expected peer range.
2. Enter your value and tolerance (default 10%).
3. The system returns:
   - `is_valid` — boolean
   - `expected_range` — min and max with tolerance
   - `deviation_percent` — how far you are from the median
   - `severity` — info, warning, or error

### 6. Upload custom data (admin only)

1. Admins can add tenant-specific datasets via **Governance → Benchmarks**.
2. Required fields per dataset:
   - dataset_id
   - name, description, industry, segment
   - metrics with statistical profiles (p10, p25, p50, p75, p90, sample_size)
3. Custom datasets can be private to the tenant or shared globally (requires super admin).

!!! tip "Tip: Use validation before finalizing forecasts"
    If your value falls far outside the peer range, review your assumptions before submitting the business case for approval. A 95th percentile cost reduction may be realistic if you have unique technology, but it needs stronger evidence.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Compare / Validate | Assigned initiatives |
| Admin | Upload / Edit datasets / Set global baselines | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Peer comparisons are capped at **1,000 records** per query.
<span class="vp-badge vp-badge--limit">Limit</span> Custom datasets must include at least **50 records** to be used in comparisons.
<span class="vp-badge vp-badge--limit">Limit</span> Benchmark data is refreshed nightly from Layer 6.

## Troubleshooting

??? question "Issue: Dataset not found for my industry"
    **Cause:** No benchmark dataset has been loaded for your industry or segment.
    **Resolution:** Ask an admin to check **Governance → Benchmarks** or upload a custom dataset. Verify the industry spelling matches the dataset exactly.

??? question "Issue: Percentile seems inconsistent with peer median"
    **Cause:** The dataset distribution is skewed, so median and percentile may diverge.
    **Resolution:** Review the full peer range (p10–p90) and sample size to assess confidence. Skewed distributions are common in cost reduction metrics.

??? question "Issue: Validation returns severity error for a value I know is correct"
    **Cause:** The tolerance is too tight, or the dataset is outdated.
    **Resolution:** Increase the tolerance percent in the validation request, or ask an admin to update the dataset with recent peer data.

??? question "Issue: Custom dataset upload fails"
    **Cause:** Missing required metric fields or invalid statistical profile.
    **Resolution:** Ensure every metric includes p10, p25, p50, p75, p90, and sample_size. Verify that p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90.

## Related pages

- [ROI Analytics](roi-analytics.md)
- [Forecast Analytics](forecast-analytics.md)
- [Interpreting Analytics](interpreting-analytics.md)
- [Core Concepts: Value Metrics](../core-concepts/value-metrics.md)

## Escalation path

For dataset upload failures or Layer 6 service unavailability, open a support ticket with severity **P2**.
