---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Single Sign-On (SSO)

SSO lets users authenticate through your corporate identity provider. ValuePact supports SAML 2.0, OpenID Connect (OIDC), and SCIM provisioning.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Tenant Admin or Super Admin role
- Administrative access to your identity provider
- Verified domain ownership

## Supported protocols

| Protocol | Use case | Provisioning |
|----------|----------|-------------|
| SAML 2.0 | Enterprise SSO with XML metadata | Manual or SCIM |
| OIDC | Modern token-based SSO | Manual or SCIM |
| SCIM | Automated user and group sync | Requires SAML or OIDC |

## Domain verification

Before enabling SSO, you must verify ownership of your email domain.

1. Go to **Admin** > **Security** > **SSO**.
2. Click **Add Domain**.
3. Enter your domain (e.g., `yourcompany.com`).
4. Copy the TXT record value.
5. Add the TXT record to your DNS provider.
6. Click **Verify**.

!!! warning "DNS timing"
    Domain verification can take up to 24 hours depending on DNS propagation.

## SAML configuration

### Step-by-step: configure SAML

1. Open **Security** > **SSO** > **SAML**.
2. Enter your **Identity Provider SSO URL**.
3. Upload or paste the **X.509 Certificate**.
4. Copy the **ValuePact Assertion Consumer Service (ACS) URL**.
5. Configure your identity provider with the ACS URL and entity ID.
6. Map identity provider attributes to ValuePact fields:
   - `email` → Email
   - `first_name` → First Name
   - `last_name` → Last Name
   - `groups` → Groups (optional)
7. Click **Test** and **Save**.

## OIDC configuration

### Step-by-step: configure OIDC

1. Open **Security** > **SSO** > **OIDC**.
2. Enter the **Issuer URL**.
3. Enter the **Client ID** and **Client Secret**.
4. Select the **Scopes** to request (typically `openid`, `profile`, `email`).
5. Map claims to ValuePact fields.
6. Click **Test** and **Save**.

## SCIM provisioning

SCIM automates user creation, updates, and deactivation.

1. Enable SCIM in **Security** > **SSO** > **SCIM**.
2. Copy the **SCIM Base URL** and **Bearer Token**.
3. Configure your identity provider with these values.
4. Map identity provider groups to ValuePact groups.
5. Set the provisioning scope: **Users only** or **Users and Groups**.

<span class="vp-badge vp-badge--limit">Limit</span> SCIM provisioning rate is limited to 100 operations per minute.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Configure SSO and SCIM | Organization |
| Tenant Admin | Configure SSO and SCIM | Organization |
| Content Admin | View SSO configuration | Organization |
| Analyst | Cannot configure SSO | — |
| Viewer | Cannot configure SSO | — |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Only one active SSO connection per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Domain verification supports up to 10 domains per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> SSO certificates must be rotated before expiry. Expired certificates block login.

## Troubleshooting

??? question "Issue: SAML login fails with certificate error"
    **Cause:** The X.509 certificate is expired or malformed.
    **Resolution:** Download the current certificate from your identity provider and re-upload it. Verify the certificate is in PEM format.

??? question "Issue: SCIM users not appearing"
    **Cause:** The bearer token is invalid, or the group mapping filter is too restrictive.
    **Resolution:** Regenerate the bearer token in **SCIM** settings. Review the group mapping filter.

??? question "Issue: domain verification keeps failing"
    **Cause:** The TXT record was added to the wrong DNS zone, or propagation is incomplete.
    **Resolution:** Confirm the DNS host and record value match exactly. Wait 24 hours and retry.

## Related pages

- [Security Overview](index.md)
- [Authentication](authentication.md)
- [MFA](mfa.md)
- [Audit Logs](audit-logs.md)
- [Groups](../user-management/groups.md)

## Escalation path

For SSO outages or certificate emergencies:

1. Verify the certificate expiry in **Security** > **SSO**.
2. If the certificate is expired, upload the new certificate immediately.
3. If users are still locked out, temporarily disable SSO enforcement to allow password login.
4. File a support ticket with severity **Critical**.
5. Escalate to `#security-ops` if the outage affects all users.
