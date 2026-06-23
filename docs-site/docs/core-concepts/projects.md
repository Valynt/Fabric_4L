---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Projects

Projects are execution containers with timelines, resources, and status tracking. They turn approved business cases and value models into funded, measurable work.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An approved [business case](business-cases.md) or validated [opportunity](opportunities.md)
- Role permission to create projects
- An [initiative](initiatives.md) to host the project (optional but recommended)

## Overview

Projects in ValuePact follow a structured lifecycle from charter to closure. Each project inherits value targets from its parent business case and reports progress through milestones and benefit checkpoints.

## Lifecycle

```
CHARTER → ACTIVE → MONITORING → CLOSED
    ↓        ↓          ↓
ON_HOLD  AT_RISK   CANCELLED
```

| Status | Meaning | Who can set |
|--------|---------|-------------|
| Charter | Draft project plan, not yet funded | Project creator |
| Active | Work in progress | Project owner |
| Monitoring | Execution complete, benefits tracking active | Project owner |
| Closed | All benefits realized and validated | Project owner or admin |
| On Hold | Paused due to external dependency | Project owner |
| At Risk | Blocked or significantly off plan | Project owner or system |
| Cancelled | Terminated before completion | Admin |

## Milestones

Milestones mark key phases of execution. Each milestone carries:

- **Name and description**
- **Target date**
- **Completion criteria**
- **Linked benefit lines** — expected value delivery at this milestone
- **Dependencies** — other milestones or external deliverables

To add a milestone:

1. Open the project.
2. Click **Milestones** in the left panel.
3. Click **Add Milestone**.
4. Enter name, target date, and criteria.
5. Link benefit lines from the project's value model.
6. Click **Save**.

## Resources

Projects track resources by role and allocation:

| Resource type | Tracking |
|--------------|----------|
| Personnel | FTE allocation per role, start and end dates |
| Budget | Planned vs actual spend by cost category |
| External | Vendor or contractor assignments |

Resource data can be entered manually or synced from Jira, ServiceNow, or Salesforce.

## Status tracking

The project dashboard shows:

- **Schedule health** — on time, slipping, or overdue
- **Budget health** — under, on, or over budget
- **Benefit health** — value realization against forecast
- **Risk register** — open risks with severity and owner

Status updates are entered weekly by the project owner. Automated status is derived from milestone completion and actuals ingestion.

### Project charter template

When creating a project from a business case, the platform auto-populates a charter with:

- **Objectives** — copied from the business case value narrative
- **Scope** — capabilities and use cases mapped in the value model
- **Success criteria** — benefit lines and target metrics
- **Stakeholders** — RACI assignments from the account stakeholder map
- **Risks** — pre-populated from the business case risk section

You can customize the charter before moving the project from `charter` to `active`.

### Resource capacity planning

The resource panel highlights overallocation:

| Indicator | Meaning | Action |
|-----------|---------|--------|
| Green | Allocation ≤ 80% | No action |
| Yellow | Allocation 81–100% | Monitor for burnout |
| Red | Allocation > 100% | Reassign or extend timeline |

## Example

A procurement automation project:

| Milestone | Target Date | Status | Linked Benefit |
|-----------|-------------|--------|---------------|
| Requirements signed | Jan 15 | Complete | — |
| Integration built | Mar 30 | Complete | — |
| UAT passed | Apr 15 | At risk | — |
| Go-live | May 01 | On track | Labor Efficiency |
| Q1 benefits review | Jun 30 | Pending | $600K target |

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Create and archive projects | Organization |
| User | Create projects | Assigned accounts |
| User | Update status and milestones | Owned or assigned projects |
| Executive | View cross-project dashboards | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `projects:write` to create or edit; `projects:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 50 milestones per project.

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 20 active projects per account.

<span class="vp-badge vp-badge--limit">Limit</span> Status updates older than 14 days trigger a stale-project warning.

## Troubleshooting

??? question "Issue: Project status shows 'at risk' but work is on schedule"
    **Cause:** A linked benefit line is underperforming, or a milestone dependency is overdue.
    **Resolution:** Check the **Benefits** tab for variance and the **Dependencies** panel for blocked milestones.

??? question "Issue: Cannot link a business case to a new project"
    **Cause:** The business case status is not `approved` or `published`.
    **Resolution:** Verify the business case status in **Deliverables**. Only approved cases can spawn projects.

??? question "Issue: Milestone target date cannot be changed"
    **Cause:** The milestone is already marked complete, or you lack edit permission.
    **Resolution:** Reopen the milestone if needed, or ask the project owner to adjust the date.

??? question "Issue: Project charter is missing stakeholder assignments"
    **Cause:** The account stakeholder map was empty or not linked when the project was created.
    **Resolution:** Add stakeholders to the account in **Intelligence > Stakeholders**, then click **Sync Stakeholders** in the project charter.

## Related pages

- [Initiatives](initiatives.md)
- [Benefits Tracking](benefits-tracking.md)
- [Business Cases](business-cases.md)
- [Outcomes](outcomes.md)

## Escalation path

For project configuration issues, contact your workspace admin. For integration sync failures with Jira or ServiceNow, open a support ticket with the integration name and sync timestamp.