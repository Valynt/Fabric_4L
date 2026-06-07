---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Permission Assignment

Permission assignment is where you grant or restrict capabilities for a role. You can set permissions at the organization level, group level, or down to individual records.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Role Creation](role-creation.md)
- Familiarity with [Permissions](../user-management/permissions.md)

## Granular permission assignment

ValuePact supports resource-level and action-level granularity.

| Resource | Actions |
|----------|---------|
| Initiative | Create, Read, Update, Delete, Approve, Export |
| Business Case | Create, Read, Update, Delete, Approve, Export |
| Dashboard | View, Edit, Schedule, Export |
| User | Invite, Deactivate, Delete, Assign Role |
| Workflow | Edit, Publish, Delete |
| Field | View, Edit, Configure |

## Scope restrictions

Every permission has a scope that limits its reach.

| Scope | Effect |
|-------|--------|
| Organization | Applies to all records in the tenant |
| Group | Applies to records linked to the user's groups |
| Own Records Only | Applies only when the user is the owner |

### Step-by-step: assign a scoped permission

1. Go to **Admin** > **Role Management**.
2. Select a role and click **Permission Assignment**.
3. Click **Add Permission**.
4. Choose a **Resource** and **Action**.
5. Select **Scope**.
6. Optionally add a **Condition**.
7. Click **Save**.

## Conditions

Conditions let you restrict permissions based on record data.

| Condition type | Example |
|----------------|---------|
| Field value | `status eq "active"` |
| Numeric range | `budget gt 50000` |
| Date range | `start_date within "this_quarter"` |
| Group membership | `user.group contains "Finance"` |

!!! warning "Condition evaluation"
    Conditions are evaluated at runtime. If a condition references a deleted field, the permission is denied by default.

## Effective permissions

The **Effective Permissions** simulator shows the final access a user has after combining role, group, and custom permissions.

1. Go to **Admin** > **Role Management** > **Effective Permissions**.
2. Select a **User**.
3. Select a **Resource**.
4. Click **Simulate** to see Allow, Deny, or Conditional results.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Assign and revoke all permissions | Organization |
| Tenant Admin | Assign and revoke all permissions | Organization |
| Content Admin | View permission assignments | Organization |
| Analyst | View own effective permissions | Own user |
| Viewer | View own effective permissions | Own user |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 50 custom permission rules per role.

<span class="vp-badge vp-badge--limit">Limit</span> Conditions support up to 5 clauses per rule.

<span class="vp-badge vp-badge--limit">Limit</span> Permission assignment changes are audited and cannot be hidden.

## Troubleshooting

??? question "Issue: permission appears assigned but does not work"
    **Cause:** A conflicting deny rule exists, or the condition evaluates to false.
    **Resolution:** Use the **Effective Permissions** simulator. Check for deny rules and condition logic.

??? question "Issue: cannot add a condition to a permission"
    **Cause:** The resource type does not support conditions, or the condition references an unsupported field type.
    **Resolution:** Check the field type in **Configuration** > **Custom Fields**. Conditions are supported on text, number, date, and select fields.

## Related pages

- [Role Management Overview](index.md)
- [Role Creation](role-creation.md)
- [Permissions](../user-management/permissions.md)
- [Groups](../user-management/groups.md)

## Escalation path

For permission assignment bugs or effective permission mismatches:

1. Export the role definition JSON from **Role Management** > **Export**.
2. Run the **Effective Permissions** simulator and capture the output.
3. File a support ticket with the role name, user ID, and simulator results.
4. Escalate to `#valuepact-ops` if the mismatch indicates a security issue.
