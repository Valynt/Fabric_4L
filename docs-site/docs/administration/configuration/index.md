---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Configuration

Configuration controls how ValuePact looks, feels, and behaves for your tenant. Admins manage branding, custom fields, workflows, and notifications from a single surface.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Content Admin</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Review of [Administration Overview](../index.md)
- Decision on which configuration changes require stakeholder sign-off

## Configuration areas

| Area | What it controls | Path |
|------|-----------------|------|
| Branding | Logo, colors, custom domain, email templates | **Configuration** > **Branding** |
| Custom Fields | Data model extensions and validation | **Configuration** > **Custom Fields** |
| Workflows | Status maps, transitions, approval gates | **Configuration** > **Workflows** |
| Notifications | Channels, templates, frequency, digests | **Configuration** > **Notifications** |

## Change impact

Configuration changes apply immediately to the tenant. There is no separate staging environment.

!!! warning "Production impact"
    Publishing a workflow or changing a custom field can affect in-flight records. Coordinate changes during low-usage windows.

## Step-by-step: review current configuration

1. Navigate to **Admin** > **Configuration**.
2. Select an area from the left sidebar.
3. Review the active settings.
4. Click **History** to see past changes and who made them.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | All configuration areas | Organization |
| Tenant Admin | All configuration areas | Organization |
| Content Admin | Branding, custom fields, notifications, workflows | Organization |
| Analyst | View-only on branding and notifications | Organization |
| Viewer | View-only on branding | Organization |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Configuration history is retained for 90 days.

<span class="vp-badge vp-badge--limit">Limit</span> Only one user should edit a configuration area at a time to avoid collisions.

<span class="vp-badge vp-badge--limit">Limit</span> Custom domain setup requires DNS verification and can take up to 24 hours.

## Troubleshooting

??? question "Issue: configuration change not reflected in the UI"
    **Cause:** Browser cache or CDN propagation delay.
    **Resolution:** Hard-refresh the browser. Wait up to 10 minutes for asset caching to clear.

??? question "Issue: cannot edit a configuration area"
    **Cause:** Another admin has the area locked, or your role lacks permission.
    **Resolution:** Check the lock indicator in the UI. Confirm your role includes the required permission.

## Related pages

- [Branding](branding.md)
- [Custom Fields](custom-fields.md)
- [Workflows](workflows.md)
- [Notifications](notifications.md)
- [Workflow Management](../../workflow-management/index.md)

## Escalation path

For configuration changes causing tenant-wide issues:

1. Revert the change using **History** > **Rollback** if available.
2. If rollback is unavailable, document the previous state and manually restore settings.
3. File a support ticket with severity **High**.
4. Escalate to `#valuepact-ops` if the issue affects login, SSO, or data access.
