---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Reporting Cadence

## Overview

Consistent reporting rhythms create accountability and surface problems early. This page provides templates for weekly, monthly, and quarterly value reporting.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Dashboards configured in ValuePact.
- Defined fiscal calendar and timezone.
- Agreement on metric definitions from finance.

## Step-by-step instructions

### 1. Weekly operating review

1. **Audience:** Initiative owners and team leads.
2. **Duration:** 30 minutes.
3. **Agenda:**
   - Green/amber/red status for each active initiative.
   - Blockers requiring cross-team help.
   - Actuals entered since last week.
4. **ValuePact actions:** Export the **Team Dashboard** to PDF and distribute 24 hours before the meeting.

### 2. Monthly business review

1. **Audience:** Department heads and value office.
2. **Duration:** 60 minutes.
3. **Agenda:**
   - Cumulative value realized vs. plan.
   - Variance analysis for metrics off by >5%.
   - Pipeline of upcoming initiatives.
4. **ValuePact actions:** Use the **Portfolio Dashboard** with date range set to month-to-date.

### 3. Quarterly board summary

1. **Audience:** Executive team and board members.
2. **Duration:** 90 minutes.
3. **Agenda:**
   - Strategic initiative ROI.
   - Risk-adjusted forecast.
   - Resource reallocation recommendations.
4. **ValuePact actions:** Export the **Executive Dashboard** to PowerPoint. Include evidence links for top three claims.

### 4. Automate distribution

1. Go to **Administration > Configuration > Notifications > Digests**.
2. Create a digest for each cadence.
3. Attach the relevant dashboard URL.
4. Schedule delivery: Monday 08:00 for weekly, first business day at 09:00 for monthly, and five days before the board meeting for quarterly.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure digests | Organization |
| User | Export dashboards | Assigned initiatives |
| Executive | View executive dashboard | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Digests per tenant: 20.
- <span class="vp-badge vp-badge--limit">Limit</span> Dashboard widgets per export: 12.
- <span class="vp-badge vp-badge--limit">Limit</span> PowerPoint export size: 50 MB.

## Troubleshooting

??? question "Issue: Weekly reports are ignored"
    **Cause:** The audience sees the report as noise because nothing changes week to week.
    **Resolution:**
    1. Lead with changes and decisions only.
    2. Remove static background sections.
    3. Send only amber and red initiatives unless explicitly requested otherwise.

??? question "Issue: Monthly numbers differ from finance"
    **Cause:** Timing differences (accrual vs. cash) or currency rate assumptions.
    **Resolution:**
    1. Align with finance on cutoff dates.
    2. Document the exchange rate source in the metric definition.
    3. Reconcile in a shared spreadsheet before the meeting.

## Related pages

- [Portfolio Reviews](portfolio-reviews.md)
- [Measuring Value](measuring-value.md)
- [Report Discrepancies Troubleshooting](../troubleshooting/report-discrepancies.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Reporting template questions | Customer Success Manager |
| Urgent | Board deadline at risk | support@valuepact.ai |
