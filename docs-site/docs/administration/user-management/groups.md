---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Groups

Groups simplify user management by letting you assign permissions, workflows, and notifications to a collection of users at once.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Analyst</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [User Management Overview](index.md)
- Defined [roles](../role-management/index.md) for group members

## Group types

| Type | Purpose | Example |
|------|---------|---------|
| Functional | Department or team | Finance, Operations |
| Project | Initiative-specific team | Q3 Cost Reduction |
| Approval | Reviewers for a workflow stage | Executive Committee |

## Create a group

1. Go to **Admin** > **User Management** > **Groups**.
2. Click **Create Group**.
3. Enter a **Group Name** and optional **Description**.
4. Select a **Group Type**.
5. Click **Save**.

## Add members

1. Open the group detail panel.
2. Click **Add Members**.
3. Search for users by name or email.
4. Select one or more users and click **Add**.

!!! tip "Bulk assignment"
    You can add up to 50 users to a group in a single operation.

## Group permissions

Groups can carry permissions that supplement individual roles.

1. Open the group and click **Permissions**.
2. Click **Add Permission**.
3. Choose a **Resource** and **Action**.
4. Set the **Scope**.
5. Click **Save**.

Group permissions are additive. A user receives the union of their role permissions and all group permissions they belong to.

## Bulk assignment

Use bulk assignment to add many users to a group quickly.

### Step-by-step: bulk assign

1. Go to **Admin** > **User Management** > **Groups**.
2. Select a group and click **Bulk Assign**.
3. Upload a CSV with a single `email` column, or paste a comma-separated list.
4. Click **Validate** to check for invalid or duplicate emails.
5. Click **Assign** to add valid users.

<span class="vp-badge vp-badge--limit">Limit</span> Bulk assignment supports up to 500 users per operation.

## Group sync with SSO

When SCIM is enabled, groups can sync automatically from your identity provider.

1. Go to **Security** > **SSO** > **SCIM**.
2. Enable **Group Sync**.
3. Map identity provider groups to ValuePact groups by exact name match.
4. Set **Auto-create groups** to `Enabled` if you want new groups imported automatically.

!!! warning "Name matching"
    Group names must match exactly, including case and spaces, for SCIM sync to link members correctly.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create, edit, delete groups | Organization |
| Tenant Admin | Create, edit, delete groups | Organization |
| Content Admin | View groups and members | Organization |
| Analyst | View groups they belong to | Own groups |
| Viewer | View groups they belong to | Own groups |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 200 groups per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> A user can belong to up to 50 groups.

<span class="vp-badge vp-badge--limit">Limit</span> Group names must be unique within a tenant.

## Troubleshooting

??? question "Issue: group permission not applied to a user"
    **Cause:** The user was added after the permission was set, or the group cache has not refreshed.
    **Resolution:** Remove and re-add the user. Wait 60 seconds and refresh. Check the user’s effective permissions.

??? question "Issue: cannot delete a group"
    **Cause:** The group is assigned as an approver in an active workflow, or it is the default group for SSO provisioning.
    **Resolution:** Remove the group from all workflow stages. Update the SSO default group before deleting.

??? question "Issue: SCIM group members not syncing"
    **Cause:** The group name in the identity provider does not match the ValuePact group name.
    **Resolution:** Compare names character-for-character. Update the mapping in **Security** > **SSO** > **SCIM**.

## Related pages

- [User Management Overview](index.md)
- [Invite Users](invite-users.md)
- [Remove Users](remove-users.md)
- [Permissions](permissions.md)
- [Role Management](../role-management/index.md)

## Escalation path

For group synchronization failures or SSO group mapping issues:

1. Verify the group name matches exactly in both ValuePact and the identity provider.
2. Check the SSO sync log in **Security** > **SSO** > **Provisioning Log**.
3. File a support ticket with the group name and expected member list.
4. Escalate to `#valuepact-ops` if provisioning stops for all groups.
