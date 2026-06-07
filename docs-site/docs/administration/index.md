---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Administration

Administration is the control center for your ValuePact tenant. Admins manage users, roles, configuration, and security settings to keep the platform aligned with organizational governance.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Super Admin or Tenant Admin role
- Familiarity with [user roles](../getting-started/user-roles.md)
- Access to the **Admin** workspace in the top navigation

## What admins control

| Area | What you can do | Canonical path |
|------|----------------|---------------|
| User Management | Invite, deactivate, and group users | **Admin** > **User Management** |
| Role Management | Create roles and assign permissions | **Admin** > **Role Management** |
| Configuration | Branding, fields, workflows, notifications | **Admin** > **Configuration** |
| Security | SSO, MFA, password policy, audit logs | **Admin** > **Security** |

## Admin experience tier

The Admin experience tier progressively discloses governance controls. Users with Admin roles see the **Admin** workspace. Other users do not.

- **Standard** users see simplified flows.
- **Advanced** users see modeling and inspection tools.
- **Admin** users see governance and tenant configuration.

## Step-by-step: switch to the Admin workspace

1. Click your avatar in the top-right corner.
2. Select **Switch to Admin** from the dropdown.
3. If you do not see the option, confirm your role includes Admin privileges.

!!! tip "Admin switch shortcut"
    Press `G` then `A` to jump directly to the Admin workspace from any page.

## Admin responsibilities checklist

Before go-live, confirm:

- [ ] User roles match your organizational hierarchy
- [ ] SSO or password policy is configured
- [ ] Workflows reflect your approval gates
- [ ] Notifications are routed to active channels
- [ ] Custom fields capture required business data
- [ ] Audit log retention meets compliance needs

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Full administration, billing, team, governance | Organization |
| Tenant Admin | Full administration, team, governance | Organization |
| Content Admin | Governance and content configuration | Organization |
| Analyst | View-only access to team membership | Assigned initiatives |
| Viewer | Read-only access to selected admin surfaces | Assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Only users with Tenant Admin or Super Admin roles can modify SSO and MFA settings.

<span class="vp-badge vp-badge--limit">Limit</span> Configuration changes apply immediately. There is no staging environment for tenant settings.

<span class="vp-badge vp-badge--limit">Limit</span> Audit logs are retained for 90 days by default. Extend retention in **Security** > **Audit Logs**.

## Troubleshooting

??? question "Issue: Admin workspace is not visible"
    **Cause:** Your role does not include Admin privileges, or your session tier is set to Standard.
    **Resolution:** Ask a Tenant Admin to verify your role. Toggle your experience tier to Advanced or Admin in your profile settings.

??? question "Issue: configuration change did not take effect"
    **Cause:** Some settings require a browser refresh or depend on a background sync.
    **Resolution:** Refresh the page. Wait up to 60 seconds for cached settings to invalidate.

??? question "Issue: unable to assign a Super Admin role"
    **Cause:** Only existing Super Admins can promote others to Super Admin.
    **Resolution:** Contact an existing Super Admin in your organization. If none are available, file a support ticket with legal authorization.

## Related pages

- [User Management](user-management/index.md)
- [Role Management](role-management/index.md)
- [Configuration](configuration/index.md)
- [Security](security/index.md)
- [Getting Started: User Roles](../getting-started/user-roles.md)

## Escalation path

For tenant-level misconfiguration or lockout:

1. Contact another Tenant Admin or Super Admin in your organization.
2. If all admins are unavailable, file a support ticket with severity **Critical**.
3. ValuePact Support can initiate a secure break-glass procedure after identity verification.
