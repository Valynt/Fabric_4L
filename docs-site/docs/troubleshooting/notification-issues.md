---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Notification Issues

## Overview

Missed notifications and undelivered emails undermine trust in the platform. This page covers how to diagnose deliverability problems, check suppression lists, and verify channel configuration.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Admin access to **Administration > Configuration > Notifications**.
- Ability to check spam folders and corporate mail gateway logs.
- Access to user profile notification preferences.

## Step-by-step instructions

### 1. Verify user preferences

1. Click your avatar and select **Profile > Notification Preferences**.
2. Confirm the desired channels are enabled (Email, Slack, In-App).
3. Verify the email address and phone number are correct.
4. Check that **Do Not Disturb** is not active.

### 2. Inspect email deliverability

1. Open **Administration > Configuration > Notifications > Email Logs**.
2. Search for the recipient address.
3. Review the delivery status: **Delivered**, **Bounced**, **Dropped**, or **Deferred**.
4. If bounced, note the SMTP response code.

### 3. Check suppression lists

1. In **Email Logs**, filter by **Status: Bounced**.
2. If an address appears with a hard bounce, it is auto-suppressed.
3. Click the address and select **Remove from Suppression List** only after confirming the address is valid.
4. Suppression removal takes effect within <span class="vp-badge vp-badge--limit">5 minutes</span>.

### 4. Validate Slack and Teams channels

1. Go to **Administration > Integrations > Slack** (or **Teams**).
2. Verify the bot is still a member of the target channel.
3. Check that the channel name has not changed.
4. Re-invite the bot if it was removed.

### 5. Review digest schedules

1. Open **Administration > Configuration > Notifications > Digests**.
2. Confirm the digest is enabled and the cron expression is valid.
3. Check the recipient list for the digest.
4. Trigger a test digest and verify receipt.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Manage notification settings | Organization |
| Admin | Manage suppression list | Organization |
| User | Edit own notification preferences | Own profile |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Suppression list removal: max 50 addresses per hour.
- <span class="vp-badge vp-badge--limit">Limit</span> Test digests: max 5 per hour per admin.
- <span class="vp-badge vp-badge--limit">Limit</span> Email rate: 1,000 messages per minute per tenant.
- <span class="vp-badge vp-badge--limit">Limit</span> In-app notification retention: 90 days.

## Troubleshooting

??? question "Issue: User is not receiving any emails"
    **Cause:** The address is on the suppression list, the corporate gateway is blocking the sender IP, or the user unsubscribed.
    **Resolution:**
    1. Check **Email Logs** for bounce or drop events.
    2. Whitelist `notifications@valuepact.ai` and the egress IPs in your mail gateway.
    3. Remove the address from suppression if appropriate.
    4. Ask the user to check spam and promotions folders.

??? question "Issue: Slack notifications stopped after a channel rename"
    **Cause:** The integration stores the channel ID, but the webhook or bot membership is tied to the name.
    **Resolution:**
    1. Re-invite the ValuePact bot to the renamed channel.
    2. In **Integrations > Slack**, click **Refresh Channels**.
    3. Re-select the channel in the notification rule.

??? question "Issue: Digest email contains stale data"
    **Cause:** The digest snapshot runs before the daily ETL (Extract, Transform, Load) completes.
    **Resolution:**
    1. Open **Digests > Schedule**.
    2. Shift the cron expression to at least 1 hour after the ETL window ends.
    3. Save and send a test digest.

## Related pages

- [Slack Integration](../integrations/slack.md)
- [Teams Integration](../integrations/teams.md)
- [Admin FAQ](../faq/admin-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Single user not receiving emails | #valuepact-support Slack |
| P2 | Entire tenant or channel missing notifications | support@valuepact.ai |
| P1 | Notification system down platform-wide | On-call page with subject "P1 Notification Outage" |
