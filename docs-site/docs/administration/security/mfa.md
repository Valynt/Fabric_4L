---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Multi-Factor Authentication (MFA)

MFA adds a second verification step to user logins. Enforcing MFA reduces the risk of credential-based attacks.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Authentication](authentication.md)
- Users must have access to a supported MFA device or app

## Supported methods

| Method | Description | Setup complexity |
|--------|-------------|-----------------|
| TOTP app | Time-based one-time password (e.g., Authenticator) | Low |
| SMS | Code sent via text message | Low |
| Hardware key | FIDO2/WebAuthn security key | Medium |
| Push notification | Mobile app push approval | Medium |

## Enforcing MFA

You can enforce MFA at the tenant level or for specific roles.

### Tenant-wide enforcement

1. Go to **Admin** > **Security** > **MFA**.
2. Toggle **Enforce MFA** to **On**.
3. Select **Grace Period**: 0, 7, or 14 days.
4. Choose **Allowed Methods**.
5. Click **Save**.

### Role-based enforcement

1. Open **Security** > **MFA** > **Role Requirements**.
2. Select a role from the list.
3. Toggle **Require MFA**.
4. Select allowed methods for that role.
5. Click **Save**.

!!! warning "Grace period"
    During the grace period, users can log in without MFA but see reminders. After the period ends, MFA is mandatory.

## Recovery

Users can set up recovery options in case they lose access to their primary MFA method.

| Recovery option | Setup | Use limit |
|-----------------|-------|-----------|
| Backup codes | Generated once during MFA setup | 10 uses |
| Secondary device | Register a second TOTP app or phone | 1 secondary |
| Admin reset | Tenant Admin disables MFA for the user | Unlimited |

### Step-by-step: reset MFA for a user

1. Go to **Admin** > **User Management** > **Users**.
2. Find the user and open the detail panel.
3. Click **Reset MFA**.
4. Confirm the action.
5. Instruct the user to re-enroll on next login.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Enforce MFA and reset any user's MFA | Organization |
| Tenant Admin | Enforce MFA and reset any user's MFA | Organization |
| Content Admin | View MFA policy | Organization |
| Analyst | Manage own MFA settings | Own user |
| Viewer | Manage own MFA settings | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Users can register up to 5 MFA devices.

<span class="vp-badge vp-badge--limit">Limit</span> Backup codes are single-use and must be regenerated after exhaustion.

<span class="vp-badge vp-badge--limit">Limit</span> SMS MFA is not available in all regions. TOTP is recommended as a fallback.

## Troubleshooting

??? question "Issue: user cannot enroll MFA"
    **Cause:** The selected method is disabled at the tenant level, or the device clock is out of sync.
    **Resolution:** Verify the method is allowed in **Security** > **MFA**. For TOTP, ensure the device time is synchronized.

??? question "Issue: MFA code rejected repeatedly"
    **Cause:** The code expired, or the user is on a backup code that was already used.
    **Resolution:** Wait for a new TOTP code. Check if the user is entering a backup code and provide a fresh one if needed.

??? question "Issue: enforced MFA is blocking a service account"
    **Cause:** Service accounts using API keys are exempt, but accounts using password login are subject to MFA.
    **Resolution:** Convert the service account to an API key. If password login is required, add the account to an exempt role.

## Related pages

- [Security Overview](index.md)
- [Authentication](authentication.md)
- [SSO](sso.md)
- [Audit Logs](audit-logs.md)

## Escalation path

For MFA enforcement causing widespread lockout:

1. Temporarily extend the grace period in **Security** > **MFA**.
2. Reset MFA for affected users individually.
3. File a support ticket with severity **High**.
4. Escalate to `#security-ops` if the issue indicates an MFA service degradation.
