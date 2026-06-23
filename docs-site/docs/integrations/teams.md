---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Microsoft Teams Integration

## Overview

The Microsoft Teams integration sends notifications, renders initiative tabs, and supports adaptive card interactions. It is the preferred channel for organizations standardized on Microsoft 365.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Microsoft 365 tenant admin consent to install Teams apps.
- ValuePact Organization Admin role.
- Azure AD app registration (auto-created during setup).

## Step-by-step instructions

### 1. Install the Teams app

1. In ValuePact, go to **Administration > Integrations > Microsoft Teams**.
2. Click **Install**.
3. You are redirected to Microsoft consent. Grant permissions for `ChannelMessage.Send`, `TeamsTab.ReadWrite.All`, and `User.Read`.
4. Select the team where ValuePact should operate.

### 2. Configure notifications

1. Open **Administration > Configuration > Notifications > Teams**.
2. Choose event types to publish.
3. Map each event to a Teams channel.
4. Save and send a test message.

### 3. Add the ValuePact tab

1. In Teams, open a channel.
2. Click the **+** icon to add a tab.
3. Select **ValuePact** from the app list.
4. Choose the view: **Portfolio Dashboard**, **Initiative Detail**, or **Executive Summary**.
5. Sign in once to link your ValuePact account.

### 4. Use adaptive cards

When an approval request is sent to Teams, the adaptive card includes:
- Initiative summary
- Approve / Reject / Request Changes buttons
- Comment field

Actions are recorded in ValuePact immediately and reflected in audit logs.

### 5. Verify connectivity

1. Create a test initiative.
2. Submit it for approval.
3. Confirm the adaptive card appears in the designated channel.
4. Approve via Teams and verify the status updates in ValuePact.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure Teams integration | Organization |
| Admin | Manage notification rules | Organization |
| User | Interact with tabs and cards | Own tenant |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Adaptive card size: 28 KB.
- <span class="vp-badge vp-badge--limit">Limit</span> Tabs per team: 16 (Microsoft limit).
- <span class="vp-badge vp-badge--limit">Limit</span> Message rate: 50 per minute per connector.

## Troubleshooting

??? question "Issue: Tab shows 'Sign in required' repeatedly"
    **Cause:** The Azure AD token expired, or conditional access policies block silent refresh.
    **Resolution:**
    1. Sign out and sign back in via the tab.
    2. Ask your Microsoft 365 admin to verify conditional access policies for `valuepact.ai`.
    3. Re-consent the app in Azure AD.

??? question "Issue: Adaptive card buttons do nothing"
    **Cause:** The Teams connector URL changed, or the bot was removed from the team.
    **Resolution:**
    1. Verify the bot is a member of the team.
    2. In ValuePact, click **Repair Connection**.
    3. Re-test with a new approval request.

??? question "Issue: Notifications arrive late"
    **Cause:** Microsoft Teams webhook endpoints throttle under high load.
    **Resolution:**
    1. Check Teams service health in the Microsoft 365 admin center.
    2. Reduce notification volume by disabling non-critical event types.
    3. Use email as a fallback for time-sensitive alerts.

## Related pages

- [Notification Issues Troubleshooting](../troubleshooting/notification-issues.md)
- [Integration FAQ](../faq/integration-faq.md)
- [Stakeholder Engagement Best Practices](../best-practices/stakeholder-engagement.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Tab or card questions | #valuepact-support Slack |
| P2 | Teams integration down for tenant | support@valuepact.ai |
| P1 | Authentication bypass or data exposure | security@valuepact.ai |
