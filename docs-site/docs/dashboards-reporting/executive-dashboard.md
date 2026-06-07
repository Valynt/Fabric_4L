---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Executive Dashboard

The Executive Dashboard provides a portfolio rollup of KPIs, strategic health, and drill-down paths for C-suite and VP/SVP decision-makers. It answers the question: "Is our portfolio delivering the value we promised?"

## Who this is for

<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- Multiple active initiatives in the portfolio.
- Executive or admin role permissions.
- Reviewed [Dashboards & Reporting Overview](index.md).

## Step-by-step instructions

### 1. Open the Executive Dashboard

1. From the home page, click **Command Center**.
2. Alternatively, navigate to the executive view from the left rail under **Dashboards**.

### 2. Review portfolio KPIs

The top row shows four cards:

| KPI | Description | Drill-down action |
|-----|-------------|-------------------|
| **Total Portfolio Value** | Sum of projected value across all approved initiatives | Click to open Portfolio Dashboard filtered by approved status |
| **Average ROI** | Blended ROI ratio across the portfolio | Click to see ROI distribution by initiative |
| **Realization Rate** | Percentage of forecasted value already realized | Click to open Value Realization Analytics |
| **At-Risk Initiatives** | Count of initiatives flagged by health monitors | Click to see risk flags and remediation items |

### 3. Drill into rollups

1. Click any KPI card to open a filtered view of the underlying initiatives.
2. Use the date range selector to compare quarter-over-quarter trends.
3. Toggle between **Portfolio** and **Industry** views if benchmarking data is available.

### 4. Inspect strategic alignment

1. Scroll to the **Strategic Recommendations** section.
2. Review top-performing value drivers and their evidence coverage.
3. Click a driver to open the account detail in the Intelligence workspace.

### 5. Check decision confidence

1. The **Decision Confidence** gauge reflects the ratio of validated claims to total claims across the portfolio.
2. Confidence is calculated from Layer 5 TruthObjects: validated claims increase the score; unverified claims decrease it.
3. If confidence is below 60%, open the **Governance → Evidence** workspace to inspect gaps.

### 6. Export a summary

1. Click **Export** to generate a PDF summary.
2. Choose **Board Summary** (high-level) or **Detailed Portfolio** (initiative list).
3. The export is emailed to you and appears in your downloads.

!!! tip "Tip: Use the Command Center for quick checks"
    The Command Center on the home page offers a lightweight version of the Executive Dashboard with recent activity, quick actions, and a prospect prompt builder.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Executive | View / Export | Portfolio |
| Admin | View / Export / Configure | Tenant-wide |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Portfolio rollups include up to **500 initiatives**.
<span class="vp-badge vp-badge--limit">Limit</span> Export generation may take up to **60 seconds** for large portfolios.
<span class="vp-badge vp-badge--limit">Limit</span> Historical trend data is retained for **24 months**.

## Troubleshooting

??? question "Issue: Realization rate is lower than expected"
    **Cause:** Baselines were set late, or actuals have not been entered for recent milestones.
    **Resolution:** Open the **Realization Plan** tab for at-risk initiatives and enter missing actuals. Check the **Value Realization Analytics** page for variance decomposition.

??? question "Issue: Confidence score is below 60%"
    **Cause:** Many initiatives have unverified claims or missing evidence references.
    **Resolution:** Ask initiative owners to validate claims in the **Governance → Evidence** workspace. Review the **Claim Traceability** section on each business case.

??? question "Issue: At-Risk Initiatives count seems high"
    **Cause:** Health monitors flag initiatives with any single red metric, even if the overall case is strong.
    **Resolution:** Click the count to open the Portfolio Dashboard and review the specific flags. Some may be false positives due to missing benchmark data.

??? question "Issue: Export fails or times out"
    **Cause:** The portfolio is too large, or the export service is under load.
    **Resolution:** Try a smaller date range, or export the Portfolio Dashboard instead of the Executive summary.

## Related pages

- [Portfolio Dashboard](portfolio-dashboard.md)
- [Value Realization Analytics](../analytics/value-realization-analytics.md)
- [Interpreting Analytics](../analytics/interpreting-analytics.md)
- [Dashboards & Reporting Overview](index.md)

## Escalation path

If portfolio totals disagree with source systems, open a support ticket with severity **P2** and include the tenant ID and the data source name.
