---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Role Creation

Custom roles let you model your organization's hierarchy without forcing users into predefined buckets. You can create roles from scratch or clone an existing role as a template.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Role Management Overview](index.md)
- Defined permission requirements for the new role

## Create a role from scratch

1. Go to **Admin** > **Role Management**.
2. Click **New Role**.
3. Enter a **Role Name** and optional **Description**.
4. Select a **Base Tier**: Standard, Advanced, or Admin.
5. Choose the initial **Permissions** from the checklist.
6. Click **Save**.

## Clone a role

Cloning copies all permissions and settings from an existing role. This is the fastest way to create variations.

1. Go to **Admin** > **Role Management**.
2. Find the role you want to clone.
3. Click the **...** menu and select **Clone**.
4. Enter a new **Role Name**.
5. Adjust permissions as needed.
6. Click **Save**.

!!! tip "Clone default roles"
    Clone default roles such as Analyst or Editor to create department-specific variants without starting from zero.

## Permission checklist

When creating a role, you select permissions across these categories:

- **User Management:** Invite, deactivate, delete
- **Role Management:** Create, edit, assign
- **Configuration:** Workflows, fields, branding, notifications
- **Security:** SSO, MFA, audit logs
- **Records:** Create, read, update, delete, approve
- **Reports:** View, export, schedule
- **Integrations:** Configure, test, disable

## Step-by-step: create a department-specific role

1. Click **New Role**.
2. Name it "Finance Analyst."
3. Clone from the base **Analyst** role.
4. Add the **View Audit Logs** permission with scope **Own Records Only**.
5. Remove the **Delete Records** permission.
6. Click **Save** and **Assign Users**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create and clone roles | Organization |
| Tenant Admin | Create and clone roles | Organization |
| Content Admin | View role details | Organization |
| Analyst | Cannot create roles | — |
| Viewer | Cannot create roles | — |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Role names must be unique within the tenant.

<span class="vp-badge vp-badge--limit">Limit</span> A role can have up to 200 permissions.

<span class="vp-badge vp-badge--limit">Limit</span> Custom roles cannot exceed the base tier of the creator. Only Super Admin can create roles with Admin tier.

## Troubleshooting

??? question "Issue: cloned role has unexpected access"
    **Cause:** The source role contained hidden group permissions or custom conditions.
    **Resolution:** Review the cloned role in **Permission Assignment** and remove unwanted rules.

??? question "Issue: role not visible to assign to users"
    **Cause:** The role is saved but not published, or it belongs to a tier higher than the assigning admin.
    **Resolution:** Ensure the role status is **Active**. Confirm the admin's tier supports assigning that role.

## Related pages

- [Role Management Overview](index.md)
- [Permission Assignment](permission-assignment.md)
- [User Management](../user-management/index.md)
- [Permissions](../user-management/permissions.md)

## Escalation path

For role creation failures or tier conflicts:

1. Verify your admin tier in **My Account** > **Profile**.
2. Check the role creation audit log for error details.
3. File a support ticket with the intended role name and permissions.
4. Escalate to `#valuepact-ops` if the UI returns a persistent error.
