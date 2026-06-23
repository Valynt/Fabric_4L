---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Initiatives

Initiatives are strategic programs that group related projects and outcomes. They provide portfolio-level visibility, resource coordination, and executive rollup of value realization.

## Who this is for

<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- At least one active [project](projects.md) or approved [business case](business-cases.md)
- Role permission to create or join initiatives
- An organizational value framework or strategic theme defined

## Overview

Initiatives sit above projects in the value hierarchy. They represent strategic bets—such as "Digital Transformation 2026" or "Cost Optimization Program"—that cut across accounts and teams.

## Strategic grouping

Projects are grouped into initiatives by:

- **Strategic theme** — such as revenue growth, operational efficiency, or risk reduction
- **Value driver** — all projects targeting the same driver family
- **Account cluster** — multi-phase engagements with a single customer
- **Time horizon** — quarterly or annual programs

To create an initiative:

1. Navigate to **Initiatives** in the top rail.
2. Click **Create Initiative**.
3. Enter name, description, and strategic theme.
4. Set a target time horizon and total forecasted value.
5. Click **Save**.

## Portfolio view

The initiative portfolio view shows:

- **Project count** — active, at risk, on hold, and closed
- **Total forecasted value** — sum of project business case forecasts
- **Realized value YTD** — sum of achieved outcomes
- **Realization rate** — realized divided by forecasted
- **Milestone health** — percentage of milestones on time

## Rollup logic

Value rolls up from project to initiative using the following rules:

- **Forecasted value** — summed directly across child projects
- **Realized value** — summed directly across child projects
- **Variance** — computed as realized minus forecasted at the initiative level
- **Status** — derived from the worst child project status unless all are closed

The rollup refreshes every 15 minutes. A manual refresh is available once per minute.

## Cross-project dependencies

Initiatives can declare dependencies between projects:

- **Finish-to-start** — Project B cannot start until Project A finishes
- **Benefit transfer** — Project A's outcome is Project B's baseline
- **Resource sharing** — Projects share a constrained resource pool

Dependency violations trigger alerts to the initiative owner.

## Initiative health score

The health score is a composite metric (0–100) derived from:

| Factor | Weight | Calculation |
|--------|--------|-------------|
| Realization rate | 40% | Realized / Forecasted |
| Milestone health | 25% | On-time milestones / Total milestones |
| Budget health | 20% | 1 - (variance / budget) |
| Risk exposure | 15% | 1 - (open high-severity risks / total risks) |

Scores are color-coded:

- **Green (80–100)** — Healthy, on track
- **Yellow (50–79)** — Needs attention
- **Red (0–49)** — Requires executive intervention

Health scores appear on the portfolio dashboard and in weekly executive summaries.

## Example

A "Manufacturing Excellence 2026" initiative contains three projects:

| Project | Forecast | Realized | Status |
|---------|----------|----------|--------|
| Predictive Maintenance | $1.2M | $900K | Monitoring |
| Quality AI | $800K | $820K | Closed |
| Energy Optimization | $600K | $200K | At risk |

Initiative rollup: $2.6M forecast, $1.92M realized, 74% realization rate. The at-risk project triggers an executive alert.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Create and archive initiatives | Organization |
| User | Create initiatives | Assigned accounts |
| User | Add or remove projects | Owned initiatives |
| Executive | View all initiative rollups | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `initiatives:write` to create or edit; `initiatives:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 100 projects per initiative.

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 50 active initiatives per organization.

<span class="vp-badge vp-badge--limit">Limit</span> Cross-project dependency chains are limited to 10 levels to prevent circular references.

## Troubleshooting

??? question "Issue: Initiative realization rate does not match project totals"
    **Cause:** A project was added or removed after the last rollup, or a project has unreported actuals.
    **Resolution:** Click **Refresh Rollup** in the initiative header, or verify that all child projects have up-to-date actuals.

??? question "Issue: Cannot add a project to an initiative"
    **Cause:** The project is already owned by another initiative, or the project status is `cancelled`.
    **Resolution:** Remove the project from its current initiative first, or restore the project from cancelled status.

??? question "Issue: Dependency alert fires incorrectly"
    **Cause:** The dependency date was not updated after a schedule change.
    **Resolution:** Open the initiative's **Dependencies** panel, edit the affected dependency, and adjust the target date.

??? question "Issue: Initiative health score dropped suddenly"
    **Cause:** A large project was added to the initiative, diluting the realization rate, or a high-severity risk was logged.
    **Resolution:** Drill down into the health score breakdown. If the drop is due to a new project, confirm the project's forecast is realistic. If due to risk, review the risk register.

## Related pages

- [Projects](projects.md)
- [Benefits Tracking](benefits-tracking.md)
- [Value Realization](value-realization.md)
- [Outcomes](outcomes.md)

## Escalation path

For initiative governance or access issues, contact your workspace admin. For rollup calculation discrepancies, open a support ticket with the initiative ID and a screenshot of the portfolio view.
