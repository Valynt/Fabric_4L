---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Notifications

Notifications keep users informed about approvals, status changes, and system events. You configure channels, templates, frequency, and digest settings from a single surface.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Content Admin</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Review of [Configuration Overview](index.md)
- Verified email and integration settings for external channels

## Notification channels

| Channel | Use case | Setup required |
|---------|----------|---------------|
| In-app | Real-time alerts inside ValuePact | None |
| Email | Detailed updates, invites, digests | Verified sender domain |
| Slack | Team channel alerts | Slack workspace connected |
| Microsoft Teams | Team channel alerts | Teams tenant connected |

## Templates

Templates define the content of each notification type.

| Template | Trigger | Editable fields |
|----------|---------|----------------|
| Approval Request | Record enters review stage | Subject, body, action button text |
| Status Change | Record status updated | Subject, body, status label |
| Digest | Scheduled summary | Subject, summary format, max items |
| Escalation | Timeout or manual escalation | Subject, body, escalation path |

### Step-by-step: edit a template

1. Go to **Admin** > **Configuration** > **Notifications**.
2. Click **Templates**.
3. Select a template from the list.
4. Edit the **Subject** and **Body**.
5. Use the variable picker to insert dynamic values.
6. Click **Preview** to send a test.
7. Click **Save**.

## Frequency and digests

Users can choose how often they receive non-urgent notifications.

| Frequency | Description |
|-----------|-------------|
| Immediate | Send as soon as the event occurs |
| Hourly | Batch and send once per hour |
| Daily | Single digest at a configured time |
| Weekly | Single digest on a chosen day |

### Step-by-step: set digest defaults

1. Go to **Configuration** > **Notifications** > **Digest Settings**.
2. Select the **Default Frequency** for new users.
3. Choose the **Delivery Time** for daily and weekly digests.
4. Set the **Max Items** per digest.
5. Click **Save**.

!!! tip "User override"
    Users can override digest settings in **My Account** > **Notifications** unless you lock the setting.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Configure all notification settings | Organization |
| Tenant Admin | Configure all notification settings | Organization |
| Content Admin | Edit templates and digest settings | Organization |
| Analyst | Set personal notification preferences | Own user |
| Viewer | Set personal notification preferences | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Email templates cannot exceed 100 KB in size.

<span class="vp-badge vp-badge--limit">Limit</span> Digests support up to 50 items. Older items are linked instead of inlined.

<span class="vp-badge vp-badge--limit">Limit</span> Slack and Microsoft Teams messages are limited to 3,000 characters. Longer content is truncated with a link.

## Troubleshooting

??? question "Issue: notifications not sending"
    **Cause:** The channel is disabled, the user unsubscribed, or the integration token expired.
    **Resolution:** Check **Configuration** > **Notifications** > **Channels**. Verify the user preference in **User Management**. Reauthorize Slack or Teams if the token is expired.

??? question "Issue: digest contains old items"
    **Cause:** The digest was generated before the items were read, or the frequency is set too low.
    **Resolution:** Switch the user to immediate or hourly frequency. Check the digest generation timestamp.

## Related pages

- [Configuration Overview](index.md)
- [Branding](branding.md)
- [Workflows](workflows.md)
- [Escalations](../../workflow-management/escalations.md)

## Escalation path

For notification delivery failures at the tenant level:

1. Check the **Delivery Log** in **Configuration** > **Notifications**.
2. Verify channel credentials and domain verification.
3. File a support ticket with the channel type and failure count.
4. Escalate to `#valuepact-ops` if no notifications are delivering to any user.
