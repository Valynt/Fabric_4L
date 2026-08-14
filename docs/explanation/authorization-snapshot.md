# Backend-verified authorization snapshot

## Trust boundary

`GET /v1/authz/snapshot` is the browser's exclusive grant source. Layer 4 requires the shared authenticated `RequestContext`, resolves the tenant record from `ctx.tenant_id`, and compares the optional `tenant_slug` selector rather than trusting it. Missing tenant identity, tenant lookup failure, an unusable authentication expiry, or an expired context returns 401; a selector mismatch returns 403. No error response contains grants.

The snapshot contains the resolved tenant ID and slug, informational compatibility role, authentication expiry, normalized request-context permissions, normalized entitlements, confirmed membership, and normalized account IDs. Arrays are deduplicated, sorted, and stripped of empty values. Permissions come only from `RequestContext.permissions`. A role never adds permissions.

## Frontend state model

Snapshot resolution is a discriminated union:

- `loading`: identity or snapshot resolution is pending; grants are empty.
- `verified`: the payload is structurally valid, tenant-matched, and current. This is the only variant containing a snapshot or grants.
- `denied`: the initial request failed or the response was missing, malformed, or mismatched; grants are empty.
- `expired`: the actual expiry has elapsed and renewal has not restored a current snapshot; grants are empty.

The query key includes the active tenant slug and does not use placeholder or previous data. A tenant change therefore publishes loading state for the replacement tenant rather than reusing grants. A timer invalidates a verified snapshot at its exact expiry, immediately removes grants, and attempts one query refresh. An unsuccessful refresh remains expired.

Requirement evaluation is a separate `loading | allowed | denied | expired` union. Only a verified snapshot containing every required permission and entitlement, confirmed tenant membership, and the exact account ID can become allowed. A verified snapshot missing a grant remains verified while that particular decision is denied.

## Routes, scope, and feature flags

`UnifiedRouteGuard` handles authentication before authorization. Signed-out users are redirected to sign-in with the attempted path in router state. Loading renders verification UI. Allowed renders children. Denied renders a supplied fallback or the in-place access-denied state while retaining the attempted URL. Expired renders reauthentication guidance after the snapshot hook has exhausted its single renewal attempt. Protected children are never rendered in any other state.

Route policies express permissions rather than tiers. Tenant-scoped routes require backend-confirmed membership; account-scoped routes additionally require the route account in `accountIds`. Feature flags are passed only as an additional restriction on a snapshot decision: a disabled flag denies, while an enabled flag cannot compensate for a missing grant.

## Compatibility tier layer

The Zustand tier store remains temporarily for display density and labels. Known role names can map to display tiers. Unknown, absent, empty, or malformed roles map to `unknown` and actively replace a previously stored tier. Store permission and route methods always deny, so persisted tiers, Clerk roles, and frontend defaults cannot authorize.

## Test-driven migration and coverage

Backend tests cover successful authoritative resolution, deterministic grants, tenant-selector attacks, missing tenant context, malformed/expired authentication expiry, router registration, and OpenAPI schema exposure. Frontend tests cover strict payload validation, custom roles, tenant and expiry failures, all-grant decisions, membership/account enforcement, feature-flag restriction, route-state rendering, return URLs, and compatibility-tier clearing. The Layer 4 OpenAPI artifact and generated TypeScript client are regenerated from runtime code so the wire contract and consumer types remain synchronized.
