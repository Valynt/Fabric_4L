---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Escalations

Escalations ensure that stalled approvals and overdue actions do not block value delivery. You define timeout rules, notification paths, and override permissions for each workflow.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Analyst</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Active [approval workflows](approval-workflows.md)
- Configured [notification channels](../administration/configuration/notifications.md)

## Escalation rules

An escalation rule links a trigger to a set of actions. Triggers are time-based or event-based.

| Trigger | Description |
|---------|-------------|
| Approval timeout | Stage has not been approved or rejected within the configured window |
| SLA breach | Record has been in a status longer than the service-level agreement |
| Value at risk | Forecasted value degradation exceeds a threshold |
| Manual escalation | User clicks **Escalate** on a record |

## Timeout configuration

Each approval stage has its own timeout. When the timeout expires, the escalation rule fires.

| Timeout tier | Default | Use case |
|-------------|---------|----------|
| Standard | 72 hours | Normal business approvals |
| Urgent | 24 hours | Time-sensitive initiatives |
| Critical | 4 hours | Executive or risk-related decisions |

### Step-by-step: set a stage timeout

1. Open **Admin** > **Configuration** > **Workflows**.
2. Select the workflow and click **Approval**.
3. Click the stage name to edit.
4. Enter **Timeout (hours)**.
5. Select **Escalation Rule** from the dropdown.
6. Click **Save** and **Publish**.

## Notification paths

Escalation notifications follow a configurable path.

```
Primary approver --> Secondary approver --> Group owner --> Tenant Admin
```

You can customize the path per workflow:

1. Go to **Configuration** > **Workflows** > **Escalations**.
2. Click **Add Path**.
3. Define up to 5 levels.
4. At each level, choose **Notify** and/or **Reassign**.
5. Select notification channels: **In-app**, **Email**, **Slack**, or **Microsoft Teams**.

!!! tip "Channel fallback"
    If the primary channel fails after two retries, the system falls back to email.

## Override permissions

Override permissions allow authorized users to bypass a stage or force a transition.

| Override type | Who can use it | Audit impact |
|--------------|---------------|--------------|
| Force approve | Tenant Admin, Super Admin | Logged as override with reason required |
| Force reject | Tenant Admin, Super Admin | Logged as override with reason required |
| Skip stage | Super Admin only | Logged as skip with full trace |
| Extend timeout | Tenant Admin, stage owner | Logged as timeout extension |

!!! warning "Override governance"
    Every override requires a reason. Reasons are included in the [audit log](../administration/security/audit-logs.md) and cannot be edited after submission.

## Escalation metrics

Track escalation effectiveness from the **Escalations** dashboard:

| Metric | Meaning |
|--------|---------|
| Average resolution time | Hours from trigger to closure |
| Escalation rate | Percentage of records that escalate |
| Override frequency | Number of force actions per week |

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Configure escalation rules and overrides | Organization |
| Tenant Admin | Configure escalation rules; use force approve/reject | Organization |
| Content Admin | Edit notification paths | Organization |
| Analyst | Extend timeout on own records | Own records |
| Viewer | View escalation status | Assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 20 escalation rules per workflow.

<span class="vp-badge vp-badge--limit">Limit</span> Notification paths support up to 5 levels.

<span class="vp-badge vp-badge--limit">Limit</span> Timeout extensions cannot exceed 720 hours per event.

<span class="vp-badge vp-badge--limit">Limit</span> Escalation actions are rate-limited to 10 per minute per workflow.

## Troubleshooting

??? question "Issue: escalation did not fire after timeout"
    **Cause:** The workflow was republished after the record entered the stage, or the escalation rule is disabled.
    **Resolution:** Check the workflow version applied to the record. Verify the escalation rule status in **Configuration**.

??? question "Issue: override button is disabled"
    **Cause:** The user lacks the required role, or the record is in a terminal status.
    **Resolution:** Confirm the user holds Tenant Admin or Super Admin role. Archived and completed records cannot be overridden.

??? question "Issue: escalation sent to a deactivated user"
    **Cause:** The notification path references a user who was deactivated after the path was created.
    **Resolution:** Update the escalation path to reference a role or group instead of a named user.

## Related pages

- [Approval Workflows](approval-workflows.md)
- [Automation](automation.md)
- [Notifications](../administration/configuration/notifications.md)
- [Audit Logs](../administration/security/audit-logs.md)

## Escalation path

For escalation system failures (notifications not sending, rules not evaluating):

1. Check the notification delivery log in **Configuration** > **Notifications** > **Delivery Log**.
2. Verify the workflow version and rule enablement status.
3. File a support ticket with severity **High**.
4. Escalate to `#valuepact-ops` if multiple workflows are affected.
