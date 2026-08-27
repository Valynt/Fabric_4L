sa# Clerk Configuration for ValuePact

> Canonical reference for Clerk authentication integration.
> For agent orchestration rules, see `.windsurf/AGENTS.md`.

---

## Architecture Overview

```txt
Clerk handles:
  authentication, sessions, organizations, invites, MFA, SSO

ValuePact handles:
  tenant mapping, account access, RBAC, entitlements, RLS, audit logs

Infisical stores:
  Clerk keys, webhook secrets, JWT verification config, per-env auth config
```

Clerk session tokens are JWTs sent to the backend. The API gateway verifies
them with `CLERK_JWKS_URL` or a local/testing-only `CLERK_PINNED_JWT_PEM`, then
re-wraps the identity into Fabric's signed internal auth envelope.

---

## What's Already Implemented

The codebase already contains a mature dual-auth architecture (legacy OIDC + Clerk Phase 2). Key files:

| Concern | File |
|---|---|
| Clerk provider (lazy-loaded) | `apps/web/src/main.tsx` |
| Clerk config & env defaults | `apps/web/src/auth/clerkConfig.ts` |
| Token bridge to API client | `apps/web/src/auth/ClerkAuthBridge.tsx` |
| API client Bearer injection | `apps/web/src/api/client.ts` |
| Route guard (Clerk auth + org) | `apps/web/src/components/routing/RequireClerkAuth.tsx` |
| Route guard (org only) | `apps/web/src/auth/RequireOrganization.tsx` |
| Unified route guard | `apps/web/src/components/routing/UnifiedRouteGuard.tsx` |
| Tenant membership hook | `apps/web/src/hooks/useTenantMembership.ts` |
| Sign-in page | `apps/web/src/pages/ClerkSignIn.tsx` |
| Sign-up page | `apps/web/src/pages/ClerkSignUp.tsx` |
| Workspace/org picker | `apps/web/src/pages/SelectOrganization.tsx` |
| Onboarding page | `apps/web/src/pages/Onboarding.tsx` |
| Router with Clerk routes | `apps/web/src/shell/router.tsx` |
| Backend Clerk config | `services/api/app/core/clerk_config.py` |
| Backend JWT verification | `services/api/app/core/clerk_verifier.py` |
| Webhook handler | `services/api/app/routers/clerk_webhooks.py` |
| Auth directory / tenant mapping | `services/api/app/core/auth_directory.py` |
| Internal envelope JWTs (L1-L6) | `services/api/app/core/internal_envelope_issuer.py` |
| Database tables (migration) | `services/api/migrations/versions/0001_clerk_auth_baseline.sql` |

---

## 1. Create Clerk Applications Per Environment

Create separate Clerk instances for:

```txt
ValuePact Dev
ValuePact Staging
ValuePact Production
```

Map them to Infisical:

```txt
Clerk Dev         → Infisical dev
Clerk Staging     → Infisical staging
Clerk Production  → Infisical prod
```

Do **not** reuse development keys in production.

Recommended domains:

```txt
dev:      http://localhost:3001
staging:  https://staging.valuepact.ai
prod:     https://www.valuepact.ai
```

---

## 2. Enable Clerk Organizations

In the Clerk Dashboard, enable **Organizations**.

For ValuePact:

```txt
Clerk Organization = ValuePact Tenant / Workspace
```

Example mapping:

```txt
Clerk organization:
  org_id: org_abc123
  slug: acme
  name: Acme Manufacturing

ValuePact tenant:
  id: ten_7f92
  clerk_org_id: org_abc123
  slug: acme
  name: Acme Manufacturing
```

Clerk positions Organizations for B2B/multi-tenant SaaS and supports organization membership, roles, and permissions. See [Clerk docs](https://clerk.com/).

ValuePact URLs continue using the tenant/workspace slug:

```txt
/t/acme/accounts/acc_123/intelligence/signals
/t/acme/accounts/acc_123/studio/calculator
/t/acme/governance/formulas
```

But backend authorization resolves using the verified Clerk organization ID, not just the URL slug.

---

## 3. Configure Roles and Permissions in Clerk

Start simple.

Recommended Clerk org roles:

```txt
org:owner
org:admin
org:member
org:guest
org:value_engineer
org:sales_leader
org:account_executive
org:customer_success
org:viewer
org:auditor
```

Recommended Clerk permissions:

```txt
org:accounts:read
org:accounts:write

org:intelligence:read
org:intelligence:review_signals
org:intelligence:approve_signals

org:value_model:read
org:value_model:write
org:value_model:approve

org:evidence:read
org:evidence:attach
org:evidence:approve

org:calculator:read
org:calculator:write

org:business_case:read
org:business_case:generate
org:business_case:export

org:governance:read
org:governance:write
org:formulas:approve
org:benchmarks:manage

org:agents:run
org:agents:approve_actions

org:admin:manage_users
org:admin:manage_integrations
org:admin:manage_api_keys
```

The gateway normalizes Clerk's built-in organization roles before creating the
Fabric internal auth context:

```txt
org:admin / admin              -> tenant_admin
org:member / basic_member      -> analyst
org:guest / guest_member       -> read_only
```

Important boundary:

```txt
Clerk org permissions = coarse org-level permission hints
ValuePact DB policies = real tenant/account/resource authorization
```

Do not try to model every account-level permission only in Clerk. ValuePact needs its own authorization tables for account access, workflow state, entitlements, and audit.

---

## 4. Configure Sign-In, Sign-Up, and Redirect URLs

In Clerk Dashboard, configure allowed origins and redirects.

For local dev:

```txt
Allowed origins:
http://localhost:3001

Sign-in URL:   /sign-in
Sign-up URL:   /sign-up
After sign-in: /workspaces
After sign-up: /onboarding
```

For staging/prod:

```txt
Allowed origins:
https://staging.valuepact.ai
https://www.valuepact.ai

After sign-in: /workspaces
After sign-up: /onboarding
```

For ValuePact, send users to `/workspaces` after login so they choose their active tenant/org before entering account-scoped workflows.

---

## 5. Store Clerk Config in Infisical

Use these Infisical paths.

### `/apps/web`

Frontend-safe only:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_test_or_pk_live_dummy_xxx
VITE_CLERK_SIGN_IN_URL=/sign-in
VITE_CLERK_SIGN_UP_URL=/sign-up
VITE_CLERK_AFTER_SIGN_IN_URL=/home
VITE_CLERK_AFTER_SIGN_UP_URL=/onboarding
VITE_CLERK_JWT_TEMPLATE=fabric4l-api
```

Anything with `VITE_` is public in the browser.

Never put this in `/apps/web`:

```env
VITE_CLERK_SECRET_KEY=
VITE_CLERK_WEBHOOK_SIGNING_SECRET=
```

### `/shared/auth`

Backend/gateway auth config:

```env
CLERK_ISSUER=https://accounts.valuepact.ai
CLERK_JWT_AUDIENCE=fabric4l-api
CLERK_AUTHORIZED_PARTIES=https://www.valuepact.ai,https://app.valuepact.ai
CLERK_JWKS_URL=https://accounts.valuepact.ai/.well-known/jwks.json
```

### `/api-gateway`

Gateway-only secrets:

```env
CLERK_SECRET_KEY=
CLERK_WEBHOOK_SIGNING_SECRET=
FABRIC_AUTH_SIGNING_KEY=
FABRIC_AUTH_SIGNING_KID=gateway-k1
FABRIC_AUTH_PUBLIC_KEYS=[{"kid":"gateway-k1","public_pem":"-----BEGIN PUBLIC KEY-----..."}]
FABRIC_AUTH_ISSUER=fabric4l-gateway
FABRIC_AUTH_AUDIENCE=fabric4l-internal
FABRIC_AUTH_ENVELOPE_TTL_SECONDS=300
```

### `/layer1-ingestion` through `/layer6-benchmarks`

Downstream services should not need Clerk secrets if you choose **gateway-only Clerk verification**.

They need only the ValuePact internal auth verification key:

```env
FABRIC_AUTH_PUBLIC_KEYS=[{"kid":"gateway-k1","public_pem":"-----BEGIN PUBLIC KEY-----..."}]
FABRIC_AUTH_ISSUER=fabric4l-gateway
FABRIC_AUTH_AUDIENCE=fabric4l-internal
```

### `/webhooks`

```env
CLERK_WEBHOOK_SIGNING_SECRET=
```

Clerk webhook docs state the signing secret is available from the Clerk Dashboard webhook endpoint. See [Clerk webhooks](https://clerk.com/docs/guides/development/webhooks/overview).

---

## 6. Install Clerk in the React/Vite Frontend

From `apps/web`:

```bash
pnpm add @clerk/clerk-react
```

The Clerk provider is already integrated in `apps/web/src/main.tsx`:

```tsx
const clerkEnabled = isClerkAuthEnabled();
const clerkUrls = getClerkUrls();
const clerkPublishableKey = clerkEnabled ? getClerkPublishableKey() : "";

const ClerkProvider = clerkEnabled
  ? lazy(() =>
      import("@clerk/react").then((m) => ({ default: m.ClerkProvider }))
    )
  : null;
```

---

## 7. Add Sign-In and Sign-Up Routes

The sign-in and sign-up pages already exist:

- `apps/web/src/pages/ClerkSignIn.tsx`
- `apps/web/src/pages/ClerkSignUp.tsx`

They are wired into the router at:

```txt
/sign-in
/sign-up
```

See `apps/web/src/shell/router.tsx`.

---

## 8. Add Frontend Auth Guard

The `RequireClerkAuth` component already exists at `apps/web/src/components/routing/RequireClerkAuth.tsx`.

For tenant-scoped pages, the `RequireOrganization` guard exists at `apps/web/src/auth/RequireOrganization.tsx`.

---

## 9. Add `getToken()` to the API Client

The API client already attaches Clerk session tokens via `ClerkAuthBridge`:

```ts
// apps/web/src/auth/ClerkAuthBridge.tsx
setClerkTokenGetter(async (options) => {
  const template = options?.template ?? FABRIC_AUTH_TEMPLATE_NAME;
  return currentGetToken({
    template,
    skipCache: options?.skipCache,
  });
});
```

Usage in the API client (`apps/web/src/api/client.ts`):

```ts
if (isClerkAuthEnabled()) {
  const rawToken = await getClerkSessionToken();
  const safeToken = sanitizeBearerToken(rawToken);
  if (safeToken) {
    config.headers['Authorization'] = `Bearer ${safeToken}`;
  }
}
```

Create a Clerk JWT template named `fabric4l-api` with claims:

```json
{
  "aud": "fabric4l-api",
  "org_id": "{{org.id}}",
  "org_slug": "{{org.slug}}",
  "org_role": "{{org.role}}",
  "org_permissions": "{{org.permissions}}"
}
```

Keep claims small. Do not put account access lists or large permission maps in the token.

---

## 10. Gateway Verifies Clerk JWT

Gateway flow (already implemented in `services/api/app/core/clerk_verifier.py`):

```txt
1. Read Authorization: Bearer <Clerk JWT>
2. Verify token signature, issuer, audience, authorized party
3. Extract Clerk user ID and org ID
4. Resolve org ID → ValuePact tenant
5. Resolve Clerk user ID → ValuePact user
6. Load tenant membership
7. Build AuthContext
8. Sign internal auth envelope
9. Forward to L1-L6
```

Internal headers:

```txt
X-Fabric-Auth: <signed internal auth context>
X-Request-ID: <request-id>
```

Do not trust:

```txt
X-Tenant-ID
tenant_id from request body
tenant slug from URL
```

unless it matches the verified internal `AuthContext`.

---

## 11. Backend Tenant Mapping Tables

Tables are defined in `services/api/migrations/versions/0001_clerk_auth_baseline.sql`:

```sql
create table users (
  id uuid primary key,
  clerk_user_id text unique not null,
  email text,
  display_name text,
  created_at timestamptz not null default now()
);

create table tenants (
  id uuid primary key,
  clerk_org_id text unique not null,
  slug text unique not null,
  name text not null,
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table tenant_memberships (
  id uuid primary key,
  tenant_id uuid not null references tenants(id),
  user_id uuid not null references users(id),
  clerk_membership_id text unique,
  role text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  unique (tenant_id, user_id)
);

create table account_memberships (
  id uuid primary key,
  tenant_id uuid not null references tenants(id),
  account_id uuid not null,
  user_id uuid not null references users(id),
  access_level text not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, account_id, user_id)
);
```

Clerk tells you **who** the user is. ValuePact decides **what tenant/account/resource** they can touch.

---

## 12. Create Clerk Webhooks

Webhook endpoint:

```txt
POST https://api.valuepact.ai/internal/webhooks/clerk
```

For dev, use a tunnel if needed:

```txt
POST https://<your-ngrok-url>/internal/webhooks/clerk
```

Subscribe to:

```txt
user.created
user.updated
user.deleted
organization.created
organization.updated
organization.deleted
organizationMembership.created
organizationMembership.updated
organizationMembership.deleted
```

The webhook handler at `services/api/app/routers/clerk_webhooks.py` already:

- verifies webhook signature (Svix HMAC-SHA256)
- is idempotent via `clerk_webhook_events` table
- upserts users, tenants, and memberships
- deactivates removed memberships
- logs audit events

---

## 13. Add API Authorization Dependencies

After the gateway creates `AuthContext`, downstream services enforce permissions.

Example policy object (from spec):

```py
class AuthContext(BaseModel):
    user_id: UUID
    tenant_id: UUID
    clerk_user_id: str
    clerk_org_id: str
    roles: list[str]
    permissions: list[str]
    entitlements: list[str]
    request_id: str
```

Permission dependency:

```py
def require_permission(permission: str):
    async def dependency(request: Request):
        auth: AuthContext = request.state.auth
        if permission not in auth.permissions:
            raise HTTPException(status_code=403, detail={...})
        return auth
    return dependency
```

Tenant RLS setup:

```py
async def set_tenant_context(session: AsyncSession, tenant_id: UUID):
    await session.execute(
        text("SET LOCAL app.tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )
```

Invariant:

```txt
No tenant-owned database query may run before app.tenant_id is set from verified AuthContext.
```

---

## 14. Configure Frontend Routes

Recommended route protection (already implemented in `apps/web/src/shell/router.tsx`):

```txt
Public:
  /
  /sign-in
  /sign-up

Authenticated:
  /workspaces
  /onboarding
  /settings/profile

Tenant-scoped:
  /t/:tenantSlug
  /t/:tenantSlug/accounts
  /t/:tenantSlug/governance

Tenant + account-scoped:
  /t/:tenantSlug/accounts/:accountId/intelligence/signals
  /t/:tenantSlug/accounts/:accountId/studio/calculator
```

Frontend route guards are for UX only. Backend authorization remains mandatory.

---

## 15. Configure Production Hardening

For production Clerk:

```txt
- production Clerk instance
- production publishable key
- production secret key
- custom domain if needed
- allowed origins locked to production domains
- redirect URLs locked to production domains
- MFA enabled for admins
- SSO/SAML available for enterprise customers
- webhook signature verification enabled
- webhook retries monitored
- API keys stored only in Infisical prod
- no developer default access to prod Clerk secrets
```

---

## 16. Add Tests

Minimum test plan:

- [ ] Frontend redirects unauthenticated users to `/sign-in`.
- [ ] Authenticated user without org is redirected to `/workspaces`.
- [ ] Authenticated user with org can access `/t/:tenantSlug`.
- [ ] API client sends `Authorization: Bearer <token>`.
- [ ] Gateway rejects missing token.
- [ ] Gateway rejects invalid Clerk token.
- [ ] Gateway rejects wrong audience.
- [ ] Gateway rejects wrong authorized party.
- [ ] Gateway resolves Clerk org to ValuePact tenant.
- [ ] Gateway signs internal AuthContext.
- [ ] L1-L6 reject requests without `X-Fabric-Auth`.
- [ ] L1-L6 reject tampered `X-Fabric-Auth`.
- [ ] Backend sets `app.tenant_id` from verified AuthContext.
- [ ] Cross-tenant account access fails.
- [ ] Clerk webhook creates/updates/deactivates local user records.
- [ ] Clerk webhook creates/updates/deactivates tenant memberships.

Existing tests:
- `apps/web/src/components/routing/RequireClerkAuth.test.tsx`
- `apps/web/src/auth/ClerkAuthBridge.test.tsx`
- `apps/web/src/auth/clerkSession.test.ts`
- `apps/web/src/api/client.clerkBearer.adversarial.test.ts`
- `apps/web/src/auth/clerkSecretLeakage.test.ts`
- `services/api/app/tests/test_clerk_webhook_idempotency.py`

---

## 17. Recommended Rollout Order

```md
- [ ] Create Clerk dev/staging/prod apps.
- [ ] Enable Organizations.
- [ ] Define org roles and coarse permissions.
- [ ] Add Clerk keys to Infisical.
- [ ] Add ClerkProvider to `apps/web`.
- [ ] Add `/sign-in`, `/sign-up`, `/workspaces`, `/onboarding`.
- [ ] Wire `getToken()` into the ValuePact API client.
- [ ] Implement gateway Clerk JWT verification.
- [ ] Implement ValuePact tenant/user mapping tables.
- [ ] Implement signed internal AuthContext from gateway.
- [ ] Implement L1-L6 internal AuthContext verification.
- [ ] Add Clerk webhook sync.
- [ ] Add frontend route guards.
- [ ] Add PostgreSQL-backed tenant/RLS integration tests.
- [ ] Add production Clerk hardening.
```

Most of these are already complete in the codebase. See "What's Already Implemented" above.

---

## Final Recommended Configuration

For ValuePact, the clean setup is:

```txt
Frontend:
  Clerk React SDK
  ClerkProvider
  getToken({ template: "fabric4l-api" })

API Gateway:
  verify Clerk JWT
  resolve Clerk org → ValuePact tenant
  sign ValuePact AuthContext

L1-L6:
  reject raw Clerk tokens
  verify ValuePact internal AuthContext
  enforce permissions
  set PostgreSQL RLS tenant context

Infisical:
  dev/staging/prod Clerk keys
  webhook secret
  gateway signing keys
  service verification keys

Database:
  users
  tenants
  tenant_memberships
  account_memberships
  entitlements
  audit events
```

This keeps Clerk as the identity provider without letting it replace ValuePact's real authorization, tenant isolation, and audit model.
