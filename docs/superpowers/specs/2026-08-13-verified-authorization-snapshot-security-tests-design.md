# Verified Authorization Snapshot Security Tests Design

**Date:** 2026-08-13

**Status:** Approved for implementation planning

**Scope:** Frontend authorization control plane, hostile browser tests, and canonical backend account-scope enforcement

## 1. Purpose

Establish one backend-issued authorization snapshot as the frontend's only privilege authority, then prove that browser state tampering, stale asynchronous responses, tenant or session transitions, and backend failures cannot expose protected UI.

The suite will distinguish three kinds of evidence:

1. Component and hook tests prove the frontend state machine and selectors fail closed.
2. Playwright tests prove hostile browser state and mocked failure responses cannot expose protected UI.
3. Backend endpoint tests prove the server rejects cross-tenant account scope. Browser mocks are not evidence of server-enforced isolation.

This work is complementary to GitHub issue [#1258](https://github.com/bmsull560/Fabric_4L/issues/1258), which owns queue tenant envelopes and worker kill switches, signed-URL/export isolation, AI retrieval/prompt/memory/trace isolation, and live staging replay evidence. This design does not duplicate those data-plane scenarios.

## 2. Security invariants

- Local storage, session storage, presentation tiers, and feature flags never grant routes, permissions, entitlements, organization membership, or account scope.
- `GET /auth/authorization-snapshot` is the frontend's sole authorization authority.
- Every non-public route resolves a snapshot. An empty permission list does not make an authenticated or tenant-scoped route public.
- A snapshot is usable only for its exact principal, session, tenant, and resolved account scope and only before expiry.
- Tenant or session changes make the previous snapshot unusable synchronously, before replacement network work completes.
- A late response for an obsolete tenant, session, or account cannot authorize the active context or render protected content.
- Backend denial, malformed data, expiry, and transport failure fail closed.
- Explicit authorization denial does not redirect by default.

## 3. Authorization model

Snapshot data and resolution state are separate types.

```ts
type AuthorizationResolution =
  | { status: "loading"; snapshot: null }
  | { status: "verified"; snapshot: AuthorizationSnapshot }
  | {
      status: "denied";
      snapshot: null;
      reason: AuthorizationDenialReason;
    }
  | { status: "expired"; snapshot: null; reason: "expired" };
```

`AuthorizationSnapshot` contains:

- `principalId`: authenticated backend principal.
- `sessionDiscriminator`: opaque value binding the snapshot to the current login session.
- `tenantId`: exact active tenant.
- Verified organization membership for `tenantId`.
- `accountScope`: either tenant-wide or one exact account.
- `roles`: resolved backend roles.
- `permissions`: resolved backend permissions.
- `entitlements`: resolved backend entitlements.
- `source: "backend"`.
- `issuedAt`: issuance instant.
- `expiresAt`: expiry instant.

The resolved account scope is a discriminated union, not an account list:

```ts
type AuthorizationAccountScope =
  | { kind: "tenant" }
  | { kind: "account"; accountId: string };
```

When the request includes `X-Account-ID`, a verified response must echo that exact account as `{ kind: "account", accountId }`. A missing echo, tenant-wide response, or different account is malformed for that request and is denied. Tenant-wide scope is valid only when the request and route do not select an account and the backend deliberately resolves tenant-wide access.

`AuthorizationDenialReason` will be a closed set that distinguishes authentication/authorization denial, tenant or account mismatch, malformed response, unknown role, and transport failure without exposing sensitive backend details.

## 4. Canonical query and validation boundary

One TanStack Query fetches and validates `GET /auth/authorization-snapshot`. Its key includes all identities that affect authorization:

```text
["authorization-snapshot", principalId, sessionDiscriminator, tenantId, accountScope]
```

The request sends the selected account through `X-Account-ID` when account-scoped. Tenant and principal/session identity come from authenticated context, not attacker-controlled request data.

The boundary accepts `verified` only if:

1. The response matches the runtime schema.
2. `source` is exactly `backend`.
3. Principal, session discriminator, and tenant match the active authenticated context.
4. Organization membership is verified for the exact tenant.
5. The returned account scope matches the request, including the exact `X-Account-ID` echo.
6. `issuedAt` and `expiresAt` are valid instants and the snapshot is not expired.
7. Roles, permissions, and entitlements are correctly typed and roles are recognized.

Malformed responses, mismatches, unknown roles, `401`, `403`, `5xx`, and network failures resolve to denial. An otherwise valid but expired snapshot resolves to `expired` so the guard can attempt refresh and present session-expiry behavior.

Only genuinely public routes skip the snapshot query. Authenticated, tenant-scoped, account-scoped, privileged, or entitled routes must resolve it even when their permission or entitlement arrays are empty.

## 5. Selectors and removal of parallel authorities

Tenant membership, exact account access, roles, permissions, and entitlements are selectors over the single `AuthorizationResolution`. Existing `useUserPermissions`, `useEntitlements`, tenant-membership access used by routing, and `useAccountAccess` will delegate to that snapshot rather than issue separate authorization queries.

Selectors return enough state for the guard to distinguish loading, verified-but-missing-requirement, denied, and expired. They cannot convert local tier or feature state into authorization.

`normalizeRoleToTier` will be deleted if it has no non-security presentation purpose. If retained for presentation, `normalizeRoleToTier("unknown_role")` must return an unresolved value rather than `standard`, and tests must preserve that behavior. It must never participate in authorization decisions.

## 6. Route guard state machine

The unified route guard behaves as follows:

| Condition | Guard behavior |
|---|---|
| Genuinely public route | Render without snapshot resolution |
| Authentication loading | Show verification UI |
| Unauthenticated protected route | Redirect to sign-in |
| Authorization `loading` | Show verification UI; never render protected children |
| Authorization `verified` and policy satisfied | Render protected children |
| Authorization `verified` but policy unsatisfied | Use an explicitly supplied fallback; otherwise render the standard in-place access-denied state |
| Authorization `denied` | Use an explicitly supplied fallback; otherwise render the standard in-place access-denied state |
| Authorization `expired` | Attempt one canonical refresh, then render expired-session or reauthentication UI if still expired |

An explicit denial does not redirect by default. Redirects are reserved for unauthenticated sign-in flow or a route policy that deliberately supplies a fallback. Every loading, denial, expiry, error, and transition test asserts that protected content never flashes.

## 7. Privileged-feature truth table

Feature flags control availability; verified authorization controls privilege. Both are required:

| Feature flag | Verified authorization | Result |
|---|---|---|
| Flag off | Unauthorized | Denied |
| Flag on | Unauthorized | Denied |
| Flag off | Authorized | Feature unavailable |
| Flag on | Authorized | Allowed |

Setting `isAdvancedModeEnabled`, changing `user-tier-storage.currentTier`, or otherwise tampering with presentation state cannot change any row's authorization input.

## 8. Component and hook tests

Focused guard tests remain alongside `apps/web/src/components/routing/UnifiedRouteGuard.test.tsx`. Supporting snapshot-query, parser, and selector tests live beside their production modules.

### Guard coverage

- `user-tier-storage.currentTier = "admin"` cannot grant an admin route, permission, or entitlement.
- `isAdvancedModeEnabled = true` cannot grant an advanced route, permission, or entitlement.
- All four privileged-feature truth-table rows.
- Missing or unknown roles remain on verification UI while resolution is loading, then deny explicitly.
- Authenticated or tenant-scoped routes with empty requirement arrays still await snapshot verification.
- Backend `401`, `403`, malformed, expired, and `5xx` outcomes fail closed with the specified state-specific UI.
- Explicit denial uses an in-place access-denied state unless the policy supplies a fallback.
- Unauthenticated access redirects to sign-in.
- No denied, loading, expired, or failure transition renders or flashes protected children.

### Query, parser, and selector coverage

- A current, unexpired snapshot for the active principal/session/tenant is accepted.
- Tenant A's snapshot is rejected immediately after switching to tenant B.
- An expired snapshot resolves to `expired`.
- A previous-session snapshot is rejected.
- Principal, session, tenant, organization-membership, or account-scope mismatch is denied.
- An account-scoped response must echo the exact `X-Account-ID`.
- Tenant, session, and exact account participate in the query key.
- Account scope verified for tenant A is not reused under tenant B, including when account identifiers match.
- `401`, `403`, malformed payloads, `5xx`, and transport failures cannot retain or revive stale verified state.
- Each selector derives membership, account access, roles, permissions, and entitlements from the same snapshot object.
- Unknown roles remain unresolved while loading and then deny; if `normalizeRoleToTier` remains, its unknown-role result is unresolved.

### Controlled late-response sequence

Tests use controlled promises:

1. Begin tenant-A resolution.
2. Switch the active context to tenant B.
3. Assert tenant-A authorization is synchronously unusable and protected content is absent.
4. Resolve the tenant-A request.
5. Assert its result cannot populate or authorize tenant B's key.
6. Resolve tenant B's request.
7. Assert only tenant B's verified result can authorize tenant-B UI.

Equivalent coverage applies to session changes and account-scope changes.

## 9. Browser authorization fixtures

`apps/web/e2e/fixtures/tier-helpers.ts` will be replaced, not wrapped. No `setUserTier` compatibility helper remains. Callers migrate to clearly named fixtures that mock the canonical snapshot endpoint:

- `mockVerifiedAuthorization`
- `mockDeniedAuthorization`
- `mockExpiredAuthorization`
- `mockDelayedAuthorization`
- `mockMalformedAuthorization`
- `mockAuthorizationTransportFailure`
- `clearAuthorizationMocks`

Fixtures construct backend-shaped responses bound to explicit principal, session, tenant, and account scope. They do not write privileged local-storage state. Direct privileged-state writes are allowed only inside hostile tampering tests, where they represent attacker behavior.

Existing E2E callers of tier helpers must adopt verified fixtures and express the required backend roles, permissions, entitlements, membership, and account scope explicitly. This prevents new tests from perpetuating tier-as-authority semantics.

## 10. Browser hostile suite

A focused file under `apps/web/e2e/security/`, tentatively `authorization-state-tampering.spec.ts`, will cover:

1. Admin-tier local-storage tampering cannot expose an admin route or admin UI.
2. Advanced-mode tampering cannot expose advanced routes or features.
3. All privileged-feature truth-table combinations.
4. Tenant-A snapshot state becomes unusable while tenant B is loading.
5. A delayed tenant-A response arriving after the switch cannot expose tenant-B protected UI.
6. Expired and previous-session snapshot replay cannot expose protected UI.
7. Tenant-A account scope cannot be reused under tenant B.
8. `401`, `403`, malformed, expired, `5xx`, and transport-failure responses fail closed.
9. Loading, transition, denial, expiry, and failure states never flash protected content.

These Playwright tests prove browser tampering resistance and frontend failure behavior against controlled responses. Test comments cross-reference #1258 as complementary data-plane tenancy coverage and explicitly state that intercepted responses do not prove server enforcement.

## 11. Canonical backend enforcement tests

Authoritative cross-tenant account-scope proof targets:

```text
GET /auth/authorization-snapshot
X-Account-ID: <selected-account>
```

Backend tests prove:

1. A principal in tenant A can receive a verified account-scoped snapshot for an account owned by tenant A when otherwise authorized.
2. A tenant-B principal requesting tenant A's account through `X-Account-ID` is rejected using the canonical non-disclosing denial response.
3. The rejection returns no tenant-A account data, roles, permissions, or entitlements.
4. The backend never issues tenant-wide scope or a different account scope in response to an account-scoped request.
5. Missing, malformed, or conflicting account scope fails closed according to the endpoint contract.

Existing account-access endpoints may receive defense-in-depth tests, but the frontend will not treat them as a parallel authority and they cannot substitute for canonical snapshot endpoint evidence.

## 12. Documentation and evidence claims

Security-suite documentation will include a coverage matrix identifying:

- Component/hook evidence: frontend validation and state transitions.
- Playwright evidence: protected UI remains absent under tampering and controlled backend outcomes.
- Backend endpoint evidence: real cross-tenant `X-Account-ID` rejection.
- Issue #1258 evidence: complementary queue, signed-URL/export, AI-context, and staging-replay tenancy enforcement.

No report, test comment, PR, or final response will present browser mocks as proof of server-enforced tenant isolation.

## 13. Implementation sequence and validation

Implementation will follow test-driven development:

1. Add failing snapshot-model and validation tests.
2. Implement the canonical query and runtime validation.
3. Add failing selector and transition tests, including controlled late responses.
4. Convert authorization hooks into selectors over the one query.
5. Add failing route-guard state-machine and tampering tests.
6. Update the guard and standard denial/expiry presentation.
7. Replace tier helpers and migrate E2E callers to verified fixtures.
8. Add the focused hostile Playwright suite.
9. Add canonical backend endpoint tests for `X-Account-ID` isolation.
10. Add the security-suite coverage documentation and #1258 boundary.

Validation will run the narrowest checks first, followed by broader gates:

- Focused Vitest files for the snapshot query, selectors, and `UnifiedRouteGuard`.
- Focused Playwright security suite.
- Focused backend authorization-snapshot endpoint tests.
- Frontend typecheck and lint.
- Relevant contract and security gates.
- Broader frontend unit tests and `make verify` when the environment supports the full gate.

## 14. Non-goals

- Queue worker tenant-envelope enforcement.
- Signed-URL or export replay/scoping.
- AI retrieval, prompt, memory, or trace tenancy.
- Live staging replay evidence.
- Using presentation tiers or feature flags as authorization inputs.
- Maintaining a parallel account-access, permission, entitlement, or membership authorization authority.
