---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Collaboration

Work with teammates using comments, tasks, approvals, sharing, and version history across all workspaces. Collaboration in ValuePact is tenant-scoped, traceable, and integrated into the workflow so feedback stays linked to the work it describes.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A signed-in session with access to the account or initiative.
- Appropriate role permissions for commenting or task creation.
- Reviewed [Core Concepts: Projects](../core-concepts/projects.md).

## Step-by-step instructions

### Comments and mentions

1. **Open the Comments page.** Navigate to **Collaboration → Comments** from the top navigation, or open the comment panel inside any workspace.
2. **Scope your comment.** Choose a **Subject type** from the dropdown:
   - `account`
   - `business_case`
   - `task`
   - `initiative`
3. Enter the **Subject ID** (for example, the business case UUID).
4. Optionally enter an **Account ID** to narrow scope.
5. **Write and post.** Enter your comment body and click **Post Comment**.
6. **Mention teammates.** Type `@` followed by a username to notify a teammate. They receive an in-app notification and an email if configured.

### Tasks and assignments

1. **Open the Tasks page.** Navigate to **Tasks** from the top navigation.
2. **Create a task.** Click **Create Task** and fill in the form:
   - **Title** — describe the work.
   - **Owner** — assignee name.
   - **Stage** — for example, `evidence`, `review`, `drivers`.
   - **Account ID** — optional scope.
3. **Track progress.** Tasks display status badges:
   - **Pending** — created but not started.
   - **In Progress** — actively being worked.
   - **Completed** — finished.
4. **Update status.** Click **Mark Complete** when the task is finished, or use the status dropdown to move it to **In Progress**.
5. **Reassign.** Admins and task creators can reassign tasks to other users.

### Approvals

1. **Request approval.** From a business case detail page, click **Request Approval** and select one or more reviewers.
2. **Review and decide.** Approvers receive a notification and can:
   - **Approve** — case moves to approved status.
   - **Reject** — case is blocked and requires rework.
   - **Request Changes** — case remains pending with feedback comments.
3. **View approval state.** The business case shows an **Approval Status** card with the current state and reviewer list.
4. **Escalate.** If an approver does not respond, admins can override or reassign the approval request.

### Sharing and permissions

1. **Share a deliverable.** From any business case or view, click **Share** and set visibility:
   - **Team** — visible to all users in the tenant.
   - **Restricted** — visible only to assigned users.
2. **Copy a link.** Generate a shareable link with an expiration date (default 30 days).
3. **Revoke.** Return to the share dialog and remove users or disable the link.

### Version history

1. **View revisions.** Open a business case and scroll to the **Revision History** section.
2. **Compare versions.** Click any revision to see a diff summary of what changed:
   - Title changes
   - Summary edits
   - Recommendation additions or removals
   - Metadata updates
3. **Restore a version.** Admins can restore an earlier version from the revision list. This creates a new revision rather than overwriting history.

!!! tip "Tip: Use tasks to drive workflow"
    Create tasks for each stage of the value workflow (signals, drivers, evidence, review) to keep the team aligned. Set due dates and link tasks to accounts so they appear on the Team Dashboard.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Comment / Create task / Share own | Assigned accounts |
| Admin | Edit / Delete any comment / Restore version / Override approvals | Tenant-wide |
| Executive | Approve / View all shared / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Comments are scoped by **subject_type** and **subject_id**; cross-subject linking is not supported.
<span class="vp-badge vp-badge--limit">Limit</span> Shareable links expire after **30 days** by default.
<span class="vp-badge vp-badge--limit">Limit</span> Each user can have at most **100 open tasks**.
<span class="vp-badge vp-badge--limit">Limit</span> Version history retains the last **50 revisions** per business case.

## Troubleshooting

??? question "Issue: Comments do not persist after reload"
    **Cause:** The comment was not posted successfully, or the subject ID is invalid.
    **Resolution:** Verify the subject ID exists and check the network response. Re-post if necessary. Ensure the subject_type matches the entity type exactly.

??? question "Issue: Task status does not update"
    **Cause:** Another user modified the task concurrently, or the API call failed.
    **Resolution:** Refresh the Tasks page and retry the status change. If the issue persists, check **Governance → Audit Log** for conflicting edits.

??? question "Issue: Approval request stuck in Pending"
    **Cause:** The approver has not logged in, or notifications are disabled.
    **Resolution:** Send a direct mention via Comments, or ask an admin to reassign the approval request.

??? question "Issue: Share link returns 403"
    **Cause:** The link expired, or the recipient lacks tenant access.
    **Resolution:** Generate a new link with a longer expiration, or invite the user to the tenant first.

??? question "Issue: Version history shows unexpected changes"
    **Cause:** An admin or automated workflow modified the case.
    **Resolution:** Check the **Governance → Audit Log** to identify who made the change and when.

## Related pages

- [Building a Business Case](building-a-business-case.md)
- [Managing Stakeholders](managing-stakeholders.md)
- [Team Dashboard](../dashboards-reporting/team-dashboard.md)
- [Individual Dashboard](../dashboards-reporting/individual-dashboard.md)
- [Core Concepts: Projects](../core-concepts/projects.md)

## Escalation path

For permission-related sharing failures, contact your workspace admin. For platform bugs, open a support ticket with severity **P3**.
