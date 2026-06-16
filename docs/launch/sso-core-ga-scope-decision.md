# SSO/OIDC Core GA Scope Decision

- **Date (UTC):** 2026-06-16
- **Status:** Pending executive/launch-owner decision
- **Owner:** Identity owner / Product / Release Management
- **Related blockers:** P0-003 (`docs/launch/launch-blocker-register.md`)
- **Related waivers:** WVR-2026-06-15-003 (`docs/launch/accepted-risk-waivers-2026-06-15.md`)

## Decision to be made

Is **enterprise SSO/OIDC provider integration** a contracted or promised requirement for Core GA?

## Option A — Enterprise SSO/OIDC IS in Core GA scope

- **Risk level:** High
- **P0-003 status:** Blocks Core GA until real enterprise IdP evidence is attached.
- **Required evidence before launch:**
  - Provider metadata and redirect URI/DNS alignment.
  - Successful login and logout flow proof.
  - Failed-login handling proof.
  - Group/role to tenant mapping validation.
  - Redacted audit event sample.
- **Fallback:** Clerk-managed authentication remains available during any SSO outage, but enterprise SSO must be validated for launch.
- **Target:** Complete validation in staging/production-like environment before Core GA.

## Option B — Enterprise SSO/OIDC is NOT in Core GA scope

- **Risk level:** Medium (acceptable residual risk)
- **P0-003 status:** Scoped out of Core GA; deferred to paid/enterprise GA.
- **Core GA auth:** Clerk-managed authentication is the supported path.
- **Required actions:**
  - Record the formal scope reduction here and in the launch-blocker register.
  - Confirm Clerk fallback is documented and monitored.
  - Set a target date for enterprise SSO validation (recommended: within 30–60 days of Core GA or before paid/enterprise GA, whichever is earlier).
- **Target:** Validate enterprise IdP before paid/enterprise GA launch.

## Decision

**Option B — Enterprise SSO/OIDC is NOT required for Core GA.**

Enterprise SSO/OIDC validation is deferred to paid/enterprise GA. Clerk-managed authentication is the supported Core GA auth path.

- **Decision date (UTC):** 2026-06-16
- **Target for enterprise SSO validation:** Before paid/enterprise GA launch (recommended within 60 days of Core GA).
- **Fallback:** Clerk-managed authentication remains in place; if enterprise IdP issues occur after future enablement, disable the IdP route and fall back to Clerk without breaking auth fail-closed behavior.

| Function | Name | Date | Decision |
|---|---|---|---|
| Product owner | _TBD_ | | Option B |
| Identity owner | _TBD_ | | Option B |
| Security owner | _TBD_ | | Option B |
| Release Management | _TBD_ | | Option B |

> **Note:** Names and countersignatures must be filled by the responsible owners before this decision is authoritative.
