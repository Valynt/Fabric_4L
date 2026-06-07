---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Team Dashboard

Track project status, milestone completion, and blockers for initiatives your team owns. The Team Dashboard uses a board view organized by workflow stage so you can see at a glance what is moving and what is stuck.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- Assigned initiatives with defined milestones.
- Tasks created for active work items.
- Reviewed [Dashboards & Reporting Overview](index.md).

## Step-by-step instructions

### 1. Open the Team Dashboard

1. Navigate to **Tasks** from the top navigation.
2. Alternatively, select **Team** from the dashboard switcher.

### 2. Review project status

The board view shows initiatives grouped by stage:

| Stage | Typical contents |
|-------|------------------|
| **Signals** | Raw market signals awaiting review |
| **Drivers** | Value drivers being mapped and validated |
| **Evidence** | Evidence collection and verification |
| **Review** | Business case review and approval queue |
| **Approved** | Approved cases ready for export or realization |

### 3. Track milestones

1. Each initiative card shows the next milestone due date.
2. A progress ring displays completion percentage.
3. Hover over the ring to see completed versus total milestones.

### 4. Manage blockers

Blockers appear as red badges on initiative cards. Click a blocker to:

1. **View root cause** — a short description of why the initiative is blocked.
2. **Create a task** — assign remediation work to a teammate.
3. **Notify the stakeholder** — send an in-app mention to the initiative owner.

### 5. Update task status

1. Use the inline task list below each initiative card.
2. Click the status dropdown to move a task:
   - **Pending → In Progress**
   - **In Progress → Completed**
3. Completed tasks update the milestone progress automatically.

### 6. Filter by assignee

1. Use the assignee filter to focus on your own work.
2. Admins can view the workload of any team member.
3. Use the **Unassigned** filter to find initiatives that need an owner.

!!! tip "Tip: Link tasks to stages"
    When creating a task, set the **Stage** field to `signals`, `drivers`, `evidence`, or `review` so it appears on the correct board column. This keeps the Team Dashboard synchronized with your workflow.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | View / Update tasks | Assigned initiatives |
| Admin | View all / Reassign / Escalate / Configure board columns | Tenant-wide |
| Executive | View | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Each initiative supports up to **50 active tasks**.
<span class="vp-badge vp-badge--limit">Limit</span> Milestone reminders are sent **3 days** before the due date.
<span class="vp-badge vp-badge--limit">Limit</span> Board views load up to **100 initiatives** at once.

## Troubleshooting

??? question "Issue: Milestone progress does not update"
    **Cause:** The milestone is not linked to a task or actual value.
    **Resolution:** Edit the milestone and link it to a task in the **Realization Plan** tab. Ensure the task status is tracked.

??? question "Issue: Blocker badge will not clear"
    **Cause:** The underlying issue (for example, missing evidence) has not been resolved.
    **Resolution:** Open the initiative detail, navigate to the flagged tab, and complete the required action. The badge clears after the next health score recalculation.

??? question "Issue: Initiative missing from board"
    **Cause:** The initiative stage field is empty, or the initiative is archived.
    **Resolution:** Edit the initiative and set a stage. Check the **Include Archived** toggle if needed.

??? question "Issue: Cannot reassign a task"
    **Cause:** The task is owned by another user and you lack edit permissions.
    **Resolution:** Ask the task creator or an admin to reassign it.

## Related pages

- [Portfolio Dashboard](portfolio-dashboard.md)
- [Individual Dashboard](individual-dashboard.md)
- [Collaboration](../end-user-guides/collaboration.md)
- [Dashboards & Reporting Overview](index.md)

## Escalation path

For task system failures or missing notifications, open a support ticket with severity **P3**.
