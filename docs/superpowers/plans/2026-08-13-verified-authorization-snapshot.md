# Verified Authorization Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace inferred tier grants with fail-closed, verified-snapshot authorization and explicit route resolution states.

**Architecture:** A focused snapshot hook fetches and parses the tenant-bound authorization document into a discriminated union. Permission and route decisions consume that union exclusively; route rendering treats authentication, snapshot authorization, and feature flags as separate gates.

**Tech Stack:** React 18, TypeScript, TanStack Query, Zod, React Router, Vitest, Testing Library, Zustand compatibility display state.

## Global Constraints

- Snapshot status is `loading | verified | denied | expired`.
- Decision status is `loading | allowed | denied | expired`.
- Only a verified snapshot exposes permissions and entitlements.
- Tier normalization is display-only and never infers grants.
- Route authorization is evaluated exclusively from the verified snapshot.
- Feature flags can only restrict access: `featureEnabled && snapshotAuthorized`.

---

### Task 1: Fail-closed role normalization

**Files:**

- Modify: `apps/web/src/stores/userTierStore.ts`
- Test: `apps/web/src/stores/userTierStore.test.ts`

**Interfaces:**

- Produces: `normalizeRoleToTier(role: unknown): UserTier | undefined`.

- [ ] Add tests expecting known roles to retain their display mapping and unknown, missing, empty, and non-string roles to return `undefined`.
- [ ] Run `pnpm --dir apps/web exec vitest run src/stores/userTierStore.test.ts` and verify the hostile normalization cases fail because unknown roles currently return `standard`.
- [ ] Change normalization to accept `unknown`, validate a non-empty string, and return `undefined` for every unrecognized value without constructing grants.
- [ ] Update compatibility callers to preserve an unresolved tier rather than assigning a grant-bearing default.
- [ ] Re-run the focused store test and verify it passes.

### Task 2: Verified snapshot boundary and permission decisions

**Files:**

- Create: `apps/web/src/hooks/useAuthorizationSnapshot.ts`
- Create: `apps/web/src/hooks/useAuthorizationSnapshot.test.tsx`
- Modify: `apps/web/src/hooks/useUserPermissions.ts`
- Create: `apps/web/src/hooks/useUserPermissions.test.tsx`

**Interfaces:**

- Produces: `AuthorizationSnapshotState`, `VerifiedAuthorizationSnapshot`, `AuthorizationDecision`, `useAuthorizationSnapshot(tenantSlug)`, and `useUserPermissions(requiredPermissions, tenantSlug)`.
- Consumes: typed `apiGet` and the authenticated tenant context.

- [ ] Write parser and hook tests for loading, verified, absent/malformed claims, unexpected Clerk role, tenant mismatch, expiration/refresh, and fetch failure.
- [ ] Run the two focused hook test files and verify they fail because the snapshot boundary does not exist and permissions still come from tiers.
- [ ] Implement strict runtime parsing, tenant and expiration checks, empty grants outside `verified`, and one refresh attempt for expired data.
- [ ] Implement permission decisions so a verified snapshot without a required permission returns decision `denied` while the snapshot stays `verified`.
- [ ] Re-run both focused hook test files and verify they pass.

### Task 3: Snapshot-exclusive route policy and rendering

**Files:**

- Modify: `apps/web/src/routes/types.ts`
- Modify: `apps/web/src/shell/router.tsx`
- Modify: `apps/web/src/components/routing/UnifiedRouteGuard.tsx`
- Modify: `apps/web/src/components/routing/UnifiedRouteGuard.test.tsx`

**Interfaces:**

- Consumes: snapshot-derived `AuthorizationDecision` and snapshot scope checks.
- Produces: guard rendering for loading, allowed, denied, expired, and unauthenticated states.

- [ ] Replace tier-oriented guard tests with hostile decision-state tests, including in-place denial, explicit fallback, expired-session UI, loading UI, feature restriction, and sign-in redirect.
- [ ] Run the focused guard test and verify it fails against redirecting tier-based behavior.
- [ ] Remove `requiredTier` route metadata and express the standard, advanced, and admin route helpers with explicit permission requirements.
- [ ] Remove persisted-tier hydration and parallel tier checks from the guard; evaluate permission, entitlement, tenant, and account requirements from one verified snapshot decision.
- [ ] Render the supplied fallback or standard access-denied state for `denied`, and an expired-session reauthentication state for `expired`.
- [ ] Re-run the focused guard test and verify it passes.

### Task 4: Verification and delivery

**Files:**

- Modify if required by checks: only files already listed above.

**Interfaces:**

- Produces: a committed change and pull request.

- [ ] Run `pnpm --dir apps/web exec vitest run src/stores/userTierStore.test.ts src/hooks/useAuthorizationSnapshot.test.tsx src/hooks/useUserPermissions.test.tsx src/components/routing/UnifiedRouteGuard.test.tsx`.
- [ ] Run `pnpm --dir apps/web run typecheck`.
- [ ] Run `pnpm --dir apps/web run lint`.
- [ ] Run `pnpm --dir apps/web run build` because route-guard behavior is runnable frontend behavior.
- [ ] Inspect `git diff --check` and `git status --short`.
- [ ] Commit with a conventional commit and `Co-authored-by: Ona <no-reply@ona.com>`.
- [ ] Create a pull request using the repository template, including governance impact, release checklist, and exact validation results.
