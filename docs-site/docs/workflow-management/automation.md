---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Workflow Automation

Automation reduces manual work by triggering actions when records change status, fields update, or time conditions are met.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Analyst</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Familiarity with [statuses](statuses.md) and [approval workflows](approval-workflows.md)
- Optional: [custom fields](../administration/configuration/custom-fields.md) configured

## Automation components

Every automation rule has three parts:

| Component | Purpose | Examples |
|-----------|---------|----------|
| Trigger | When the rule runs | Status changed, field updated, scheduled time |
| Condition | Filter for relevance | Value > 100k, category = "Strategic" |
| Action | What the rule does | Change status, send notification, update field |

## Available triggers

- **Status changed** — fires when a record enters or exits a status
- **Field updated** — fires when a specified field is modified
- **Record created** — fires on creation
- **Approval completed** — fires when all stages finish
- **Scheduled** — fires at a recurring time or date
- **Webhook received** — fires on external event

## Available actions

- Update status
- Update field value
- Send email notification
- Send in-app notification
- Send Slack or Microsoft Teams message
- Create a task or reminder
- Invoke external webhook
- Run a formula recalculation

## Condition examples

| Use case | Condition |
|----------|-----------|
| High-value initiatives | `budget gt 100000` |
| Strategic category | `category eq "Strategic"` |
| Overdue milestones | `milestone_date lt today()` |
| Finance group | `owner.group contains "Finance"` |

## Step-by-step: create an automation rule

1. Go to **Admin** > **Configuration** > **Workflows**.
2. Select a workflow and click **Automation**.
3. Click **Add Rule**.
4. Choose a **Trigger** from the list.
5. Define **Conditions** using the visual builder or expression editor.
6. Select one or more **Actions**.
7. Enter a **Rule Name** and set **Active** to `Enabled`.
8. Click **Save** and **Test** with a sample record.
9. Click **Publish** to activate.

!!! warning "Test before publish"
    Always test automation rules on a sample record. Actions such as status changes and webhooks execute immediately and cannot be undone in bulk.

## Conditions

Conditions use a simple expression language.

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | Equal to | `status eq "active"` |
| `ne` | Not equal | `priority ne "low"` |
| `gt` | Greater than | `budget gt 100000` |
| `contains` | Contains text | `title contains "Q3"` |
| `in` | In list | `category in ["A","B"]` |

You can combine conditions with `and` and `or`.

## Automation log

The automation log shows execution history for every rule:

| Column | Description |
|--------|-------------|
| Timestamp | When the rule ran |
| Rule name | The automation rule |
| Record | Affected record ID |
| Result | Success, skipped, or failed |
| Details | Error message or action summary |

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create, edit, delete automation rules | Organization |
| Tenant Admin | Create, edit, delete automation rules | Organization |
| Content Admin | Edit rule names and conditions | Organization |
| Analyst | View active rules on own records | Own records |
| Viewer | View active rules | Assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 100 active automation rules per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Each rule can have up to 10 conditions and 5 actions.

<span class="vp-badge vp-badge--limit">Limit</span> Scheduled triggers have a minimum interval of 15 minutes.

<span class="vp-badge vp-badge--limit">Limit</span> Webhook actions timeout after 30 seconds.

## Troubleshooting

??? question "Issue: automation rule did not run"
    **Cause:** The rule is disabled, conditions evaluated to false, or the rule is still queued.
    **Resolution:** Check the **Automation Log** for the rule status. Verify the record matches all conditions. Note that rules may take up to 60 seconds to execute.

??? question "Issue: automation created duplicate notifications"
    **Cause:** Multiple rules share the same trigger and lack mutual exclusion conditions.
    **Resolution:** Add a unique condition to each rule, such as checking a flag field that the first rule sets.

??? question "Issue: webhook action returns an error"
    **Cause:** The endpoint is unavailable, the payload is too large, or authentication failed.
    **Resolution:** Verify the webhook URL and headers. Check the **Automation Log** for the HTTP response code.

## Related pages

- [Statuses](statuses.md)
- [Approval Workflows](approval-workflows.md)
- [Escalations](escalations.md)
- [Custom Fields](../administration/configuration/custom-fields.md)
- [Integrations](../integrations/index.md)

## Escalation path

For automation rules causing unintended side effects:

1. Disable the rule immediately from **Configuration** > **Workflows** > **Automation**.
2. Review the **Automation Log** for affected record IDs.
3. File a support ticket with severity **Medium** and attach the rule definition.
4. Escalate to `#valuepact-ops` if the rule affected more than 50 records.
