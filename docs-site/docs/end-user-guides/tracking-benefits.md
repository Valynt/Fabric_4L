---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Tracking Benefits

Track forecasted value through to realized outcomes by setting baselines, entering actuals, and monitoring variance in the **Value Studio** and **Governance** workspaces. This guide covers the full realization lifecycle from conversion to quarterly review.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An approved business case converted to value realization.
- Understanding of [Core Concepts: Benefits Tracking](../core-concepts/benefits-tracking.md).
- Understanding of [Core Concepts: Forecasts](../core-concepts/forecasts.md) and [Actuals](../core-concepts/actuals.md).

## Step-by-step instructions

### 1. Convert the business case

1. Open the approved business case detail page.
2. Scroll to **Post-Approval Actions**.
3. Click **Convert to Value Realization**.
4. The system creates a realization plan linked to the original case.

### 2. Set baselines

1. In **Value Studio**, select the **Realization Plan** tab.
2. For each value driver, enter the baseline value before implementation begins.
3. Baselines represent the starting point: cost, time, or revenue before your solution is applied.
4. Click **Lock Baselines** when finished. Locked baselines require admin approval to change.

### 3. Define milestones

1. In the **Realization Plan** tab, click **Add Milestone**.
2. Enter a name, target date, and expected outcome for each milestone.
3. Link milestones to specific value drivers so variance can be traced later.
4. Set reminder notifications for 3 days before each due date.

### 4. Enter actuals

1. As work progresses, return to the **Realization Plan** tab.
2. For each reporting period, input actual measurements against each driver.
3. Actuals can be entered once per driver per period.
4. Add a note explaining any significant deviation from forecast.

### 5. Monitor variance

1. The system calculates variance as `actual - forecast`.
2. Drivers that deviate beyond tolerance are flagged automatically.
3. Open the variance chart to see positive and negative contributors.

### 6. Review realization analytics

1. Open **Analytics → Value Realization Analytics**.
2. Review the realization rate: `realized value / forecasted value`.
3. Inspect variance decomposition to see which drivers contribute most to the gap.
4. Review attribution to link outcomes back to specific business cases.

### 7. Adjust forecasts

1. If actuals diverge significantly, return to the **Value Model** tab.
2. Update formula variables or assumptions.
3. Recalculate in the **ROI Calculator**.
4. Save the updated scenario and document the reason for the change.

### 8. Audit changes

1. Use **Governance → Traces** to review who changed baselines or actuals and when.
2. Use **Governance → Audit Log** for a complete history of realization plan edits.

!!! tip "Tip: Use variance decomposition to prioritize"
    Variance decomposition shows which drivers contribute most to the overall gap. Focus remediation on the top contributors first rather than trying to fix every small deviation.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Enter Actuals / View | Assigned accounts |
| Admin | Edit Baselines / Tolerances / Lock / Unlock | Tenant-wide |
| Executive | View Analytics / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Actuals can only be entered **once per driver per reporting period**.
<span class="vp-badge vp-badge--limit">Limit</span> Baseline changes after the first actual is logged require admin approval.
<span class="vp-badge vp-badge--limit">Limit</span> Milestone reminders are sent **3 days** before the due date.
<span class="vp-badge vp-badge--limit">Limit</span> Realization plans support up to **50 milestones** per initiative.

## Troubleshooting

??? question "Issue: Variance shows negative for all drivers"
    **Cause:** Baselines were set after implementation began, or forecasts were overly optimistic.
    **Resolution:** Revisit the **Value Model** tab to validate formula assumptions and update benchmarks. If baselines were incorrect, request an admin to unlock and reset them.

??? question "Issue: Realization rate is stuck at zero"
    **Cause:** No actuals have been entered, or the business case was not converted to realization tracking.
    **Resolution:** Click **Convert to Value Realization** from the business case detail page, then enter actuals for at least one period.

??? question "Issue: Cannot edit a baseline"
    **Cause:** Baselines are locked after the first actual is entered.
    **Resolution:** Ask an admin to unlock the baseline in the **Realization Plan** tab. Provide a justification for the change.

??? question "Issue: Milestone reminder never arrived"
    **Cause:** Notification preferences are disabled, or the milestone was created without a due date.
    **Resolution:** Check **Settings → Notifications** and ensure milestone reminders are enabled. Edit the milestone to confirm a due date is set.

??? question "Issue: Actuals entry rejected as duplicate"
    **Cause:** An actual was already entered for this driver and period.
    **Resolution:** Edit the existing actual instead of creating a new one. If the original value was wrong, document the correction in the notes field.

## Related pages

- [Building a Business Case](building-a-business-case.md)
- [Value Realization Analytics](../analytics/value-realization-analytics.md)
- [Core Concepts: Benefits Tracking](../core-concepts/benefits-tracking.md)
- [Core Concepts: Forecasts](../core-concepts/forecasts.md)
- [Core Concepts: Actuals](../core-concepts/actuals.md)

## Escalation path

If realization data does not match source-of-truth systems, open a support ticket with severity **P3** and include the account ID and reporting period.
