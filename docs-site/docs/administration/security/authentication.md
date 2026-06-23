---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Authentication

Authentication verifies who a user is before granting access to ValuePact. You can configure password policies, session behavior, and API key governance.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Security Overview](index.md)

## Auth methods

ValuePact supports multiple authentication methods:

| Method | Best for | Configuration path |
|--------|----------|-------------------|
| Email and password | Small teams, quick start | Default |
| SSO (SAML/OIDC) | Enterprise directories | **Security** > **SSO** |
| API keys | Service and integration accounts | **Security** > **Authentication** > **API Keys** |

## Password policy

Password policies enforce minimum strength and rotation rules.

| Setting | Default | Range |
|---------|---------|-------|
| Minimum length | 12 characters | 8–128 |
| Complexity | Upper, lower, digit, symbol | Toggle each |
| Rotation period | 90 days | 0–365 (0 = disabled) |
| Reuse prevention | Last 5 passwords | 1–20 |
| Lockout threshold | 5 failed attempts | 3–10 |
| Lockout duration | 30 minutes | 5–1440 minutes |

### Step-by-step: update password policy

1. Go to **Admin** > **Security** > **Authentication**.
2. Click **Password Policy**.
3. Adjust the sliders and toggles.
4. Click **Preview** to see the impact on existing passwords.
5. Click **Save**.

!!! warning "Existing passwords"
    Policy changes apply to new passwords and resets. Existing passwords are not invalidated unless you force a reset.

## Session management

Sessions control how long a user remains logged in.

| Setting | Default | Description |
|---------|---------|-------------|
| Session lifetime | 8 hours | Time before forced re-authentication |
| Idle timeout | 30 minutes | Inactivity before prompt |
| Concurrent sessions | 3 per user | Maximum active sessions |
| Remember me | Disabled | Extended session on trusted devices |

### Step-by-step: configure session behavior

1. Open **Security** > **Authentication** > **Sessions**.
2. Set **Session Lifetime** and **Idle Timeout**.
3. Choose **Concurrent Session Limit**.
4. Toggle **Remember Me**.
5. Click **Save**.

## API keys

API keys are used for service-to-service authentication.

1. Go to **Security** > **Authentication** > **API Keys**.
2. Click **Create Key**.
3. Enter a **Name** and select a **Role**.
4. Choose an **Expiration**: 30, 90, or 365 days.
5. Copy the key immediately. It is shown only once.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 100 active API keys per tenant.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Manage password, session, and API key settings | Organization |
| Tenant Admin | Manage password, session, and API key settings | Organization |
| Content Admin | View authentication settings | Organization |
| Analyst | Manage own API keys | Own user |
| Viewer | View own session status | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Password history cannot be disabled.

<span class="vp-badge vp-badge--limit">Limit</span> Session lifetime cannot exceed 168 hours (7 days).

<span class="vp-badge vp-badge--limit">Limit</span> API keys expire automatically. There is no option for non-expiring keys.

## Troubleshooting

??? question "Issue: user cannot log in after password reset"
    **Cause:** The reset link expired, or the new password violates the updated policy.
    **Resolution:** Resend the reset link. Confirm the password meets all policy requirements shown in the UI.

??? question "Issue: API key rejected"
    **Cause:** The key is expired, revoked, or the role was deleted.
    **Resolution:** Check the key status in **API Keys**. Create a new key if the old one is expired.

## Related pages

- [Security Overview](index.md)
- [SSO](sso.md)
- [MFA](mfa.md)
- [Audit Logs](audit-logs.md)

## Escalation path

For authentication outages or brute-force attacks:

1. Review the login failure log in **Security** > **Audit Logs**.
2. Temporarily increase the lockout threshold if legitimate users are blocked.
3. File a support ticket with severity **High**.
4. Escalate to `#security-ops` if an attack pattern is confirmed.
