---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Individual Dashboard

See your personal workload: initiatives you own, tasks assigned to you, and approvals awaiting your review. The Individual Dashboard is your daily starting point for focused work in ValuePact.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- At least one initiative or task assigned to you.
- Reviewed [Dashboards & Reporting Overview](index.md).

## Step-by-step instructions

### 1. Open your dashboard

1. Click **Home** from the left rail.
2. Scroll to the **Recent Activity** panel on the right side.

### 2. Review My Initiatives

The **Recent Maps** table shows:

| Column | Description |
|--------|-------------|
| Domain | The company or account domain |
| Pages | Number of pages processed by ingestion |
| Status | Current ingestion or initiative status |
| Updated | Last activity timestamp |

Click any row to open the account overview.

### 3. Check My Tasks

1. Navigate to **Tasks** from the top navigation.
2. The default filter shows tasks assigned to you.
3. Use tabs to switch between:
   - **Open** — pending and in-progress tasks
   - **Completed** — finished tasks
   - **All** — full history

### 4. Review pending approvals

1. Approval requests appear in the **Notifications** panel on the home page.
2. Click a notification to open the business case detail page.
3. Review the case, inspect claim validation, and choose:
   - **Approve**
   - **Request Changes**
   - **Reject**

### 5. Quick actions

From the home page, use the **Prospect Prompt Builder** to:

1. Describe a new account in plain language.
2. Let the system suggest signals and drivers.
3. Create the account and jump straight into the Intelligence workspace.

### 6. Track activity

The **Recent Activity** feed shows:

- Ingestion job status changes
- New comments on initiatives you follow
- Task completions by teammates
- Business case approvals

!!! tip "Tip: Set notification preferences"
    Go to **Settings → Notifications** to choose how you receive task reminders and approval requests. Options include in-app, email, and Slack (if integrated).

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View own | Personal |
| Admin | View any user’s dashboard / Reassign tasks | Tenant-wide |
| Executive | View own / Team rollup | Personal and direct reports |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Recent activity shows the last **30 days**.
<span class="vp-badge vp-badge--limit">Limit</span> Notifications are batched and sent at most **once per hour**.
<span class="vp-badge vp-badge--limit">Limit</span> The task list loads up to **100 tasks** per page.

## Troubleshooting

??? question "Issue: My tasks do not appear"
    **Cause:** The task assignee field does not match your username, or the task is scoped to a different account.
    **Resolution:** Ask the task creator to verify the assignee name, or remove the account filter. Check that you are viewing the correct tenant workspace.

??? question "Issue: Approval request is missing"
    **Cause:** The request was sent to a different reviewer, or the business case was regenerated and lost the approval chain.
    **Resolution:** Open the business case detail and click **Request Approval** again. Check the **Revision History** to see if the case was regenerated.

??? question "Issue: Recent Maps table is empty"
    **Cause:** You have not created or accessed any accounts recently.
    **Resolution:** Create a new account using the **Prospect Prompt Builder**, or open an existing account from the **Accounts** list.

??? question "Issue: Notifications are delayed"
    **Cause:** Notification batching is enabled, or the email provider is experiencing delays.
    **Resolution:** Switch to in-app notifications for real-time updates, or check your email spam folder.

## Related pages

- [Team Dashboard](team-dashboard.md)
- [Collaboration](../end-user-guides/collaboration.md)
- [Quick Start Guide](../getting-started/quick-start-guide.md)
- [Dashboards & Reporting Overview](index.md)

## Escalation path

For persistent notification failures, open a support ticket with severity **P4**.
