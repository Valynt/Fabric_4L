---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Remove Users

Removing a user requires choosing between deactivation and deletion. Deactivation preserves history and allows recovery. Deletion is permanent and should be used with caution.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Review of [Invite Users](invite-users.md)
- Understanding of record ownership in your tenant

## Deactivation vs deletion

| Action | Effect | Recoverable | Use when |
|--------|--------|-------------|----------|
| Deactivate | User cannot log in; history preserved | Yes | Temporary leave, role change, offboarding |
| Delete | User removed; history anonymized | No | Legal request, data subject request, irreversible offboarding |

## Deactivate a user

1. Go to **Admin** > **User Management** > **Users**.
2. Search for the user and click the row.
3. Click **Deactivate** in the detail panel.
4. Choose a **Reason** from the dropdown.
5. Decide whether to **Transfer ownership** of their records.
6. Click **Confirm**.

Deactivated users:

- Lose access immediately
- Do not count toward active user limits
- Retain their name on historical audit entries

## Delete a user

1. Go to **Admin** > **User Management** > **Users**.
2. Search for the user and click the row.
3. Click **Delete**.
4. Confirm that you understand deletion is irreversible.
5. Transfer or reassign record ownership.
6. Click **Permanently Delete**.

!!! warning "Deletion impact"
    Deleted user names are replaced with anonymized identifiers in audit logs. Their comments and evidence remain but show as "Former User."

## Data ownership transfer

Before removing a user, transfer ownership of initiatives, business cases, and evidence.

### Step-by-step: transfer ownership

1. In the user detail panel, click **Transfer Ownership**.
2. Select the **Target User** who will receive the records.
3. Choose **All Records** or filter by type.
4. Click **Preview** to review the transfer list.
5. Click **Execute Transfer**.

Records transfer with full history intact. The original creator is preserved in metadata.

### Ownership types that transfer

| Type | Transferred? | Notes |
|------|-------------|-------|
| Initiative owner | Yes | New owner receives notifications |
| Business case owner | Yes | Approval history preserved |
| Evidence uploader | No | Uploader metadata remains |
| Comment author | No | Comments show "Former User" if deleted |

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Deactivate and delete users | Organization |
| Tenant Admin | Deactivate and delete users | Organization |
| Content Admin | View user status | Organization |
| Analyst | Cannot remove users | — |
| Viewer | Cannot remove users | — |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Bulk deactivation supports up to 100 users at once.

<span class="vp-badge vp-badge--limit">Limit</span> Ownership transfer is limited to 1,000 records per operation.

<span class="vp-badge vp-badge--limit">Limit</span> Deleted users cannot be restored. Their tenant-scoped data is anonymized, not removed, to preserve referential integrity.

## Troubleshooting

??? question "Issue: cannot delete a user"
    **Cause:** The user is the sole owner of records and no transfer target is selected, or the user is the last Tenant Admin.
    **Resolution:** Assign a new owner to all records. Promote another user to Tenant Admin before deleting the last one.

??? question "Issue: transferred records still show the old owner"
    **Cause:** The browser cache is stale, or the transfer is still processing.
    **Resolution:** Refresh the page. Large transfers may take up to 5 minutes to complete.

??? question "Issue: deactivated user still receiving notifications"
    **Cause:** The user is subscribed to a shared report or group notification.
    **Resolution:** Remove the user from all groups and scheduled reports before deactivation.

## Related pages

- [User Management Overview](index.md)
- [Invite Users](invite-users.md)
- [Groups](groups.md)
- [Permissions](permissions.md)
- [Audit Logs](../security/audit-logs.md)

## Escalation path

For accidental deletion or failed ownership transfer:

1. If deactivation was used, reactivate the user immediately from **User Management** > **Deactivated Users**.
2. If deletion occurred, file a support ticket with severity **High** within 24 hours.
3. Escalate to `#valuepact-ops` if record ownership is inconsistent after transfer.
