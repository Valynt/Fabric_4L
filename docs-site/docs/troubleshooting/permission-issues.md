---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Permission Issues

Diagnose and resolve access errors, role problems, and cross-tenant isolation issues.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Common issues

### "Access denied" or 403 error

**Symptom**: Error 403 when accessing a page, feature, or API endpoint.

**Resolution**:

1. Verify you're signed in to the correct organization (check the org switcher in the top bar).
2. Confirm your role has the required permission. See [User Roles](../getting-started/user-roles.md).
3. Check if the resource belongs to a different tenant — cross-tenant access is blocked by design.
4. Ask your admin to verify your role assignment in **Administration → User Management**.

### Role change not applied

**Symptom**: Promoted to Admin but still seeing User-level features.

**Resolution**:

1. Role changes take effect on the next session. Sign out and sign back in.
2. Clear browser cache and cookies.
3. Verify the role change was saved (check the user list in admin panel).
4. If using SSO, role may be mapped from identity provider — check SAML attribute mapping.

### Can't see an initiative or project

**Symptom**: Initiative visible to colleagues but not to you.

**Resolution**:

1. Confirm you're in the correct organization.
2. Check if the initiative is restricted to specific users or groups.
3. Verify your role includes `initiatives:read` permission.
4. The initiative may be in a status (e.g., `draft`) that your role cannot view.

### API returns 403 with valid token

**Symptom**: API requests return 403 even though authentication succeeds.

**Resolution**:

1. Check the `X-Tenant-ID` header matches your organization.
2. Verify the JWT includes the required permission claim.
3. Confirm the resource exists and belongs to your tenant.
4. Review the API endpoint documentation for role requirements.

## Permissions by role

| Action | Viewer | User | Admin | Executive |
|--------|--------|------|-------|-----------|
| View initiatives | ✓ | ✓ | ✓ | ✓ |
| Create initiatives | — | ✓ | ✓ | ✓ |
| Delete initiatives | — | — | ✓ | ✓ |
| Approve business cases | — | — | ✓ | ✓ |
| Manage users | — | — | ✓ | — |
| Configure SSO | — | — | ✓ | — |
| View audit logs | — | — | ✓ | ✓ |

## Cross-tenant isolation

ValuePact enforces strict tenant isolation. Users can only:

- View resources in their assigned tenant(s)
- Switch between tenants they are members of
- Never access resources in other tenants, even with direct URLs

!!! warning "Isolation is absolute"
    There is no mechanism to share resources across tenants. Use a single tenant for cross-organizational collaboration.

## Escalation

For persistent permission issues:

1. Document the exact page, action, and error message.
2. Include your email, role, and organization name.
3. Contact support@valuepact.ai.

## Related pages

- [Getting Started → User Roles](../getting-started/user-roles.md)
- [Administration → Permissions](../administration/user-management/permissions.md)
- [Administration → Role Management](../administration/role-management/index.md)
