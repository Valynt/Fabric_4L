---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Portfolio Dashboard

Monitor initiative health, risk flags, and resource allocation across your portfolio from a single view. The Portfolio Dashboard is the control center for directors and portfolio managers who need to balance value delivery across multiple accounts.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Active initiatives with assigned owners and stages.
- Reviewed [Core Concepts: Initiatives](../core-concepts/initiatives.md).
- Reviewed [Dashboards & Reporting Overview](index.md).

## Step-by-step instructions

### 1. Open the Portfolio Dashboard

1. Navigate from the home page or select **Portfolio** from the dashboard switcher.
2. The default view shows all initiatives you have permission to see.

### 2. Filter initiatives

Use the filter bar to narrow the list:

| Filter | Options |
|--------|---------|
| Status | Draft, Pending Review, Validated, Export Ready, Export Blocked |
| Owner | User names from the tenant |
| Industry | Industries configured in your value packs |
| Health Score | Green, Yellow, Red |

### 3. Review health cards

Each initiative card displays:

- **Status** — current workflow state.
- **Health score** — composite score based on:
  - Claim validation coverage
  - Evidence reference count
  - Forecast variance
  - Milestone on-time rate
- **Risk flags** — automatically generated when:
  - A milestone slips by more than 7 days
  - Confidence drops below 50%
  - A value driver has no formula

### 4. Inspect resource allocation

1. Switch to the **Allocation** chart view.
2. See how effort (estimated hours or cost) is distributed across initiatives.
3. Identify over-allocated owners or under-resourced initiatives.

### 5. Click to drill

1. Select any initiative card to open the account overview.
2. From the overview, continue into the **Intelligence** or **Value Studio** workspace.
3. Review the business case, claims, and remediation items.

### 6. Escalate blockers

1. Click the **Blockers** column on any initiative card.
2. Choose an action:
   - **Create Task** — assign to the initiative owner.
   - **Notify Stakeholder** — send an in-app mention.
   - **Escalate to Admin** — flag for admin review.

!!! warning "Warning: Export Blocked initiatives need attention"
    Initiatives with **Export Blocked** status have failed validation gates. Drill down to inspect remediation items before including them in portfolio reports.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View | Assigned initiatives |
| Admin | View / Edit allocation / Escalate / Configure health rules | Tenant-wide |
| Executive | View all / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Health scores are recalculated every **15 minutes**.
<span class="vp-badge vp-badge--limit">Limit</span> Risk flags auto-clear when the underlying metric returns to tolerance for **2 consecutive calculation cycles**.
<span class="vp-badge vp-badge--limit">Limit</span> Portfolio views are paginated at **50 initiatives per page**.

## Troubleshooting

??? question "Issue: Initiative health score is red but all metrics look fine"
    **Cause:** A downstream dependency (for example, missing benchmark data) may be affecting the score.
    **Resolution:** Open the initiative detail and check the **Governance → Health** tab for dependency status. Verify Layer 6 benchmark connectivity.

??? question "Issue: Resource allocation chart is empty"
    **Cause:** Initiatives do not have assigned owners or effort estimates.
    **Resolution:** Edit each initiative and assign an owner and expected effort in the **Action Plan** tab. Effort estimates flow from the value model variables.

??? question "Issue: Risk flags appear and disappear rapidly"
    **Cause:** A metric is hovering near the threshold boundary.
    **Resolution:** Adjust the tolerance in **Workspace Settings → Governance → Policies** or wait for the next health score recalculation.

??? question "Issue: Cannot export portfolio view"
    **Cause:** The export includes initiatives with restricted sharing settings.
    **Resolution:** Filter to initiatives you own, or ask an admin to run the export.

## Related pages

- [Executive Dashboard](executive-dashboard.md)
- [Team Dashboard](team-dashboard.md)
- [Forecast Analytics](../analytics/forecast-analytics.md)
- [Value Realization Analytics](../analytics/value-realization-analytics.md)
- [Dashboards & Reporting Overview](index.md)

## Escalation path

For persistent health score discrepancies, contact support with severity **P3** and the initiative ID.
