---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Benefits Tracking

Benefits tracking monitors expected versus achieved benefits across projects and initiatives. It surfaces variance early, trends performance over time, and holds execution accountable to the value model.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- A ValuePact account with at least one approved [business case](business-cases.md)
- Active [projects](projects.md) linked to the account
- [Actuals](actuals.md) configured or manually entered

## Overview

Benefits tracking operates at two levels:

- **Project level** — tracks benefit lines tied to individual project milestones
- **Initiative level** — rolls up project benefits into strategic program views

Each benefit line carries an expected value (from the forecast), an achieved value (from actuals), a variance, and a status indicator.

## How it works

### Define benefit lines

When a business case is approved, its value drivers are converted into benefit lines. Each line includes:

- **Driver name** — such as "Labor Efficiency" or "Downtime Reduction"
- **Category** — hard savings, strategic value, or risk reduction
- **Baseline** — the starting metric before the project
- **Target** — the forecasted metric at project completion
- **Timeline** — quarterly or monthly checkpoints

### Track actuals against expected

As [actuals](actuals.md) are ingested, the platform matches them to benefit lines by driver and time period. The tracking dashboard shows:

| Metric | Definition |
|--------|-----------|
| Expected | Forecasted benefit for the period |
| Achieved | Actual benefit recorded for the period |
| Variance | Achieved minus expected |
| Variance % | Variance divided by expected |
| Status | On track, at risk, off track, or achieved |

### Monitor trends

The trend view plots expected and achieved values over time. It highlights:

- **Positive drift** — achieved exceeds expected for two consecutive periods
- **Negative drift** — achieved falls below expected for two consecutive periods
- **Inflection points** — periods where variance crosses the 10% threshold

### Trigger alerts

Alerts fire automatically when:

- Variance exceeds 10% of expected or $10K (whichever is larger)
- A benefit line is off track for two consecutive periods
- A milestone is overdue and linked benefits are unreported

#### Alert severity levels

| Severity | Condition | Recipient |
|----------|-----------|-----------|
| Info | Variance between 5% and 10% | Project owner |
| Warning | Variance exceeds 10% or one period off track | Project owner and initiative sponsor |
| Critical | Two consecutive periods off track or milestone overdue | Executive sponsor and account team |

### Configure alert rules

1. Open **Administration > Configuration > Notifications**.
2. Select the **Benefits Tracking** category.
3. Adjust thresholds, severity mappings, and recipient roles.
4. Click **Save**.

Changes apply to all accounts in the organization.

### Categories of benefit lines

Benefit lines are classified by category to help stakeholders understand the nature of value:

| Category | Definition | Reporting treatment |
|----------|-----------|---------------------|
| Hard savings | Direct cost reduction or revenue increase | Top-line in CFO summaries |
| Strategic value | Indirect or long-term competitive advantage | Narrative in executive views |
| Risk reduction | Avoided loss or compliance improvement | Disclosure in risk sections |
| Capital efficiency | Improved asset or cash utilization | Balance sheet impact notes |

## Example

A manufacturing initiative tracks three benefit lines:

| Benefit Line | Expected YTD | Achieved YTD | Variance | Status |
|--------------|-------------|-------------|----------|--------|
| Downtime Reduction | $800K | $720K | -$80K | At risk |
| Yield Improvement | $400K | $410K | +$10K | On track |
| Energy Optimization | $200K | $190K | -$10K | On track |

The initiative manager receives an alert for Downtime Reduction and drills down to the linked project.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure benefit line templates | Organization |
| User | View and comment on tracking | Assigned accounts |
| User | Enter actuals and update status | Assigned projects |
| Executive | View initiative rollup | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `benefits:write` to enter actuals; `benefits:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 100 benefit lines per account.

<span class="vp-badge vp-badge--limit">Limit</span> Actuals must be entered within 90 days of the reporting period to avoid stale-data warnings.

<span class="vp-badge vp-badge--limit">Limit</span> Trend charts display up to 24 months of history.

## Troubleshooting

??? question "Issue: Benefit line shows 'missing baseline'"
    **Cause:** The baseline metric was not captured before the project started.
    **Resolution:** Enter a retroactive baseline in the **Benefits Tracking** tab. Baselines entered after project start are flagged with a warning icon.

??? question "Issue: Actuals do not appear in the tracking dashboard"
    **Cause:** The actuals source is not mapped to the correct driver ID or time period.
    **Resolution:** Open **Actuals > Reconciliation**, match unmapped rows to benefit lines, and confirm the mapping.

??? question "Issue: Initiative rollup does not match project totals"
    **Cause:** A project was removed from the initiative after benefits were recorded, or a project has duplicate benefit lines.
    **Resolution:** Review the initiative membership list and deduplicate benefit lines in **Project Settings > Benefits**.

??? question "Issue: Alert emails are not being received"
    **Cause:** The user's notification preferences are disabled, or the benefit line is not linked to a milestone.
    **Resolution:** Check **Profile > Notifications** for the user. Ensure the benefit line has at least one linked milestone in **Project > Milestones**.

## Related pages

- [Actuals](actuals.md)
- [Forecasts](forecasts.md)
- [Projects](projects.md)
- [Initiatives](initiatives.md)
- [Value Realization](value-realization.md)

## Escalation path

For data reconciliation issues, contact your account admin. For alert configuration or workflow changes, open a ticket with Platform Support.