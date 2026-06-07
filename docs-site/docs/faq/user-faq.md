---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# User FAQ

## Overview

This page covers daily usage questions, keyboard shortcuts, and best practices for end users who create and track value initiatives.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- Active ValuePact account with at least one assigned initiative.
- Completion of the beginner learning path (recommended).

## Frequently asked questions

### 1. How do I create a new value initiative?

1. Click **New Initiative** in the top navigation bar.
2. Select a template or start blank.
3. Fill in the title, owner, and target outcome.
4. Click **Save Draft** or **Submit for Approval**.

### 2. What keyboard shortcuts are available?

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Open global search |
| `Ctrl + /` | Open keyboard help |
| `G` then `D` | Go to Dashboard |
| `G` then `I` | Go to Initiatives |
| `Esc` | Close modal or panel |
| `N` then `I` | New Initiative |

### 3. How do I track benefits over time?

1. Open an initiative and select the **Benefits** tab.
2. Click **Add Actual**.
3. Enter the period, value, and evidence link.
4. Save. The line chart auto-updates.

### 4. Can I upload files as evidence?

Yes. Each benefit actual supports up to <span class="vp-badge vp-badge--limit">10 attachments</span>. Supported formats: PDF, PNG, JPG, XLSX, and CSV. Maximum file size is <span class="vp-badge vp-badge--limit">25 MB</span> per file.

### 5. How do I @mention a colleague?

Type `@` in any comment field. A searchable list of users in your tenant appears. Select the user. They receive an in-app notification and an email digest if enabled.

### 6. What does the color coding mean?

| Color | Meaning |
|-------|---------|
| Green | On track |
| Amber | At risk |
| Red | Off track |
| Gray | Not started |
| Blue | Completed |

### 7. How do I export my initiative to share offline?

1. Open the initiative.
2. Click **Actions > Export > PDF**.
3. Choose detail level: Summary or Full.
4. Download the file.

### 8. Why is my initiative stuck in "Pending Approval"?

Your workflow requires one or more approval gates. Check the **Workflow** tab to see who owns the next approval. You can send a reminder by clicking **Nudge Approver**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Create initiatives | Own team |
| User | Edit own initiatives | Own initiatives |
| User | Add actuals | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Initiatives per user: 50 active.
- <span class="vp-badge vp-badge--limit">Limit</span> Comments per initiative: 500.
- <span class="vp-badge vp-badge--limit">Limit</span> Attachment storage: 1 GB per user.

## Troubleshooting

??? question "Issue: Search does not find my initiative"
    **Cause:** The initiative is in a different tenant, archived, or filtered out by default scopes.
    **Resolution:**
    1. Check the tenant selector.
    2. Toggle **Include Archived** in search filters.
    3. Verify you are the owner or a stakeholder.

??? question "Issue: Chart values look wrong after editing a benefit"
    **Cause:** The cache has not refreshed.
    **Resolution:**
    1. Hard refresh the page.
    2. Wait up to 5 minutes for the aggregation pipeline to catch up.

## Related pages

- [Admin FAQ](admin-faq.md)
- [Data Quality Best Practices](../best-practices/data-quality.md)
- [Stakeholder Engagement Best Practices](../best-practices/stakeholder-engagement.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | How-to questions | #valuepact-users Slack |
| Urgent | Data loss or access block | support@valuepact.ai |
