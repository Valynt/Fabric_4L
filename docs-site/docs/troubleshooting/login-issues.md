---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Login Issues

Resolve sign-in problems including SSO failures, MFA issues, and session errors.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- Valid invitation or existing account
- Supported browser (Chrome, Firefox, Safari, Edge — latest 2 versions)

## Common issues

### Can't sign in with email and password

**Symptom**: Error "Invalid credentials" or "Authentication failed"

**Resolution**:

1. Verify you're using the correct email address (check for typos).
2. Use the **Forgot Password** link to reset your password.
3. Check your email spam folder for the reset link.
4. Ensure Caps Lock is off when entering your password.
5. Try an incognito/private browser window to rule out extension conflicts.

### SSO sign-in fails

**Symptom**: Redirect loop, "SSO configuration error", or blank page after identity provider

**Resolution**:

1. Check [status.valuepact.ai](https://status.valuepact.ai) for SSO provider incidents.
2. Verify your organization's SSO is still enabled in **Administration → Security → SSO**.
3. Confirm your domain is verified and not expired.
4. Clear browser cookies for `valuepact.ai` and your identity provider.
5. Try a different browser or incognito mode.
6. Ask your admin to re-authenticate the SSO connection.

!!! warning "Domain verification expiry"
    SSO domain verification expires after 90 days of inactivity. Re-verify in the admin panel.

### MFA code not working

**Symptom**: "Invalid MFA code" or "MFA verification failed"

**Resolution**:

1. Ensure your device's clock is synchronized (TOTP codes are time-sensitive).
2. Wait for a new code to generate (codes change every 30 seconds).
3. Use a backup code if available.
4. Contact your admin to temporarily disable MFA if you lost access to your authenticator.
5. Re-enroll MFA after regaining access.

### Invitation link expired

**Symptom**: "Invitation expired" or "Invalid invitation token"

**Resolution**:

1. Invitation links expire after 7 days.
2. Ask your admin to send a new invitation.
3. Check that the invitation email hasn't been forwarded (links are single-use).

### Session keeps expiring

**Symptom**: Signed out unexpectedly, "Session expired" message

**Resolution**:

1. Sessions expire after 24 hours of inactivity (configurable by admin).
2. Enable **Remember me** during sign-in for extended sessions (up to 7 days).
3. Check if your browser is clearing cookies on exit.
4. Corporate proxies or VPNs may drop sessions — try without VPN.

## Browser compatibility

| Browser | Minimum Version | Notes |
|---------|----------------|-------|
| Chrome | 120+ | Recommended |
| Firefox | 121+ | Fully supported |
| Safari | 17+ | Fully supported |
| Edge | 120+ | Fully supported |

!!! tip "Clearing cache"
    If login issues persist across browsers, clear cache and cookies for `valuepact.ai` completely.

## Escalation

If issues persist after following the steps above:

1. Gather your email, organization name, browser version, and error message.
2. Contact support@valuepact.ai with subject "Login Issue — [Your Org]".
3. For P1 (complete inability to access platform), call the emergency hotline.

## Related pages

- [Administration → Authentication](../administration/security/authentication.md)
- [Administration → SSO](../administration/security/sso.md)
- [Administration → MFA](../administration/security/mfa.md)
- [FAQ → Security FAQ](../faq/security-faq.md)
