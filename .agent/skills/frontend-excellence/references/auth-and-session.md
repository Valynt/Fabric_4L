# Auth & Session Handling

**Destination:** Production-grade authentication and authorization on top of a prototype that almost certainly has none: token flows, RBAC, and secure session/cookie handling.

## Steps

1. **Choose the auth foundation.** If the repo uses Clerk (`apps/web` + `.claude/skills/clerk-*`), follow those skills (custom-ui, webhooks, testing). Otherwise pick an OIDC/OAuth2 provider with a maintained SDK.
2. **Token strategy.** Issue short-lived access tokens + long-lived refresh tokens. Never store sensitive tokens in localStorage (XSS-readable). Prefer `httpOnly` Secure `SameSite` cookies for browser sessions; keep refresh tokens out of JS reach.
3. **RBAC.** Encode roles/claims in the token or derive from server state; enforce on the backend for every request, never trust client-side checks alone. Map UI gates to the same roles.
4. **Session lifecycle.** Login → silent refresh → expiry → logout must be wired end-to-end and tested, including 401-refresh-retry logic in the frontend API client.
5. **Tenant isolation.** Every data access is scoped by `tenant_id` from authenticated context. Do not accept a tenant ID from the request body.
6. **Secure cookies.** `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict`), explicit `Path`/`Domain`, sensible `Max-Age`. No session cookie without `Secure` in production.
7. **Human-in-the-loop escape hatches.** For sensitive agentic actions, require explicit user confirmation (see `checklists/agentic-guardrails.md`).

## Dev-Auth Guardrails

The repo forbids dev-auth bypass flags in production (`DEV_AUTH_BYPASS`, `ALLOW_INSECURE_DEV_AUTH_BYPASS`, etc.). Never enable these in prod builds; `ProductionSafetyValidator` gates startup on them.

## Common Failure

**SameSite/Cookie mismatch between localhost and prod domain.** The login works on `localhost` but the session cookie is dropped in production because `Secure` + `SameSite` were configured for dev only, or the cookie `Domain` doesn't match the deployed origin. Test the full flow against a staging URL with the production cookie settings.

## Verification

```bash
pnpm --dir apps/web run test:prod-auth-bypass
pnpm --dir apps/web run test:e2e:golden:j1:canonical   # full auth journey
# Security: cross-tenant read fails 403, unauthenticated rejected 401
pytest tests/security -m tenant_boundary
```