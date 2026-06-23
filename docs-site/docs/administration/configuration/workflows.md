---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Workflows

Workflow configuration lets you define the status map, transitions, and approval gates that govern how records move through your value lifecycle.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Content Admin</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Review of [Workflow Management](../../workflow-management/index.md)
- Defined [statuses](../../workflow-management/statuses.md) for your process

## Workflow definitions

A workflow definition is a versioned set of rules applied to an entity type. ValuePact supports separate definitions for initiatives, business cases, and approvals.

| Property | Description |
|----------|-------------|
| Entity type | Initiative, Business Case, or Approval |
| Version | Auto-incremented on every publish |
| Status map | The statuses available to records |
| Transitions | Valid moves between statuses |
| Approval stages | Review gates (optional) |
| Automation rules | Triggered actions (optional) |

## Status maps

The status map lists every status a record can hold.

1. Go to **Admin** > **Configuration** > **Workflows**.
2. Select an entity type.
3. Click **Statuses**.
4. Add, reorder, or remove statuses.
5. Click **Save Draft**.

!!! warning "Status removal"
    You cannot remove a status that is in use by active records. Archive it instead.

## Transitions

Transitions define how records move between statuses.

### Step-by-step: add a transition

1. Open the workflow and click **Transitions**.
2. Click **Add Transition**.
3. Select **From Status** and **To Status**.
4. Choose **Trigger Type**: Manual or Automatic.
5. For manual transitions, select **Required Role**.
6. For automatic transitions, define the **Trigger Condition**.
7. Add **Guard Conditions** if needed.
8. Click **Save**.

## Approval gates

Approval gates are embedded in the workflow definition.

1. Open the workflow and click **Approval**.
2. Click **Add Stage**.
3. Define approvers, timeout, and escalation rule.
4. Link the stage to a transition into `approved` status.
5. Click **Save**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create, edit, publish workflows | Organization |
| Tenant Admin | Create, edit, publish workflows | Organization |
| Content Admin | Edit workflow drafts | Organization |
| Analyst | View active workflows | Assigned workflows |
| Viewer | View active workflows | Assigned workflows |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 50 statuses per workflow.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 100 transitions per workflow.

<span class="vp-badge vp-badge--limit">Limit</span> Workflow versions are retained for 12 months.

<span class="vp-badge vp-badge--limit">Limit</span> Publishing a workflow applies immediately to new records. Existing records remain on their current version unless migrated.

## Troubleshooting

??? question "Issue: transition button is missing"
    **Cause:** The user lacks the required role, a guard condition is failing, or the workflow version is stale.
    **Resolution:** Check the transition configuration for role requirements and guard conditions. Verify the record is on the latest workflow version.

??? question "Issue: approval stage not triggering"
    **Cause:** The stage is not linked to a transition, or the transition trigger is set to manual instead of automatic.
    **Resolution:** Open the workflow diagram and confirm the stage connects to the correct transition. Set the transition trigger to automatic if the stage completion should advance the record.

## Related pages

- [Configuration Overview](index.md)
- [Workflow Management Overview](../../workflow-management/index.md)
- [Statuses](../../workflow-management/statuses.md)
- [Approval Workflows](../../workflow-management/approval-workflows.md)
- [Automation](../../workflow-management/automation.md)

## Escalation path

For workflow definition errors causing records to stall:

1. Check the workflow version applied to the record in the record detail panel.
2. Roll back to the previous version if available.
3. File a support ticket with the workflow ID and affected record IDs.
4. Escalate to `#valuepact-ops` if rollback does not resolve the issue.
