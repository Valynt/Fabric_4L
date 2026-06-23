---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# User Roles

ValuePact controls access through two complementary mechanisms: **experience tiers** and **roles**. Tiers progressively disclose features in the interface, while roles determine administrative boundaries and data access.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">End User</span>

## Overview

Every user in ValuePact is a member of a Clerk organization (tenant). Within that organization, the user has a role that governs what they can view, edit, approve, and administer. The platform also supports tiered disclosure—Standard, Advanced, and Admin modes—that changes which UI surfaces are visible without altering underlying permissions.

## Experience tiers

The interface adapts to three tiers:

| Tier | Description | How to access |
|------|-------------|---------------|
| **Standard** | Simplified flows for business users. Hides advanced modeling and configuration. | Default for most users. Toggle in the left rail footer. |
| **Advanced** | Power-user modeling and inspection tools. Exposes formula editing, driver trees, and agent configuration. | Toggle **Advanced Mode** in the left rail footer. |
| **Admin** | Governance controls and tenant configuration. Shows user management, billing, audit logs, and integrations. | Gated by role; only **Admin** and **Super Admin** users see this tier. |

!!! note
    Users can switch between **Standard** and **Advanced** modes using the tier switcher in the left rail footer. **Admin** capabilities are locked and require the corresponding role.

## Roles and permissions

### Super Admin

The highest level of access. Typically reserved for platform owners and tenant creators.

- [x] Full user and role management
- [x] Billing and subscription configuration
- [x] SSO and MFA setup
- [x] API key management
- [x] Audit log access across the organization
- [x] Cross-account data access (bypasses account-level scoping)
- [x] Activate and deactivate industry value packs
- [x] Configure custom fields and workflows

!!! warning
    **Super Admin** bypasses Row-Level Security (RLS) for operational tasks. All bypass actions are logged in the audit trail.

### Admin (Tenant Admin)

Day-to-day administrators who manage the organization but do not require full platform control.

- [x] Invite, remove, and deactivate users
- [x] Assign and revoke roles
- [x] Manage teams and groups
- [x] Configure branding and notifications
- [x] View audit logs (read-only)
- [x] Approve business cases for export
- [x] Manage integrations (Salesforce, HubSpot, Slack, etc.)
- [ ] Cannot modify billing subscriptions (Super Admin only)
- [ ] Cannot delete the organization (Super Admin only)

### Executive

Senior stakeholders who review portfolios and approved deliverables.

- [x] View executive and portfolio dashboards
- [x] Approve business cases
- [x] View audit logs (read-only)
- [x] Export approved reports
- [ ] Cannot edit value models or formulas
- [ ] Cannot manage users or settings
- [ ] Cannot create or delete accounts

### User

Standard team members who build value models and deliverables.

- [x] Create and edit prospect accounts
- [x] Use **Intelligence** and **Value Studio** workspaces
- [x] Edit variables and formulas (Advanced mode)
- [x] Generate business cases
- [x] Submit cases for approval
- [x] View stakeholders and evidence
- [ ] Cannot approve or export business cases
- [ ] Cannot access audit logs or governance
- [ ] Cannot manage users or integrations

### Viewer

Read-only access for stakeholders who need visibility without mutation rights.

- [x] View intelligence data (signals, drivers, evidence, stakeholders)
- [x] View approved business cases and deliverables
- [x] View dashboards (team and individual)
- [ ] Cannot edit any data
- [ ] Cannot create accounts or business cases
- [ ] Cannot export deliverables
- [ ] Cannot access audit logs

## Role-to-workspace mapping

| Workspace | Viewer | User | Executive | Admin | Super Admin |
|-----------|--------|------|-----------|-------|-------------|
| **Accounts** | View | Create/Edit | View | Full | Full |
| **Intelligence** | View | Edit | View | Full | Full |
| **Value Studio** | View | Edit | View | Full | Full |
| **Deliverables** | View (approved only) | Create/Submit | Approve/Export | Full | Full |
| **Governance** | — | — | View audit | Full | Full |
| **Settings** | — | — | — | Full | Full |
| **Context Engine** | View | View/Use | View | Configure | Full |

!!! tip
    A dash (—) means the workspace is not visible to that role in the left rail.

## How roles are assigned

1. An **Admin** or **Super Admin** navigates to **Settings** > **Team & Access**.
2. Click **Invite Members** and enter the user's email address.
3. Select a role from the dropdown: **Viewer**, **User**, **Executive**, **Admin**.
4. The invited user receives an email and joins the Clerk organization on first sign-in.

!!! note
    Role changes take effect immediately. The user does not need to sign out and back in.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Assign roles | Organization |
| Admin | Deactivate users | Organization |
| Super Admin | Delete organization | Organization |
| Super Admin | Configure billing | Organization |

<span class="vp-badge vp-badge--permission">Required</span> Only **Super Admin** can delete the organization or modify billing details.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 50 **Admin** users per organization.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 500 total users per organization on the Standard plan; enterprise tiers support more.

<span class="vp-badge vp-badge--limit">Limit</span> A user can belong to up to 10 Clerk organizations simultaneously.

<span class="vp-badge vp-badge--limit">Limit</span> Role assignment changes are audited. You cannot self-elevate to **Admin** or **Super Admin**.

## Troubleshooting

??? question "Issue: I cannot see the Admin tier in the left rail switcher"
    **Cause:** Your role is **User**, **Viewer**, or **Executive**. The Admin tier is gated by role, not by toggle.
    **Resolution:** Ask an **Admin** or **Super Admin** to elevate your role in **Settings** > **Team & Access**.

??? question "Issue: A new team member sees a blank page after accepting the invite"
    **Cause:** The user has not selected an active organization, or the invite was sent to a different email.
    **Resolution:** Ask the user to check the **Choose a workspace** screen after sign-in. If the organization is missing, resend the invite to the exact email address registered with Clerk.

??? question "Issue: I changed a user's role but they still see the old UI"
    **Cause:** The frontend caches tier and role state for the session duration.
    **Resolution:** The user should refresh the browser. If the issue persists, ask them to sign out and sign in again.

??? question "Issue: An Executive cannot export a business case"
    **Cause:** The case status is **draft** or the Executive role lacks export permission on unapproved cases.
    **Resolution:** Ensure the case is **approved**. If approved and still blocked, verify the Executive has not been downgraded to **Viewer**.

## Related pages

- [Navigating the Platform](navigating-the-platform.md)
- [Quick Start Guide](quick-start-guide.md)
- [Administration: User Management](../administration/user-management/index.md)
- [Administration: Role Management](../administration/role-management/index.md)
- [Administration: Permissions](../administration/user-management/permissions.md)
- [Administration: Security](../administration/security/index.md)

## Escalation path

If role assignment or access issues persist:

1. Verify the user's role in **Settings** > **Team & Access**.
2. Check the [Troubleshooting: Permission Issues](../troubleshooting/permission-issues.md) guide.
3. Open a support ticket with severity **S3** and include the affected user email and expected role.
4. For suspected tenant isolation violations, escalate to severity **S1** immediately.
