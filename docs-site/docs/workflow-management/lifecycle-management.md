---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Lifecycle Management

Lifecycle management governs how a record progresses from creation through archive. Stage gates ensure quality and compliance at every step.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Analyst</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Configured [statuses and transitions](statuses.md)
- Understanding of [value realization](../core-concepts/value-realization.md)

## Lifecycle stages

| Stage | Status range | Purpose | Gate |
|-------|-------------|---------|------|
| Inception | `draft` | Capture the idea | Required fields complete |
| Review | `in_review` | Validate approach | Approval workflow complete |
| Commitment | `approved` | Allocate resources | Budget and stakeholder sign-off |
| Execution | `active` | Deliver outcomes | Milestones tracked |
| Closure | `completed` | Validate value | Evidence uploaded and actuals captured |
| Retention | `archived` | Audit and reference | Retention period defined |

## Stage gates

Stage gates are mandatory checks that block progression until satisfied.

### Default gates

- **Inception gate:** Title, description, and at least one value metric.
- **Review gate:** All approval stages passed with no active rejections.
- **Commitment gate:** Budget field populated and stakeholder mapping complete.
- **Execution gate:** Start date is today or earlier; owner assigned.
- **Closure gate:** Actual benefit values entered and linked to evidence.
- **Retention gate:** Retention category selected (regulatory, contractual, standard).

### Custom gates

You can add custom gates tied to fields, formulas, or external data.

1. Open **Admin** > **Configuration** > **Workflows**.
2. Select a workflow and click **Stage Gates**.
3. Click **Add Gate**.
4. Choose a gate type: **Field**, **Formula**, **Integration**, or **Approval**.
5. Define the pass condition and error message.
6. Click **Save** and **Publish**.

## Gate evaluation behavior

| Gate type | Evaluation timing | Failure action |
|-----------|-------------------|----------------|
| Field | On transition attempt | Block transition, show error |
| Formula | On transition attempt | Block transition, show error |
| Integration | Async, before transition | Block transition, queue retry |
| Approval | During approval stage | Return to `rejected` or stay `in_review` |

## Retention policies

Retention policies control how long records remain in `completed` before automatic archiving.

| Retention category | Default duration | Action at expiry |
|-------------------|------------------|-----------------|
| Standard | 12 months | Auto-archive to `archived` |
| Contractual | 84 months (7 years) | Auto-archive to `archived` |
| Regulatory | Configurable per jurisdiction | Hold until policy date; then archive |

!!! warning "Regulatory holds"
    Records under regulatory hold cannot be manually deleted. Adjust the hold date before attempting removal.

## Step-by-step: configure a retention policy

1. Go to **Admin** > **Configuration** > **Workflows**.
2. Open the entity workflow (Initiative or Business Case).
3. Click the **Retention** tab.
4. Select a **Default retention category**.
5. Set **Auto-archive** to `Enabled` or `Disabled`.
6. Click **Save** and **Publish**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Configure stage gates and retention | Organization |
| Tenant Admin | Configure stage gates and retention | Organization |
| Content Admin | Edit gate messages and retention labels | Organization |
| Analyst | View gate status on own records | Own records |
| Viewer | View gate status | Assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 10 custom stage gates per workflow.

<span class="vp-badge vp-badge--limit">Limit</span> Retention duration cannot exceed 255 months.

<span class="vp-badge vp-badge--limit">Limit</span> Records in `archived` status are read-only. Edit requires temporary reactivation by an Admin.

<span class="vp-badge vp-badge--limit">Limit</span> Integration gates timeout after 30 seconds and fail closed.

## Troubleshooting

??? question "Issue: record stuck at a stage gate"
    **Cause:** A required field is empty, a formula evaluates to false, or an integration check is failing.
    **Resolution:** Open the record detail panel. Review the **Gate Status** section for the specific failure and remediation steps.

??? question "Issue: record archived too early"
    **Cause:** The retention policy was set to a short duration, or a bulk automation rule triggered archive.
    **Resolution:** Admins can reactivate a record from **Admin** > **Records** > **Reactivate**. Update the retention policy to prevent recurrence.

??? question "Issue: integration gate keeps failing"
    **Cause:** The external service is unavailable, or the integration credential expired.
    **Resolution:** Check the integration health in **Configuration** > **Integrations**. Reauthorize the connection if the token is expired.

## Related pages

- [Statuses](statuses.md)
- [Approval Workflows](approval-workflows.md)
- [Automation](automation.md)
- [Custom Fields](../administration/configuration/custom-fields.md)

## Escalation path

For stage gate or retention policy misconfiguration:

1. Verify the workflow version in **Configuration** > **Workflows** > **Versions**.
2. Roll back to the previous version if the issue is blocking.
3. Contact support with the workflow ID and affected record IDs.
4. Escalate to `#valuepact-ops` if rollback does not resolve the issue.
