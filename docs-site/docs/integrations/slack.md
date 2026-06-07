---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Slack Integration

## Overview

The Slack integration delivers real-time notifications, slash commands, and initiative updates directly into your workspaces. It reduces context switching and keeps teams aligned.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Slack workspace admin permission to install apps.
- ValuePact Organization Admin role.
- A dedicated channel for ValuePact notifications (recommended).

## Step-by-step instructions

### 1. Install the Slack app

1. In ValuePact, go to **Administration > Integrations > Slack**.
2. Click **Add to Slack**.
3. Select your workspace and approve the OAuth scopes.
4. Choose or create a channel for notifications, e.g., `#valuepact-alerts`.

### 2. Configure notifications

1. In ValuePact, open **Administration > Configuration > Notifications > Slack**.
2. Select event types:
   - Initiative status changes
   - Approval requests
   - Weekly digest
   - @mentions
3. Map each event type to a channel or DM.
4. Save.

### 3. Use slash commands

| Command | Description |
|---------|-------------|
| `/valuepact search [term]` | Search initiatives |
| `/valuepact status [initiative-id]` | Show initiative health |
| `/valuepact actuals [initiative-id]` | List latest actuals |
| `/valuepact help` | Show command reference |

### 4. Set up channel-specific alerts

1. Invite the ValuePact bot to a project channel.
2. Type `/valuepact subscribe [initiative-id]`.
3. The bot confirms the subscription.
4. All status changes for that initiative now post to the channel.

### 5. Verify delivery

1. Create a test initiative.
2. Change its status to **At Risk**.
3. Confirm the alert appears in the configured channel within 30 seconds.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure Slack integration | Organization |
| Admin | Manage notification rules | Organization |
| User | Use slash commands | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Slash command response time: 3 seconds.
- <span class="vp-badge vp-badge--limit">Limit</span> Subscriptions per channel: 20 initiatives.
- <span class="vp-badge vp-badge--limit">Limit</span> Messages per minute: 100 per workspace.

## Troubleshooting

??? question "Issue: Bot is not responding to slash commands"
    **Cause:** The Slack app was removed, or the command request URL is unreachable.
    **Resolution:**
    1. Reinstall the app from **Integrations > Slack**.
    2. Verify the request URL is whitelisted in your firewall.
    3. Re-authorize the bot.

??? question "Issue: Notifications stopped after renaming a channel"
    **Cause:** Slack channel IDs persist, but the bot membership is tied to the name.
    **Resolution:**
    1. Re-invite the ValuePact bot to the renamed channel.
    2. In ValuePact, click **Refresh Channels**.
    3. Re-select the channel in notification rules.

??? question "Issue: Duplicate notifications in multiple channels"
    **Cause:** Overlapping subscriptions or duplicate notification rules.
    **Resolution:**
    1. Audit **Notifications > Slack** rules.
    2. Remove redundant rules.
    3. Consolidate subscriptions into one channel per initiative type.

## Related pages

- [Notification Issues Troubleshooting](../troubleshooting/notification-issues.md)
- [Integration FAQ](../faq/integration-faq.md)
- [Stakeholder Engagement Best Practices](../best-practices/stakeholder-engagement.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Command or notification questions | #valuepact-support Slack |
| P2 | Bot unresponsive workspace-wide | support@valuepact.ai |
| P1 | Suspected data leakage through Slack | security@valuepact.ai |
