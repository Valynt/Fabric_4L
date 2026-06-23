---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Outcomes

Outcomes are concrete results achieved by projects and initiatives. They differ from outputs (such as deliverables completed) by measuring the real change in business performance.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- A completed or active [project](projects.md)
- Defined [value metrics](value-metrics.md) with baselines and targets
- [Actuals](actuals.md) recorded for the measurement period

## Overview

Outcomes validate that value was delivered, not just projected. They are the endpoint of the value realization lifecycle and the primary input to [benefits tracking](benefits-tracking.md) and executive reporting.

## Defining outcomes

An outcome record includes:

- **Name** — such as "Reduced onboarding cycle time by 30%"
- **Linked metric** — the value metric that measures the outcome
- **Baseline** — the starting value
- **Achieved value** — the realized value
- **Attribution method** — how credit is assigned to the project
- **Evidence** — supporting documents, system logs, or customer sign-off
- **Date achieved** — when the outcome was confirmed

Outcomes are defined during project chartering and validated at project closure.

## Measuring outcomes

Measurement methods vary by metric type:

| Method | Best for | Example |
|--------|----------|---------|
| System measurement | Automated, high-volume metrics | CRM pipeline velocity |
| Customer survey | Qualitative or satisfaction metrics | NPS improvement |
| Financial reconciliation | Cost or revenue metrics | Audited cost savings |
| Controlled comparison | Isolated impact metrics | A/B test conversion lift |
| Expert estimation | Early-phase or intangible metrics | Risk reduction score |

To record an outcome:

1. Open the project.
2. Click the **Outcomes** tab.
3. Click **Add Outcome**.
4. Select the linked metric.
5. Enter the achieved value, measurement method, and evidence URL or file.
6. Click **Save**.

## Attribution

Attribution determines how much of an outcome is credited to the project versus other factors. ValuePact supports three attribution models:

| Model | Use case | Calculation |
|-------|----------|-------------|
| Full attribution | The project is the sole cause | 100% credit |
| Partial attribution | Multiple projects contributed | User-defined percentage |
| Incremental attribution | Baseline trend must be subtracted | Achieved minus projected baseline trend |

!!! warning "Governance note"
    Full attribution requires a signed customer acknowledgement or audit trail. Unattributed outcomes are flagged in executive dashboards.

## Reporting

Outcomes feed three reporting layers:

1. **Project closeout report** — summary of all outcomes with variance to forecast
2. **Initiative rollup** — aggregated outcomes across projects
3. **Executive dashboard** — portfolio-level outcome metrics with trend lines

### Outcome validation workflow

Before an outcome is included in rollup reports, it passes a validation workflow:

| Step | Validator | Checkpoint |
|------|-----------|------------|
| 1. Record | Project owner | Achieved value entered |
| 2. Evidence check | System | Evidence file or URL present |
| 3. Attribution review | Initiative sponsor | Attribution model approved |
| 4. Customer sign-off | Account executive | Customer acknowledgement received |
| 5. Finalize | System | Outcome locked and reported |

Steps 3 and 4 can be waived by an admin for internal-only initiatives. Waivers are logged in the audit trail.

## Example

A customer success initiative reports the following outcomes:

| Outcome | Metric | Baseline | Achieved | Attribution | Variance to Forecast |
|---------|--------|----------|----------|-------------|---------------------|
| Reduced churn | Monthly churn rate | 12% | 8% | 100% | -1pp vs target |
| Faster onboarding | Time to first value | 45 days | 32 days | 80% | On target |
| Expansion revenue | Net revenue retention | 105% | 112% | 50% | +2pp vs target |

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure attribution models | Organization |
| User | Record and edit outcomes | Assigned projects |
| User | Upload evidence | Assigned projects |
| Executive | View outcome reports | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `outcomes:write` to record; `outcomes:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 50 outcomes per project.

<span class="vp-badge vp-badge--limit">Limit</span> Evidence files are limited to 25 MB each.

<span class="vp-badge vp-badge--limit">Limit</span> Outcomes cannot be backdated more than 90 days without admin approval.

## Troubleshooting

??? question "Issue: Outcome variance shows a large negative number"
    **Cause:** The achieved value was entered in a different unit than the forecast, or the baseline was incorrect.
    **Resolution:** Verify the unit consistency in **Value Studio > Metrics**. If the baseline was wrong, create a revision and recalculate variance.

??? question "Issue: Outcome is not appearing in the initiative rollup"
    **Cause:** The project status is not `monitoring` or `closed`, or the outcome lacks a linked metric.
    **Resolution:** Update the project status, or open the outcome and link it to a valid metric.

??? question "Issue: Attribution percentage cannot be changed"
    **Cause:** The outcome has been locked after customer sign-off or audit completion.
    **Resolution:** Contact an admin to unlock, or create a new outcome revision with updated attribution.

??? question "Issue: Outcome validation workflow is stuck at 'customer sign-off'"
    **Cause:** The customer acknowledgement email was not sent, or the sign-off link expired.
    **Resolution:** Resend the sign-off request from **Outcomes > Pending Sign-offs**. Links expire after 14 days.

## Related pages

- [Projects](projects.md)
- [Value Metrics](value-metrics.md)
- [Actuals](actuals.md)
- [Value Realization](value-realization.md)

## Escalation path

For attribution model questions, contact your value engineering lead. For reporting discrepancies, open a support ticket with the project ID and outcome ID.
