---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Branding

Branding lets you align ValuePact with your organization's visual identity. You can customize the logo, color palette, custom domain, and email templates.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Content Admin</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Logo file in PNG or SVG format
- Access to your organization's DNS settings for custom domain setup

## Logo

1. Go to **Admin** > **Configuration** > **Branding**.
2. Under **Logo**, click **Upload**.
3. Select a PNG or SVG file.
4. Preview the logo in the header and email template.
5. Click **Save**.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum file size is 2 MB. Recommended dimensions: 200x40 pixels.

## Colors

You can customize the primary and accent colors used in the UI.

1. Open **Configuration** > **Branding**.
2. Under **Colors**, click the color swatch next to **Primary**.
3. Enter a HEX code or use the color picker.
4. Repeat for **Accent**.
5. Click **Save**.

The preview updates in real time. Changes apply on the next page load for all users.

## Custom domain

A custom domain lets users access ValuePact from a URL such as `value.yourcompany.com`.

### Step-by-step: configure a custom domain

1. Go to **Configuration** > **Branding** > **Custom Domain**.
2. Enter your domain name.
3. Copy the DNS records displayed (CNAME and TXT for verification).
4. Add the records to your DNS provider.
5. Click **Verify DNS**.
6. Once verified, enable **Force HTTPS**.

!!! warning "DNS propagation"
    DNS changes can take up to 24 hours. Do not delete the verification record after setup.

## Email templates

Email templates control the look of invitations, notifications, and digests.

1. Go to **Configuration** > **Branding** > **Email Templates**.
2. Select a template: **Invite**, **Notification**, or **Digest**.
3. Edit the subject line and body text.
4. Use available variables such as `{{user_name}}` and `{{tenant_name}}`.
5. Click **Preview** to send a test email.
6. Click **Save**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Manage all branding settings | Organization |
| Tenant Admin | Manage all branding settings | Organization |
| Content Admin | Manage logo, colors, and email templates | Organization |
| Analyst | View branded UI | Organization |
| Viewer | View branded UI | Organization |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Only one custom domain per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Email template subject lines cannot exceed 200 characters.

<span class="vp-badge vp-badge--limit">Limit</span> Color contrast is validated for accessibility. Low-contrast combinations are rejected.

## Troubleshooting

??? question "Issue: logo appears blurry"
    **Cause:** The uploaded file is too small or in a raster format scaled beyond its resolution.
    **Resolution:** Upload an SVG for crisp rendering at all sizes. If using PNG, ensure it is at least 400x80 pixels.

??? question "Issue: custom domain shows a certificate error"
    **Cause:** HTTPS was enabled before DNS fully propagated, or the CNAME is incorrect.
    **Resolution:** Verify the CNAME record points to the correct target. Wait for DNS propagation, then toggle HTTPS off and on.

??? question "Issue: email template variables not rendering"
    **Cause:** A variable name is misspelled or unsupported for the selected template.
    **Resolution:** Use only the variables listed in the template sidebar. Variable names are case-sensitive.

## Related pages

- [Configuration Overview](index.md)
- [Custom Fields](custom-fields.md)
- [Notifications](notifications.md)
- [Workflows](workflows.md)

## Escalation path

For branding issues affecting user trust or access:

1. Revert to the default logo and colors from **Branding** > **Reset Defaults**.
2. If the custom domain is broken, temporarily use the default domain.
3. File a support ticket with screenshots and domain details.
4. Escalate to `#valuepact-ops` if HTTPS or domain verification fails repeatedly.
