---
skill_id: login-signup-ux
name: login-signup-ux
version: 1.0.0
description: Best practices for designing, building, and testing login and signup flows with strong UX, accessibility, security, and OAuth integration
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Login & Signup UX Skill

Comprehensive guide for implementing production-grade authentication UX. Covers signup flow design, login experience, error handling, accessibility, security testing edge cases, and OAuth integration with Vite/SPA frontends.

## Sources

- [Authgear: Login & Signup UX Guide (2025)](https://www.authgear.com/post/login-signup-ux-guide)
- [Frugal Testing: Login Auth Edge Cases](https://www.frugaltesting.com/blog/testing-login-authentication-flows-edge-cases-people-forget)
- [OAuth Login Flow with Vite](https://dev.to/digitalrisedorset/oauth-login-flow-with-vite-n98)

---

## 1. Core UX Principles

Every login/signup flow must balance ease-of-use, security, and trust.

- **Security with Usability**: Balance security measures (password rules, 2FA) with convenience. Prefer phishing-resistant but frictionless flows (e.g., passkeys).
- **Clarity**: Label actions unambiguously ("Create Account" vs "Log In"). Users should never wonder whether they are signing up or logging in.
- **Minimize Cognitive Load**: Don't make users recall unnecessary info. Support password managers, allow paste, offer magic-link or social login options. Per WCAG 2.2, login must not rely on memorization without alternatives.
- **Inclusivity**: Use plain language (~Grade 8 reading level). Ensure screen reader compatibility, high contrast, and no reliance on color alone for errors.
- **Mobile-First**: Big tap targets, responsive layout, leverage SMS autofill, device biometrics, and OTP auto-detection.
- **Trust Signals**: SSL indicators, privacy statement links, on-brand white-labeled login screens. Add notes like "We'll never post to your Facebook" near social login buttons.
- **Data-Informed Iteration**: Monitor signup conversion, login success rate, password reset volume. Iterate based on analytics and user feedback.

---

## 2. Signup Flow Best Practices

### Keep It Simple

- Ask for minimum info upfront (email/phone + password). Collect profile details later via progressive profiling.
- Use email as the login identifier unless a public username is required.
- Remove "Confirm Password" field; use a "Show Password" toggle instead.
- Show password complexity requirements inline and validate in real time (green checkmarks as rules are met).
- Offer social sign-up ("Sign up with Google/Apple") to streamline the process. Follow each provider's button branding guidelines.

### Progressive Onboarding

- If many fields are needed, use a multi-step wizard with progress indicator ("Step 2 of 3").
- Keep step 1 minimal (email + password) so the account is created even if the user drops off.
- Consider phone number sign-up for mobile-first or developing-region audiences.
- Consider deferring email verification: let users in immediately, verify in background, lock some features until verified.
- After sign-up, log the user in automatically. Show a welcome message or onboarding tour. Never redirect back to the login screen.

### Form UI Details

- **Strong CTAs**: Prominent, contrasting "Sign Up" or "Create Account" button. Avoid ambiguous "Continue".
- **Microcopy**: Set expectations ("Join [App] - it's free and takes 30 seconds!"). Add privacy reassurance near social login buttons.
- **Error Prevention**: Use `type="email"` for email keyboard on mobile. Validate on blur ("That doesn't look like a valid email").
- **GDPR Consents**: Keep consent text brief. Newsletter opt-in should be unchecked by default.
- **Confirmation**: Show clear success feedback. If email verification is sent, display "Check your inbox" with a "Resend email" option.

---

## 3. Login Flow Best Practices

### Make Login Quick and Painless

- **Skip login if already authenticated**: If a valid session/token exists, go straight to the app.
- **Prominent login options**: Show the most common method first (email/password or social login depending on audience).
- **"Remember me" / device trust**: Include "Keep me signed in" checkbox on web. On mobile, keep users logged in by default. For MFA, offer "Remember this device for 30 days".
- **Password input UX**: Provide show/hide toggle, never disable paste, use `autocomplete="current-password"` and `autocomplete="username"` so password managers work.
- **Fast error feedback**: Show errors instantly on submission. Do not clear the email field on failure. After multiple failures, gently suggest "Perhaps you don't have an account? [Sign up]".
- **Account recovery**: Make "Forgot password?" easy to find (below the password field). The reset flow should be email-click + new-password-form, nothing more. Include a "Need help logging in?" link.

### Speed & Feedback

- Show a spinner or loading bar during API calls. Never leave a disabled form with no feedback.
- For magic link flows: display "Email sent! Check your inbox." with resend and change-email options.
- On successful login, show a brief success indicator ("Success! Redirecting...") before navigating.

### Account Security vs. UX

- **2FA/MFA**: Let users choose their method (SMS, TOTP, push, security key). Use plain language ("Enter the 6-digit code from your Authenticator app"). Allow skipping on trusted devices.
- **Security notifications**: Notify on new-device login ("New login from Chrome on Windows. Was this you?").
- **Rate limiting & lockouts**: Communicate clearly ("Too many attempts. Try again in 5 minutes or reset your password."). Email the user proactively about failed attempts.

---

## 4. Error Handling & Recovery

### Error Message Guidelines

- **Clarity**: State what went wrong in plain language ("We couldn't find an account with that email").
- **Politeness**: Don't blame the user. "Incorrect password. Please try again." not "You entered the wrong password!".
- **Precision**: For consumer apps, precise messages ("No account found for that email") usually outweigh the minimal enumeration risk. Use a generic message on first failure, add hints on subsequent failures.
- **Constructive Advice**: Always pair errors with a next step ("Incorrect password. [Reset it here] or try again."). Never leave a dead-end.
- **Field-level errors**: Display errors next to the problematic field (red outline, shake animation, message below the input).

### Error-to-Recovery Mapping

| Error Scenario | UX Recovery |
|---|---|
| Wrong password | "Incorrect password. [Reset password] or try again." |
| Unknown email | "No account with that email. [Sign up] or try a different email." |
| Account locked | "Account locked. Try again in X minutes or [contact support]." |
| Expired reset link | "This link has expired. [Request a new one]." |
| Expired OTP | "Code expired. [Resend code]." |
| Social login failure | "Could not connect to Google. [Try again] or use email/password." |

### Microcopy That Delights

- **Password strength**: Live meter with text ("Add a symbol to make it stronger").
- **2FA prompts**: "Enter the 6-digit code sent to your phone ending in **1234**."
- **Success**: "Welcome to [App]!" on signup. "You've been logged out. See you soon!" on logout.
- **Loading**: Show useful tips during account setup ("Did you know you can connect your Google account later?").
- **Error humor (cautiously)**: "Passwords are hard! Try again or reset it if you can't recall."

---

## 5. Accessibility Checklist (A11y)

- [ ] Every input has a visible `<label>` (not just placeholder text). Use `<label for="...">`.
- [ ] Use `autocomplete="username"` and `autocomplete="current-password"` attributes.
- [ ] Never disable paste on password or OTP fields.
- [ ] Keyboard navigation works: logical tab order, visible focus states, no focus traps.
- [ ] Errors are announced to screen readers via `role="alert"` or ARIA live regions.
- [ ] Link errors to fields with `aria-describedby`.
- [ ] Error indicators use more than just color (icons, text, borders).
- [ ] Minimum 4.5:1 contrast ratio for all text including error messages.
- [ ] Decorative icons use `aria-hidden="true"`. Informational images have alt text.
- [ ] Session timeouts warn the user and allow continuation.
- [ ] CAPTCHAs have accessible alternatives (reCAPTCHA v3 invisible, audio CAPTCHA, or email verification).
- [ ] Biometric login always has a fallback (PIN, password). Clearly instruct ("Use Touch ID or press cancel to use your password").
- [ ] Test the entire flow with a screen reader (VoiceOver/NVDA) and keyboard-only navigation.
- [ ] Test at 200% zoom - form must remain functional and readable.

---

## 6. Testing Edge Cases

These scenarios are commonly missed in QA and cause production incidents.

### Password Recovery

- Expired reset links show a clear message and re-request option
- Multiple rapid reset requests don't cause duplicate emails or race conditions
- Reset emails don't land in spam (check SPF/DKIM/DMARC)
- Weak or reused passwords are rejected during reset

### Account Lockout

- Lockout triggers after N failures with clear cooldown messaging
- Error messages don't reveal whether the username exists
- Recovery via email, SMS, or support contact all work
- Behavior is correct across shared accounts and multiple devices

### Session Management

- Session expiration during inactivity redirects gracefully
- Concurrent login from multiple devices behaves correctly (last-writer-wins, or multi-session)
- Browser refresh preserves auth state
- Logout invalidates sessions across all open tabs

### MFA Challenges

- Delayed or missing OTP delivery has a "Resend" option
- Incorrect OTP attempts show remaining tries
- Time-based token expiration is handled (clock skew tolerance)
- MFA bypass attempts during network issues are blocked

### Account Status Variations

- Disabled/suspended users see an appropriate message (not a generic error)
- Unverified email accounts have limited access with a prompt to verify
- Role-based access restrictions are enforced post-login
- Profile changes (name, email) don't break login

### Social Login Failures

- Expired OAuth tokens trigger re-authentication gracefully
- Revoked permissions show a clear re-authorization prompt
- Provider downtime falls back to email/password with a message
- Mismatches between social profile data and app metadata are handled

### Security Edge Cases

- **SQL injection**: All login inputs are parameterized, never concatenated into queries
- **HTTPS enforcement**: Login pages force HTTPS redirect; cookies have `Secure` flag
- **Brute force**: Rate limiting, CAPTCHA triggers, IP-based blocking, and alerting
- **Session tokens**: `HttpOnly` and `Secure` flags set; tokens regenerated after login; proper invalidation on logout

### Performance

- Login response time < 2s under normal load
- Test under peak traffic and degraded network conditions
- Validate concurrent login handling, database load, and dependency failures

---

## 7. OAuth Flow with Vite / SPA Frontends

Vite (and similar SPA frameworks) run entirely in the browser and **cannot** securely handle JWTs server-side or set HTTP-only cookies. This requires a specific architecture.

### Architecture Pattern

```
[Vite SPA] --redirect--> [OAuth Provider (Google, etc.)]
                              |
                          callback
                              |
                    [Auth Server (Express/Passport)]
                              |
                      sets JWT as HTTP-only cookie
                              |
                    redirect back to [Vite SPA]
```

### Key Requirements

1. **Auth Bridge Service**: A thin Express (or equivalent) server that:
   - Implements the OAuth strategy (e.g., Google via Passport)
   - Receives the JWT after successful authentication
   - Sets it as a `Secure`, `HttpOnly`, `SameSite` cookie
   - Redirects the user back to the Vite frontend

2. **Shared Parent Domain**: The auth-bridge must share the same parent domain as the Vite host.
   - Example: `auth.example.com` sets a cookie for `.example.com`, which is sent to `app.example.com`.

3. **Token Never Exposed to Client JS**: The JWT lives in an HTTP-only cookie. The Vite app never reads or stores the token in `localStorage` or JS memory.

4. **Session Sync**: After redirect, the Vite app calls a `/me` or `/session` endpoint (with cookies) to get the authenticated user profile.

### Implementation Checklist

- [ ] OAuth provider configured (client ID, secret in env vars, redirect URIs registered)
- [ ] Auth server implements OAuth callback, JWT creation, and cookie setting
- [ ] Cookie flags: `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict`)
- [ ] Cookie domain set to shared parent domain (e.g., `.example.com`)
- [ ] Vite app redirects to auth server for login, not directly to OAuth provider
- [ ] After redirect back, Vite app calls authenticated `/me` endpoint to hydrate user state
- [ ] CSRF protection in place (SameSite cookie + CSRF token for state-changing requests)
- [ ] Logout endpoint clears the cookie and revokes the session server-side
- [ ] Error handling for OAuth failures (denied consent, provider downtime, token expiry)
- [ ] Local development setup works (e.g., `localhost` domain sharing or proxy config)

---

## 8. Implementation Checklist (Summary)

### Signup

- [ ] Minimal fields (email + password or social only)
- [ ] Inline real-time validation with password strength meter
- [ ] Show/hide password toggle (no "Confirm Password" field)
- [ ] Social login buttons with provider branding guidelines
- [ ] Multi-step wizard if >3 fields required
- [ ] Auto-login after signup with welcome screen
- [ ] GDPR consent checkbox (unchecked by default)

### Login

- [ ] Skip login screen if session is valid
- [ ] "Remember me" / device trust option
- [ ] `autocomplete` attributes on all fields
- [ ] Show/hide password toggle, paste enabled
- [ ] "Forgot password?" link below password field
- [ ] Loading indicator during authentication
- [ ] Error messages are specific, polite, and constructive
- [ ] Do not clear email field on error

### Accessibility

- [ ] All items in Section 5 checklist pass
- [ ] Tested with screen reader + keyboard-only
- [ ] Tested at 200% zoom

### Security & Testing

- [ ] All edge cases in Section 6 have test coverage
- [ ] OAuth flow follows Section 7 architecture (if applicable)
- [ ] Rate limiting and lockout messaging verified
- [ ] Session management tested across tabs, devices, and browsers

---

## When to Use This Skill

- Building a new login or signup page
- Auditing an existing auth flow for UX, accessibility, or security gaps
- Writing E2E or integration tests for authentication
- Integrating OAuth/social login into a Vite or SPA frontend
- Preparing an auth flow for production launch or compliance review
