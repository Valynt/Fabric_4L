---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Dashboards & Reporting

ValuePact provides four levels of dashboards, each designed for a different decision horizon. Use them to monitor portfolio health, track initiative progress, surface blockers, and share insights with stakeholders. Reporting tools let you export, schedule, and distribute dashboards across your organization.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Dashboard philosophy

- **Top-down visibility** — Executives see portfolio rollups; teams see project status.
- **Drill-down** — Every high-level metric links to the underlying initiatives, drivers, and evidence.
- **Actionable** — Risk flags and blockers surface automatically so you can act before value decays.
- **Shareable** — Any dashboard view can be exported to PDF or scheduled for recurring delivery.

## Dashboard levels

| Level | Audience | Primary use | Key metrics |
|-------|----------|-------------|-------------|
| [Executive Dashboard](executive-dashboard.md) | C-suite, VP/SVP | Portfolio KPIs, strategic health, rollup views | Total value, average ROI, realization rate, at-risk count |
| [Portfolio Dashboard](portfolio-dashboard.md) | Directors, portfolio managers | Initiative health, risk flags, resource allocation | Health score, risk flags, resource allocation, status distribution |
| [Team Dashboard](team-dashboard.md) | Project leads, analysts | Project status, milestone tracking, blockers | Milestone progress, task completion, blocker list |
| [Individual Dashboard](individual-dashboard.md) | Any user | My initiatives, my tasks, my approvals | Recent activity, pending tasks, approval queue |

## Reporting workflows

1. **Explore** — Open the dashboard that matches your role.
2. **Drill** — Click any KPI or initiative card to open the detail view.
3. **Act** — Create a task, add a comment, or escalate a blocker directly from the dashboard.
4. **Share** — Export a PDF or schedule a report from [Exporting & Sharing Reports](exporting-sharing-reports.md).

## How dashboards connect to workspaces

```
Executive Dashboard
  └── Portfolio Dashboard
        └── Team Dashboard
              └── Individual Dashboard
                    └── Account Overview
                          ├── Intelligence workspace
                          ├── Value Studio workspace
                          └── Deliverables workspace
```

## Role-based entry points

=== "Executive"
    Start with the [Executive Dashboard](executive-dashboard.md). Review portfolio KPIs, then drill into the [Portfolio Dashboard](portfolio-dashboard.md) to inspect at-risk initiatives.

=== "Portfolio Manager"
    Start with the [Portfolio Dashboard](portfolio-dashboard.md). Filter by owner and status, then open the [Team Dashboard](team-dashboard.md) to manage blockers.

=== "Individual Contributor"
    Start with the [Individual Dashboard](individual-dashboard.md). Check pending tasks and approvals, then open the [Team Dashboard](team-dashboard.md) to update milestone status.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View Individual / Team | Assigned initiatives |
| Admin | View all dashboards / Configure scheduled reports / Set refresh policies | Tenant-wide |
| Executive | View Executive / Portfolio / Export summaries | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Dashboards refresh every **5 minutes**.
<span class="vp-badge vp-badge--limit">Limit</span> Scheduled reports are limited to **10 per tenant**.
<span class="vp-badge vp-badge--limit">Limit</span> Export generation may take up to **60 seconds** for large portfolios.

## Troubleshooting

??? question "Issue: Dashboard shows stale data"
    **Cause:** The cache has not refreshed, or the underlying ingestion job is incomplete.
    **Resolution:** Wait for the next refresh cycle, or manually reload the page. Check ingestion status in **Context Engine → Ingestion Jobs**.

??? question "Issue: Cannot see Executive Dashboard"
    **Cause:** Your user tier is `standard` and the dashboard requires `admin` or `executive` access.
    **Resolution:** Ask your admin to upgrade your role in **Workspace Settings → Team & Access → Roles**.

??? question "Issue: Scheduled report did not arrive"
    **Cause:** The tenant reached the report limit, or the recipient address is invalid.
    **Resolution:** Review scheduled reports in **Workspace Settings → Governance → Audit Log** and remove inactive schedules.

## Related pages

- [Executive Dashboard](executive-dashboard.md)
- [Portfolio Dashboard](portfolio-dashboard.md)
- [Team Dashboard](team-dashboard.md)
- [Individual Dashboard](individual-dashboard.md)
- [Exporting & Sharing Reports](exporting-sharing-reports.md)
- [Analytics Overview](../analytics/index.md)
- [Quick Start Guide](../getting-started/quick-start-guide.md)

## Escalation path

For dashboard configuration or scheduled report issues, contact your admin or open a support ticket with severity **P4**.
