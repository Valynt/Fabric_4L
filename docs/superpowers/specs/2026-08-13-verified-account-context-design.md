# Verified Account Context Design

## Goal

Make the presentation-level selected account fail closed across authentication and tenant transitions by binding its session-scoped persisted payload to the backend-verified Fabric tenant identity.

## Scope

This change covers the canonical platform store contract, the web account-context store and authorization lifecycle integrations, unit and hostile regression tests, Playwright account helpers, and contract documentation. It does not change backend authorization APIs or make browser state authoritative.

## Architecture

The platform contract defines one versioned session-storage key and payload version. The only persisted fields are `fabricTenantId` and `selectedAccountId`; Zustand metadata may wrap that payload, but no Clerk organization, authentication token, account data, or authorization decision is persisted.

The web store does not hydrate automatically. Automatic hydration is disabled so an asynchronous or delayed hydration callback cannot restore stale state after an identity reset. Instead, the store exposes explicit lifecycle transitions:

- An authentication-session or active-Clerk-organization change synchronously clears both in-memory and persisted account context before replacement authorization resolves.
- A verified backend tenant snapshot supplies the authoritative `fabricTenantId`. Only then may the store read the untrusted browser payload and restore `selectedAccountId`, and only when the stored tenant exactly equals the verified tenant.
- A denied, expired, or unauthenticated result synchronously clears in-memory and persisted state.
- Account selection writes are ignored until a verified tenant is active. After verification, writes persist the selected account with that verified tenant identifier.

`activeOrgId` is an invalidation/comparison signal only. It is never persisted as the tenant identity and never substitutes for `fabricTenantId`.

## Storage Contract

- Storage: `window.sessionStorage`.
- Key: one exported platform-contract constant containing an explicit version suffix.
- Payload version: one exported platform-contract constant used by the Zustand persist envelope.
- Persisted state: `{ fabricTenantId: string | null, selectedAccountId: string | null }`.
- Trust: all parsed browser values are untrusted presentation input. Malformed, wrong-version, wrong-tenant, or structurally invalid values are discarded.

The old manual tenant-keyed `loadAccountContextForTenant` and `saveAccountContextForTenant` helpers are removed because the consumer audit found no production callers. Their dedicated tests are removed and replaced by lifecycle behavior tests.

## Data Flow

1. Clerk authentication/session or organization identity changes.
2. The auth bridge synchronously calls the account store invalidation transition, which updates memory and removes the versioned session key.
3. The tenant-resolution query requests the backend authorization mapping.
4. While resolution is pending, the store has no verified tenant and rejects selection persistence.
5. On a verified snapshot, the resolver calls the store verification transition with `fabricTenantId`. The store restores only an exact-tenant, valid-version payload; otherwise it clears storage and starts with no selected account.
6. On denied, expired, query failure, or unauthenticated resolution, the resolver calls the clearing transition.
7. Account-scoped routes, data, controls, and actions continue to wait for and require the existing exact-account backend access check. The selected account only assists navigation and presentation.

## Security and Failure Handling

- Tenant switching cannot carry a selected account across the authorization boundary.
- Session switching and sign-out synchronously remove the persisted and in-memory selection.
- Storage tampering cannot establish authorization; invalid payloads fail closed, and even valid-looking IDs must pass backend account authorization.
- Delayed hydration cannot repopulate state because implicit Zustand hydration is disabled and restoration occurs only inside the verified transition.
- Backend tenant denial, expiration, unauthenticated state, and account denial expose no account-scoped route, data, control, or action.

## Testing

Store tests cover initial state, pre-verification write rejection, verified exact-tenant persistence/restoration, tenant mismatch, malformed/tampered payloads, synchronous session and organization resets, denied/expired/unauthenticated clearing, and delayed-hydration resistance. Hook/bridge tests prove lifecycle events invoke the synchronous reset and verified-resolution transitions. Route/access tests retain or add a hostile backend-account-denial assertion showing a browser-selected account cannot grant access. Playwright helpers seed and inspect the exact canonical key, version, and payload.

## Documentation and Compatibility

`packages/platform-contract/src/typescript/stores.ts` is the executable source of truth for the key, version, payload, and canonical store lifecycle. `packages/platform-contract/CONTRACT.md` documents the same values and explicitly states that selected-account state is untrusted navigation/presentation input. This intentionally invalidates the prior unversioned session payload; no compatibility reader is retained because failing closed is safer than migrating authorization-adjacent browser state.
