---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Invite Users

Adding users to ValuePact ensures teams can collaborate on initiatives and business cases. You can invite users individually, in bulk, or automatically through SSO.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Analyst</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Verified email domain (recommended for SSO auto-provisioning)
- Access to **Admin** > **User Management**

## Invitation methods

| Method | Best for | Speed |
|--------|----------|-------|
| Email invite | Small teams, targeted additions | Immediate |
| Bulk import | Large teams, migrations | Minutes |
| SSO auto-provisioning | Enterprise directories | Automatic |

## Invite by email

1. Go to **Admin** > **User Management** > **Invite Users**.
2. Enter the **Email Address**.
3. Select an initial **Role** from the dropdown.
4. Optionally assign the user to one or more **Groups**.
5. Click **Send Invite**.

The user receives an email with a secure link to set a password and join the tenant. Invites expire after 7 days.

!!! tip "Role selection"
    Assign the least-privileged role that matches the user’s responsibilities. You can promote later.

## Bulk import

Bulk import is useful when onboarding an entire department or migrating from another platform.

### CSV format

```csv
email,first_name,last_name,role,group
alice@example.com,Alice,Chen,Analyst,Finance
bob@example.com,Bob,Singh,Viewer,Operations
```

### Step-by-step: bulk import

1. Go to **Admin** > **User Management** > **Invite Users**.
2. Click **Bulk Import**.
3. Download the **CSV template**.
4. Fill in user details. Use valid role names exactly as shown in the UI.
5. Upload the file and click **Validate**.
6. Review the validation report for errors.
7. Click **Import** to send invites.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 500 rows per CSV file.

## Re-inviting users

If an invite expires or bounces, you can resend it:

1. Go to **User Management** > **Users**.
2. Filter by status **Invited**.
3. Select the user and click **Resend Invite**.
4. Optionally update the role or groups before resending.

## SSO auto-provisioning

When SSO is enabled with SCIM, users are provisioned automatically.

1. Enable SSO in **Admin** > **Security** > **SSO**.
2. Configure SCIM in your identity provider.
3. Map identity provider groups to ValuePact groups.
4. Assign roles via your identity provider role claims.

Users logging in through SSO are created on first login if they match the verified domain.

!!! warning "Domain verification"
    Auto-provisioning only works for verified domains. Add and verify domains in **Security** > **SSO** before enabling SCIM.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Invite users by any method | Organization |
| Tenant Admin | Invite users by any method | Organization |
| Content Admin | View invited user list | Organization |
| Analyst | Cannot invite users | — |
| Viewer | Cannot invite users | — |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Pending invites expire after 7 days and can be resent twice.

<span class="vp-badge vp-badge--limit">Limit</span> Email addresses must be unique across the tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Bulk imports are rate-limited to one per 5 minutes.

## Troubleshooting

??? question "Issue: invite email bounces"
    **Cause:** Invalid email address, full mailbox, or corporate filter.
    **Resolution:** Verify the email spelling. Ask the user’s IT team to whitelist `noreply@valuepact.ai`. Resend the invite.

??? question "Issue: bulk import validation fails"
    **Cause:** Missing required columns, invalid role names, or duplicate emails.
    **Resolution:** Ensure the CSV uses the exact template headers. Check that role names match the canonical list in **Role Management**.

??? question "Issue: SSO user lands on login page instead of dashboard"
    **Cause:** SCIM is not configured, or the user domain is not verified.
    **Resolution:** Verify domain verification in **Security** > **SSO**. Confirm the SCIM bearer token is active.

## Related pages

- [User Management Overview](index.md)
- [Remove Users](remove-users.md)
- [Groups](groups.md)
- [Permissions](permissions.md)
- [SSO](../security/sso.md)

## Escalation path

For invite delivery or provisioning failures at scale:

1. Check the **Delivery Log** in **Configuration** > **Notifications**.
2. Retry the import or invite after correcting errors.
3. File a support ticket with the affected email addresses and timestamp.
4. Escalate to `#valuepact-ops` if SSO provisioning stops entirely.
