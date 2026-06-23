---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Interpreting Analytics

Learn how to read ValuePact charts correctly, avoid common misinterpretations, and communicate confidence levels to stakeholders. This guide is essential for anyone who presents analytics to decision-makers.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Familiarity with at least one analytics view (ROI, Forecast, or Realization).
- Reviewed [Core Concepts: Value Metrics](../core-concepts/value-metrics.md).
- Reviewed [Core Concepts: Outcomes](../core-concepts/outcomes.md).

## How to read charts

### Confidence scores

Confidence scores are derived from claim validation, formula evaluation, and benchmark coverage. Use this table when communicating to stakeholders:

| Score | Meaning | Action | Safe for external sharing? |
|-------|---------|--------|---------------------------|
| 85% or higher | High confidence | Safe to share with external stakeholders | Yes |
| 60–84% | Medium confidence | Add more evidence or validate assumptions before sharing | With caveats |
| 30–59% | Low confidence | Requires significant additional validation | No |
| Below 30% | No confidence | Do not use in a business case without rework | No |

### Percentiles in benchmarking

- **p10** — 10% of peers are below this value. You are outperforming 90%.
- **p50 (median)** — Half of peers are above, half below. This is the middle of the market.
- **p90** — 90% of peers are below this value. Only 10% are higher.

Your percentile tells you where you stand, not whether the value is good. A 95th percentile cost reduction is excellent; a 95th percentile time-to-value may indicate a problem.

### Variance decomposition

Variance is additive across drivers. A driver with a large positive variance can mask another with a large negative variance. Always inspect the per-driver table before drawing conclusions about overall performance.

| Variance type | Visual indicator | Interpretation |
|---------------|------------------|----------------|
| Positive | Green bar | Actual exceeded forecast (favorable for revenue, unfavorable for cost) |
| Negative | Red bar | Actual fell short of forecast (unfavorable for revenue, favorable for cost) |
| Near zero | Gray bar | On target |

## Common misinterpretations

- **Correlation is not causation.** A driver that moves with outcomes may not be the cause. Check evidence provenance in the **Governance → Evidence** workspace.
- **Aggregate ROI hides risk.** A portfolio ROI of 2x may include one initiative at 10x and nine at zero. Use the portfolio dashboard to inspect distribution.
- **Forecast accuracy degrades over time.** A model that was 95% accurate last quarter may be 70% accurate next quarter. Re-validate assumptions regularly.
- **Benchmarks are directional, not targets.** Peer medians describe what others achieve, not what you should achieve. Your strategy may justify outperforming or underperforming the median.
- **Anomalies are not always errors.** A flagged point may represent a genuine one-time event (for example, a major contract win). Investigate before discarding.

## Communicating to different audiences

=== "Board / Investors"
    Focus on realization rate, portfolio ROI, and confidence scores. Use the Executive Dashboard export. Avoid driver-level detail unless asked.

=== "CFO"
    Present the CFO View with cost-benefit tables, payback periods, and risk remediation items. Include scenario bounds.

=== "Technical Leads"
    Share the Technical View with evidence provenance, implementation details, and remediation items. Include claim traceability.

=== "Account Teams"
    Use the Team Dashboard and Individual Dashboard to show task progress, milestones, and blockers.

!!! tip "Tip: Always pair metrics with narratives"
    A chart shows what happened. The **Narrative** tab in Value Studio explains why it happened. Use both in stakeholder presentations. A slide with only numbers invites misinterpretation.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Export | Assigned initiatives |
| Admin | Configure confidence thresholds / Set narrative templates | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Confidence thresholds are editable only by admins in **Workspace Settings**.
<span class="vp-badge vp-badge--limit">Limit</span> Chart exports are limited to **50 per day** per user.
<span class="vp-badge vp-badge--limit">Limit</span> Narrative templates are limited to **10 per tenant**.

## Troubleshooting

??? question "Issue: Confidence score differs between dashboards"
    **Cause:** Different dashboards use different confidence inputs (claim validation vs. formula evaluation vs. benchmark coverage).
    **Resolution:** Open the **Governance → Evidence** tab to inspect the underlying truth objects and their maturity levels. The most restrictive score is the safest to report.

??? question "Issue: Stakeholders question the forecast"
    **Cause:** The forecast was presented without scenario bounds or sensitivity analysis.
    **Resolution:** Include pessimistic, base, and optimistic cases from the **ROI Calculator** in your presentation. Show the sensitivity of NPV to key variables.

??? question "Issue: Benchmark percentile confuses stakeholders"
    **Cause:** Stakeholders interpret percentile as a grade rather than a rank.
    **Resolution:** Explain that percentile shows relative position, not absolute quality. Pair with the peer range and sample size for context.

??? question "Issue: Variance chart is hard to read in presentations"
    **Cause:** Too many drivers are displayed, or colors are not accessible.
    **Resolution:** Filter to the top 5 drivers by absolute variance. Use the exported PNG instead of a screenshot for better resolution.

## Related pages

- [ROI Analytics](roi-analytics.md)
- [Benchmarking](benchmarking.md)
- [Value Realization Analytics](value-realization-analytics.md)
- [Core Concepts: Value Metrics](../core-concepts/value-metrics.md)
- [Core Concepts: Outcomes](../core-concepts/outcomes.md)
- [Executive Dashboard](../dashboards-reporting/executive-dashboard.md)

## Escalation path

For training requests or help with stakeholder presentations, contact your customer success manager or open a support ticket with severity **P4**.
