---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Jira Integration

## Overview

The Jira connector links issues to value initiatives, syncs status, and maps story points or time tracking to benefit actuals. It bridges delivery execution and value realization.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Jira Cloud or Jira Data Center 9.x+.
- Admin access to Jira to install apps and manage webhooks.
- ValuePact Organization Admin role.

## Step-by-step instructions

### 1. Connect Jira to ValuePact

1. In ValuePact, go to **Administration > Integrations > Jira**.
2. Click **Connect**.
3. Enter your Jira base URL (e.g., `https://yourcompany.atlassian.net`).
4. Provide an API token (Cloud) or PAT (Data Center) with `read:jira-work` and `write:jira-work` scopes.
5. Test the connection and save.

### 2. Configure issue linking

1. Open **Issue Linking** settings.
2. Choose the Jira project(s) to sync.
3. Set the link type: **Relates to**, **Blocks**, or **Is delivered by**.
4. Map Jira issue types to ValuePact entities:
   - `Epic` → Initiative
   - `Story` / `Task` → Benefit actual
   - `Bug` → Risk

### 3. Sync status

1. Enable **Status Sync**.
2. Map Jira statuses to ValuePact workflow states:
   - `To Do` → Draft
   - `In Progress` → Active
   - `Done` → Completed
3. Choose sync direction. Most customers sync Jira → ValuePact.
4. Save.

### 4. Map effort to value

1. Open **Effort Mapping**.
2. Select the Jira field: `timeestimate`, `timespent`, or `customfield_storypoints`.
3. Define a conversion rate (e.g., 1 story point = $500).
4. Enable automatic creation of benefit actuals when issues transition to **Done**.

### 5. Verify end-to-end

1. Create a Jira issue in the linked project.
2. Link it to a ValuePact initiative.
3. Move the issue to **Done**.
4. Confirm the status update and benefit actual appear in ValuePact within the sync interval.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage issue linking | Organization |
| User | View linked issues | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Jira API rate: 10 requests per second per token.
- <span class="vp-badge vp-badge--limit">Limit</span> Linked issues per initiative: 200.
- <span class="vp-badge vp-badge--limit">Limit</span> Sync interval: minimum 5 minutes.

## Troubleshooting

??? question "Issue: Status changes in Jira do not reflect in ValuePact"
    **Cause:** The webhook in Jira was deleted, or the sync job is backlogged.
    **Resolution:**
    1. In Jira, check **System > WebHooks** for the ValuePact webhook.
    2. If missing, re-create it using the URL from **Integrations > Jira > Webhook URL**.
    3. Check ValuePact **Audit Logs** for Layer 1 queue depth.

??? question "Issue: Benefit actuals are created with incorrect values"
    **Cause:** The conversion rate or source field mapping is wrong.
    **Resolution:**
    1. Review **Effort Mapping** settings.
    2. Verify the Jira field contains numeric data.
    3. Update the conversion rate and recalculate historical actuals if needed.

??? question "Issue: Jira Cloud API token expired"
    **Cause:** Tokens expire after 30 days of inactivity or were revoked by an admin.
    **Resolution:**
    1. Generate a new token at id.atlassian.com.
    2. Update the token in **Integrations > Jira**.
    3. Re-test the connection.

## Related pages

- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)
- [Missing Data Troubleshooting](../troubleshooting/missing-data.md)
- [Integration FAQ](../faq/integration-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Linking or mapping questions | #valuepact-support Slack |
| P2 | Bidirectional sync broken | support@valuepact.ai |
| P1 | Data corruption in linked issues | On-call page with subject "P1 Jira Integration" |
