---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Permissions

Permissions control what actions a user can perform and on which data. ValuePact uses a role-based system with optional custom permissions for fine-grained control.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [User Roles](../../getting-started/user-roles.md)
- Familiarity with [Role Management](../role-management/index.md)

## Permission matrix by role

| Permission | Super Admin | Tenant Admin | Content Admin | Analyst | Editor | Viewer |
|-----------|:-----------:|:------------:|:-------------:|:-------:|:------:|:------:|
| Invite users | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No | No | No |
| Delete users | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No | No | No |
| Configure SSO | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No | No | No |
| Configure workflows | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No | No |
| Manage custom fields | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No | No |
| Create initiatives | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No | No |
| Edit initiatives | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No |
| View audit logs | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | View-only | No | No | No |
| Approve records | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | Assigned | Assigned | No |
| Export reports | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | <span class="vp-badge vp-badge--permission">Yes</span> | No |

## Custom permissions

Custom permissions extend the default roles. You can create permission sets that apply to specific record types, fields, or workflows.

### Step-by-step: add a custom permission

1. Go to **Admin** > **Role Management** > **Permission Assignment**.
2. Select a role and click **Add Custom Permission**.
3. Choose a **Resource Type**: Initiative, Business Case, Dashboard, or User.
4. Select an **Action**: Create, Read, Update, Delete, or Approve.
5. Define the **Scope**: Organization, Group, or Own Records Only.
6. Add an optional **Condition**, such as `value_metric > 100000`.
7. Click **Save**.

## Scope restrictions

Scope determines how far a permission reaches.

| Scope | Description |
|-------|-------------|
| Organization | All records in the tenant |
| Group | Records linked to the user’s groups |
| Own Records Only | Records where the user is the owner |

### Scope examples

| Use case | Scope |
|----------|-------|
| CFO can see all business cases | Organization |
| Department lead sees team initiatives | Group |
| Analyst sees only their own drafts | Own Records Only |

!!! warning "Scope inheritance"
    Custom permissions do not override deny rules. If a role lacks a base permission, a custom permission cannot grant it.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Manage all permissions | Organization |
| Tenant Admin | Manage all permissions | Organization |
| Content Admin | View permission matrix | Organization |
| Analyst | View own permissions | Own records |
| Viewer | View own permissions | Own records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 50 custom permission rules per role.

<span class="vp-badge vp-badge--limit">Limit</span> Conditions support up to 5 clauses per rule.

<span class="vp-badge vp-badge--limit">Limit</span> Permission changes take effect within 60 seconds.

## Troubleshooting

??? question "Issue: user has permission but action is blocked"
    **Cause:** A conflicting deny rule, missing field-level permission, or record-level scope restriction.
    **Resolution:** Check the role’s effective permissions in **Role Management** > **Effective Permissions**. Verify the record ownership and group membership.

??? question "Issue: custom permission not appearing"
    **Cause:** The permission was saved but the role cache has not refreshed.
    **Resolution:** Wait 60 seconds and refresh. If still missing, republish the role definition.

## Related pages

- [User Management Overview](index.md)
- [Groups](groups.md)
- [Role Management](../role-management/index.md)
- [Permission Assignment](../role-management/permission-assignment.md)

## Escalation path

For permission misconfiguration causing access issues:

1. Use the **Effective Permissions** simulator in **Role Management** to debug.
2. Revert the role to its previous version if available.
3. File a support ticket with the user ID, role name, and expected behavior.
4. Escalate to `#valuepact-ops` if the issue affects multiple users.
