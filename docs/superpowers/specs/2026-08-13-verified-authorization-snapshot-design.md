# Verified Authorization Snapshot Design

## Goal

Make frontend route authorization fail closed and derive every permission,
entitlement, tenant-membership, and account-scope decision exclusively from a
current, tenant-matched, verified authorization snapshot.

## State model

Snapshot resolution and access decisions are separate discriminated unions.

```ts
type AuthorizationSnapshotState =
  | { status: "loading"; permissions: readonly []; entitlements: readonly [] }
  | {
      status: "denied";
      permissions: readonly [];
      entitlements: readonly [];
      reason: string;
    }
  | {
      status: "expired";
      permissions: readonly [];
      entitlements: readonly [];
      reason: string;
    }
  | { status: "verified"; snapshot: VerifiedAuthorizationSnapshot };

type AuthorizationDecision =
  | { status: "loading" }
  | { status: "allowed" }
  | { status: "denied"; reason: string }
  | { status: "expired"; reason: string };
```

Only `verified` exposes the snapshot's grants. A verified snapshot that lacks a
required grant remains verified while the resulting permission decision is
denied. Missing snapshots, malformed claims, unknown roles, tenant mismatches,
and fetch failures expose no grants.

## Snapshot boundary

`useAuthorizationSnapshot` owns the server-state boundary. It requests the
current principal's authorization snapshot for the active tenant through the
typed API client and validates the response before exposing it. A verified
snapshot contains its tenant identifier, expiration time, permissions,
entitlements, tenant membership, and account scopes. The parser rejects
incorrect shapes, missing roles, and unexpected Clerk roles rather than
constructing compatibility grants.

Expired data is never used. Expiration triggers one query refresh. Resolution
reports `loading` while that refresh is pending and `expired` if no current
verified snapshot results. A transport failure without an expired snapshot is
an explicit denied snapshot state.

## Decisions

`useUserPermissions` consumes only `useAuthorizationSnapshot`. It evaluates
required permissions against a verified snapshot and returns an
`AuthorizationDecision`; its compatibility booleans, if retained, are derived
from that decision. It must not read `userTierStore` or infer grants from a
role. Tenant membership, account scope, and entitlements are evaluated from the
same verified snapshot so route authorization has one authority.

Role-to-tier normalization remains a presentation compatibility helper only.
Known roles map to display tiers. Unknown, absent, or malformed roles return an
explicit unresolved result and never imply permissions.

Feature flags remain outside authorization. They may only narrow access:

```text
featureEnabled && snapshotAuthorized
```

## Route guard behavior

The route guard first resolves authentication. Unauthenticated users redirect
to sign-in with the attempted URL preserved. Authenticated users then receive
one of four authorization decision states:

- `loading`: show the existing verification state.
- `allowed`: render children, subject to feature flags.
- `denied`: render an explicitly provided fallback or the standard access
  denied state in place; do not redirect by default.
- `expired`: after refresh cannot resolve a current snapshot, render an expired
  session state that asks the user to reauthenticate.

Tier checks and persisted-tier hydration are removed from the guard. Route
metadata expresses requirements as permissions, entitlements, tenant scope,
and account scope only.

## Hostile behavior and tests

Tests prove that unknown and absent roles do not normalize to `standard`;
unexpected Clerk roles, malformed snapshot claims, missing snapshots,
tenant-mismatched snapshots, expired snapshots, and snapshot-fetch failures
expose no grants. Hook tests distinguish snapshot status from permission
decision status. Guard tests prove loading, in-place denial, explicit fallback,
expired-session, allowed, feature-disabled, and unauthenticated redirect
behavior, and prove protected children never render without `allowed`.

## Scope

This change modifies the frontend authorization boundary and route metadata. It
does not weaken backend authorization, add a new role hierarchy, or make
feature flags grant access. Backend enforcement remains authoritative.
