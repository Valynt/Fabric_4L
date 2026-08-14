# Backend-Authoritative Authorization Snapshot Design

**Status:** Approved for implementation.
**Date:** 2026-08-13  
**Scope:** API gateway authorization contract, platform contract, and frontend authentication and routing domains

## Problem

Frontend authorization currently combines independently fetched decisions with role-to-tier inference and persisted Zustand tier state. Persisted or incomplete client state must never grant access. Authorization must instead come from one backend-authoritative, session-, tenant-, and account-bound snapshot whose transport and runtime shape are validated before use.

## Goals

- Add or update the canonical `GET /v1/authz/snapshot` endpoint without duplicating an existing aggregate authorization service.
- Atomically resolve roles, permissions, entitlements, tenant identity, and account scope at the backend authentication boundary.
- Bind every snapshot to the authenticated principal, an opaque session discriminator, the active tenant, and a canonical account scope.
- Fail closed for absent, malformed, expired, mismatched, conflicting, or unavailable authorization data.
- Remove route authorization dependence on persisted Zustand tier state.
- Refetch and isolate authorization whenever session, active Clerk organization, tenant, or account scope changes.

## Non-goals

- The snapshot does not replace backend enforcement at resource endpoints.
- Clerk organization claims do not grant roles, permissions, entitlements, or account access.
- This work does not create another client-side role or tier grant table.
- Feature flags are not authorization grants.

## Architecture Decision

The API gateway owns `GET /v1/authz/snapshot` because it is the platform authentication boundary. Before adding code, implementation must locate and reuse any existing aggregate authorization service. If authority is currently split across repositories, it must be composed behind one backend service boundary rather than through multiple frontend requests or a duplicate endpoint.

The endpoint derives principal and session identity exclusively from verified authentication middleware. It resolves the effective tenant and optional account scope on the backend, then returns one immutable snapshot. The frontend uses Clerk only to establish that a session and active organization exist and to validate that the backend result is bound to the current Clerk context.

## Authoritative Contract

The authoritative OpenAPI and platform contract will define a response equivalent to:

```ts
interface AuthorizationSnapshot {
  principalId: string;
  sessionDiscriminator: string;
  tenant: {
    id: string;
    slug: string;
  };
  accountScope: {
    kind: "tenant" | "account";
    accountId?: string;
    grantsAccountOperations: boolean;
  };
  roles: AuthorizationRole[];
  permissions: string[];
  entitlements: Array<{
    key: string;
    expiresAt?: string;
  }>;
  source: "backend";
  issuedAt: string;
  expiresAt: string;
}
```

Exact wire naming will follow repository conventions and be mapped at the frontend boundary. Arrays are deduplicated and deterministically ordered (roles by enum order; permissions lexicographically; entitlements by `key` then `expiresAt`). Role values are a closed contract enum and MUST be explicitly enumerated in the OpenAPI/platform contract (and mirrored in this design doc) before implementation. Unknown, absent, or malformed roles invalidate the entire snapshot; they must never normalize to `standard` or any other access-bearing default.

`sessionDiscriminator` is an opaque, non-secret identifier suitable only for equality and cache binding. The frontend must not decode it or assume it equals a Clerk session ID. The server derives it from the verified session. The frontend validates it against a trusted discriminator made available for the current session by the authentication integration; it never accepts a discriminator from URL or local storage.

### Request Inputs and Scope Canonicalization

The endpoint accepts an optional `account_scope` query parameter. The backend validates and canonicalizes it completely, including identifier syntax, tenant ownership, principal access, aliases, and canonical account ID. Client canonicalization is not trusted.

A tenant-wide snapshot has `kind: "tenant"`. It does not authorize an account-scoped operation unless `grantsAccountOperations` is explicitly true under the contract. An account snapshot has `kind: "account"`, includes the canonical `accountId`, and authorizes only that exact account. A requested account outside the authenticated tenant fails closed with a structured 403 response and no snapshot.

Tenant identity is not accepted as an authority-bearing request parameter. The backend obtains it from verified tenant context. Any route tenant or organization hint is comparison-only and cannot override authenticated context.

### Lifetime

The backend sets `issuedAt` to the generation time and `expiresAt` to the earliest of:

1. Clerk session expiry;
2. authorization-policy TTL;
3. the earliest relevant entitlement expiry.

The backend must never intentionally issue a snapshot that is expired at issuance. If no positive lifetime remains, it returns a denial/error response instead. Timestamps are UTC RFC 3339 values. The frontend rejects invalid ordering, invalid timestamps, future-skewed `issuedAt` beyond a small bounded tolerance (e.g., 5 minutes), or elapsed `expiresAt`.

## Backend Resolution and Failure Behavior

One authorization service operation will:

1. Require an authenticated, verified principal and session.
2. Resolve verified tenant membership and active tenant identity.
3. Canonicalize and validate optional account scope within that tenant.
4. Resolve only recognized roles from authoritative membership/policy data.
5. Resolve permissions from backend policy, not from frontend tier inference.
6. Resolve entitlements and their expirations from the authoritative billing/policy source.
7. Compute the bounded lifetime and issue the snapshot atomically.

Missing authentication returns 401 with the canonical error envelope. Tenant mismatch, membership denial, conflicting identity sources, invalid account scope, inaccessible account, malformed authoritative role data, or policy denial returns a structured 403 with the canonical error envelope (including a stable `error.code`) and no snapshot. Internal dependency failure returns a non-success response in the same canonical envelope and never a partial snapshot. Logs and audit events record safe reason codes, request IDs, principal identifiers, and scope without exposing tokens or raw Clerk claims.

## Frontend Authentication Domain

The frontend will add a focused authorization domain containing:

- `AuthorizationSnapshot`, mapped from the generated OpenAPI type;
- strict runtime parsing at the network boundary;
- `AuthorizationResolutionStatus = "loading" | "verified" | "denied" | "expired"`;
- a provider and hook backed by TanStack Query;
- pure requirement evaluators for route and UI decisions.

Resolution status describes only whether a trustworthy current snapshot exists. It is separate from a requirement decision. A `verified` snapshot can yield either `allowed` or `denied` for a specific route, permission, entitlement, account, navigation item, or action.

The parser validates `principalId`, `sessionDiscriminator`, tenant ID and slug, canonical account scope, closed-enum roles, permissions, entitlements, source, and timestamp bounds. It then compares principal and session binding with the active verified Clerk session integration, and tenant identity with the active Clerk organization. Missing Clerk context while Clerk authentication is enabled, any mismatch, or conflicting source becomes `denied`. An otherwise valid snapshot whose expiry has elapsed becomes `expired`.

Mock/development authentication must use an explicitly trusted test/backend fixture path and must not relax production validation or infer grants from incomplete claims.

## Query Identity, Refresh, and Isolation

The authorization query key contains the exact trusted context tuple:

```text
["authz", "snapshot", principalId, sessionDiscriminator, tenantId, tenantSlug, canonicalAccountScope]
```

The request uses the raw requested account scope only as backend input; the returned canonical scope must match the expected operation context before authorization is used.

Previous-data and placeholder reuse are disabled across query-key changes. When principal, session, active Clerk organization, tenant route context, or account scope changes, the provider must:

1. cancel in-flight obsolete authorization queries;
2. remove obsolete authorization queries from the query cache;
3. publish `loading` for the new tuple;
4. fetch a fresh snapshot.

No prior tenant, session, or account result may render as verified during a transition. A cached snapshot may be used only for the exact tuple and only while valid. Backend failure with no valid exact-tuple cache results in `denied`.

Before `expiresAt`, the provider schedules or triggers a refresh with a bounded safety margin. During refresh, an exact-tuple snapshot that remains valid may continue to authorize. If refresh succeeds, it replaces the snapshot. If it fails, the existing snapshot is usable only until its actual expiry. At expiry the provider enters `expired`, performs refresh-before-expired handling, and denies protected access unless refresh produces a new verified snapshot. It never silently extends lifetime.

## Requirement Evaluation

Pure evaluators return explicit `allowed | denied` decisions plus safe reason codes. They only evaluate `verified` snapshots.

- Tenant membership requires exact agreement between verified Clerk organization context and the backend snapshot tenant.
- Account access requires an account-scoped snapshot for the exact canonical account, or an explicit contract grant allowing account operations from tenant scope.
- Permissions require every declared permission.
- Entitlements require every declared entitlement to exist and remain unexpired.
- Navigation visibility and privileged action controls use the same evaluators, so hidden UI and route/action guards cannot drift.
- Feature-gated authorization is always `featureEnabled && snapshotAuthorized`; a feature flag never promotes authorization.

Existing `requiredTier` route support remains a temporary compatibility adapter. It may translate a tier requirement only to a recognized backend role requirement defined by the migration contract. It must not infer permissions, synthesize entitlements, default absent roles, or become a parallel grant table. `normalizeRoleToTier` should be removed if no non-authorization consumer needs it; if temporarily retained, unknown and absent roles return unresolved and never `standard`.

## Guard and Consumer Migration

`UnifiedRouteGuard`, `useUserPermissions`, `useEntitlements`, tenant membership checks, account-access checks, navigation visibility, and privileged action controls will consume the same snapshot provider.

Guard behavior remains:

- unauthenticated users alone are redirected to sign-in, preserving the requested location;
- `loading` renders the in-place verification state;
- an expired snapshot receives refresh-before-expired handling, then fails closed if not renewed;
- authorization denial renders the existing in-place denial UI;
- a caller-supplied `fallback` is used when present;
- verified-but-insufficient requirements produce a route decision of `denied`, not a snapshot resolution failure.

The migration removes `getPrivilegedPersistedTier`, `shouldWaitForTierHydration`, route hydration waits, `useUserTierStore` access checks, and all local-storage/Zustand participation in authorization. The tier store may remain only for unrelated, non-security UI preferences until separately retired.

## Security and Data Flow

```text
Verified Clerk session + active organization
                 |
                 v
API gateway authentication/tenant middleware
                 |
                 v
Atomic backend authorization service
  roles + permissions + entitlements + canonical account scope
                 |
                 v
GET /v1/authz/snapshot + authoritative OpenAPI contract
                 |
                 v
Frontend runtime parser and Clerk-context binding validation
                 |
                 v
resolution: loading | verified | denied | expired
                 |
                 v
per-requirement decision: allowed | denied
```

Frontend checks improve UX and prevent accidental disclosure but do not replace backend authorization on protected APIs.

## Test Strategy

Implementation follows test-driven development and includes both allowed and denied behavior.

### Backend and Contract Tests

- authenticated member receives an atomically generated, contract-valid snapshot;
- snapshot expiry is bounded by session, policy, and entitlement expiry;
- backend never intentionally issues an already-expired snapshot;
- unauthenticated requests return 401;
- tenant mismatch and cross-tenant account scope fail closed;
- tenant-wide scope cannot authorize account operations without the explicit grant;
- account aliases canonicalize to the authoritative account ID;
- inaccessible, missing, or malformed account scope fails closed;
- absent roles fail closed;
- unexpected Clerk roles and malformed claims cannot enter authoritative roles;
- malformed or unknown backend roles fail closed;
- entitlement/policy dependency failure returns no partial snapshot;
- OpenAPI and platform contract drift checks cover the endpoint and schema.

### Frontend Domain and Provider Tests

- valid exact-context responses resolve `verified`;
- verified snapshots independently produce allowed and denied requirement decisions;
- principal, session discriminator, tenant, and account mismatches resolve `denied`;
- malformed payloads, malformed claims, unknown roles, absent roles, and conflicting sources resolve `denied`;
- elapsed snapshots resolve `expired` and refresh-before-expired is attempted;
- fetch failure with no valid exact-tuple cache resolves `denied`;
- a valid exact-tuple cache survives a transient refresh only until actual expiry;
- session, organization, tenant, and account changes cancel and remove obsolete queries;
- stale-query completion cannot replace the current tuple;
- previous-data and placeholder reuse cannot expose old authorization;
- persisted admin/advanced tier data cannot promote route, navigation, or action access;
- feature access requires both the feature flag and snapshot authorization.

### Consumer Tests

- the route guard redirects only unauthenticated users to sign-in;
- loading remains in place without flashing protected content;
- denied and expired access uses in-place denial behavior after refresh handling;
- supplied fallback behavior is preserved;
- permissions, entitlements, tenant membership, and account access read only verified snapshots;
- navigation items and privileged controls disappear or disable consistently with route/action decisions;
- the temporary tier adapter does not infer permissions or default unknown roles.

## Rollout and Compatibility

1. Add service tests and the canonical backend model/service.
2. Add the endpoint and regenerate the OpenAPI artifact through the repository generator; do not hand-edit generated specifications.
3. Update the platform contract and contract tests.
4. Add frontend parser/provider tests, then implementation.
5. Migrate hooks, route guard, navigation, and privileged actions.
6. Remove Zustand authorization paths and obsolete independent authorization queries.
7. Run targeted backend, contract, frontend tests, typecheck, lint, production-auth-bypass checks, and the broad verification gate.

The endpoint is additive, but migrating authorization consumers is security-sensitive. Deployment must ensure the endpoint is available before or with the frontend release. No permissive compatibility fallback is allowed.

## Risks and Mitigations

- **Policy-source inconsistency:** centralize composition in one backend service operation and reject partial results.
- **Stale cache privilege:** bind keys to principal/session/tenant/account, remove obsolete queries, validate expiry at use time, and prevent previous-data reuse.
- **Clock skew:** document a small bounded tolerance for `issuedAt`; never extend `expiresAt` client-side.
- **Role drift:** use a closed backend/OpenAPI enum and reject unknown or absent roles.
- **Scope confusion:** canonicalize on the backend and require exact returned-scope matching.
- **UI drift:** share pure snapshot evaluators across routes, navigation, and actions.
- **Endpoint rollout ordering:** deploy backend contract first and fail closed when unavailable.

## Acceptance Criteria

- `GET /v1/authz/snapshot` is implemented once at the canonical authentication boundary and covered by authoritative OpenAPI/platform contracts.
- The snapshot is backend-authoritative and contains principal, opaque session discriminator, tenant, canonical account scope, roles, permissions, entitlements, source, issuance, and expiry.
- Expiry obeys the earliest governing lifetime and no already-expired snapshot is intentionally issued.
- Frontend runtime validation binds all identity and scope fields to the current verified Clerk context.
- Resolution status and per-requirement decisions remain distinct.
- Context changes cancel/remove old queries and cannot reuse previous authorization data.
- Route guards, hooks, tenant/account checks, navigation, and privileged actions use the snapshot.
- Zustand persistence and incomplete Clerk claims cannot grant or promote access.
- All enumerated allowed and hostile tests pass.
