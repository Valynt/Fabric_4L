---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Security

Security administration protects your tenant data, controls access, and maintains compliance. You manage authentication, single sign-on, multi-factor authentication, and audit logs from the Security workspace.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Super Admin or Tenant Admin role
- Review of [Administration Overview](../index.md)
- Access to your identity provider (for SSO configuration)

## Security areas

| Area | Purpose | Path |
|------|---------|------|
| Authentication | Password policy, session management, API keys | **Security** > **Authentication** |
| SSO | SAML, OIDC, SCIM, domain verification | **Security** > **SSO** |
| MFA | Enforce multi-factor authentication | **Security** > **MFA** |
| Audit Logs | Search, export, and retain activity records | **Security** > **Audit Logs** |

## Security principles

ValuePact follows these principles across all security features:

- **Tenant isolation:** Users cannot access data outside their tenant.
- **Least privilege:** Users receive the minimum permissions needed.
- **Audit everything:** Administrative actions are logged and immutable.
- **Fail secure:** Misconfigurations default to denying access, not allowing it.

## Step-by-step: open security settings

1. Navigate to **Admin** > **Security**.
2. Select a tab from the left sidebar.
3. Review the current configuration.
4. Click **Edit** to modify settings.

!!! warning "Sensitive changes"
    Changes to SSO, MFA, or password policy can lock users out. Coordinate changes and communicate timing to your organization.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Manage all security settings | Organization |
| Tenant Admin | Manage all security settings | Organization |
| Content Admin | View security configuration | Organization |
| Analyst | View own security settings | Own user |
| Viewer | View own security settings | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> SSO configuration changes require a 5-minute cooldown between saves to prevent accidental lockout.

<span class="vp-badge vp-badge--limit">Limit</span> Audit logs are retained for 90 days by default. Extend retention up to 7 years in **Audit Logs** > **Retention**.

<span class="vp-badge vp-badge--limit">Limit</span> MFA enforcement applies to all users except break-glass emergency accounts.

## Troubleshooting

??? question "Issue: users locked out after security change"
    **Cause:** SSO certificate expired, MFA enforcement is incomplete, or password policy is too strict.
    **Resolution:** Use a break-glass Super Admin account to revert the change. Verify the SSO certificate validity in **Security** > **SSO**.

??? question "Issue: security settings not saving"
    **Cause:** Another admin has the settings locked, or the change violates a policy constraint.
    **Resolution:** Check for an active editing session. Review error messages for constraint details.

## Related pages

- [Authentication](authentication.md)
- [SSO](sso.md)
- [MFA](mfa.md)
- [Audit Logs](audit-logs.md)
- [Administration Overview](../index.md)

## Escalation path

For tenant-wide lockout or suspected security breach:

1. Use a break-glass Super Admin account to access the tenant.
2. Revert the most recent security change.
3. File a support ticket with severity **Critical**.
4. Escalate to `#security-ops` if unauthorized access is confirmed.
