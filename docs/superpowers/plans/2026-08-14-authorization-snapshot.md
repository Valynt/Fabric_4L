# Authorization Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish `GET /auth/authorization-snapshot` and one fail-closed frontend provider as the only browser privilege authority.

**Architecture:** The gateway issues a versioned candidate from one lock-consistent authorization projection populated from canonical identity data. The frontend validates the candidate against the active Clerk session, organization, and requested account tuple before exposing grants. Existing hooks temporarily become selectors over the provider, while flags remain an independent conjunctive rollout input.

**Tech Stack:** FastAPI, Pydantic v2, React, Clerk React, TanStack Query, Zod, Vitest, pytest, OpenAPI.

## Global Constraints

- Use only `GET /auth/authorization-snapshot`.
- `X-Account-ID` is an untrusted optional selector and never establishes identity or tenant.
- Only `verified` frontend resolution exposes grants.
- The initial query key is `sessionDiscriminator`, active Clerk organization ID, and normalized account scope.
- Snapshot candidates use `source: "backend"`, expire within five minutes, and are never intermediary-cacheable.
- Feature flags never grant privileges; privileged features require both flag and snapshot authorization.

---

### Task 1: Canonical backend snapshot issuance

**Files:**
- Modify: `services/api/app/core/clerk_verifier.py`
- Modify: `services/api/app/core/clerk_auth.py`
- Modify: `services/api/app/core/auth_directory.py`
- Create: `services/api/app/services/authorization_snapshot.py`
- Modify: `services/api/app/routers/clerk_auth.py`
- Test: `services/api/tests/test_authorization_snapshot.py`

**Interfaces:**
- Consumes: verified `ClerkClaims`, `AuthContext`, and optional `X-Account-ID`.
- Produces: `AuthorizationSnapshotService.issue(auth, claims, account_id)` and the OpenAPI response model.

- [ ] Write failing tests for tenant issuance, exact session binding, closed roles, maximum expiry, atomic projection reads, no-store responses, and indistinguishable account denial.
- [ ] Run `pytest -q services/api/tests/test_authorization_snapshot.py` and confirm failures identify the missing endpoint/service.
- [ ] Add the session claim, lock-consistent projection read, service, route, and stable denial envelope.
- [ ] Run the focused pytest file and confirm it passes.

### Task 2: Authoritative OpenAPI contract

**Files:**
- Modify by generation: `contracts/openapi/fabric-4l-api.json`
- Modify by generation: `packages/platform-contract/src/typescript/generated/fabric_4l_api.ts`
- Modify by generation: `apps/web/src/api/generated/fabric/index.ts`

**Interfaces:**
- Consumes: FastAPI response models from Task 1.
- Produces: `AuthorizationSnapshot` and `CanonicalAuthorizationRole` generated schemas.

- [ ] Add a contract test asserting the exact endpoint, header, response schema, closed role enum, and no-store documentation.
- [ ] Run the contract test and confirm it fails before regeneration.
- [ ] Run the repository OpenAPI/type generation command.
- [ ] Run `pnpm run check:api-types` and confirm no drift.

### Task 3: Fail-closed frontend provider

**Files:**
- Create: `apps/web/src/auth/authorizationSnapshotSchema.ts`
- Create: `apps/web/src/auth/AuthorizationProvider.tsx`
- Create: `apps/web/src/auth/AuthorizationProvider.test.tsx`
- Modify: `apps/web/src/App.tsx`

**Interfaces:**
- Consumes: Clerk `user`, `session`, and active organization plus selected account state.
- Produces: `useAuthorizationSnapshot(): AuthorizationResolution` with verified-only selectors.

- [ ] Write failing tests for runtime validation, tuple mismatch, expiry, query keys, header behavior, and synchronous stale-data removal.
- [ ] Run the focused Vitest file and confirm expected failures.
- [ ] Implement the Zod candidate parser, provider state machine, exact query key, and verified-only selectors.
- [ ] Mount the provider above routing and run focused tests to green.

### Task 4: Migrate guards and temporary selector hooks

**Files:**
- Modify: `apps/web/src/components/routing/UnifiedRouteGuard.tsx`
- Modify: `apps/web/src/hooks/useUserPermissions.ts`
- Modify: `apps/web/src/hooks/useEntitlements.ts`
- Modify: `apps/web/src/hooks/useTenantMembership.ts`
- Modify: `apps/web/src/hooks/useAccountAccess.ts`
- Modify: their focused tests.

**Interfaces:**
- Consumes: `useAuthorizationSnapshot` only.
- Produces: existing compatibility return shapes without independent fetches or inferred grants.

- [ ] Write failing tests proving tier/local-storage/flags cannot grant and compatibility hooks issue no requests.
- [ ] Run focused tests and confirm the parallel authorities are detected.
- [ ] Replace guard decisions and hooks with snapshot selectors; remove tier-to-permission tables.
- [ ] Run focused tests to green.

### Task 5: Migrate navigation and privileged controls

**Files:**
- Modify: `apps/web/src/components/navigation/TieredNav.tsx`
- Modify: `apps/web/src/components/navigation/MobilePersistentSidebar.tsx`
- Modify: `apps/web/src/components/layout/LeftNavigation.tsx`
- Modify: affected action-control components discovered by `rg`.
- Test: affected navigation and component tests.

**Interfaces:**
- Consumes: verified snapshot selectors plus independent feature-flag inputs.
- Produces: fail-closed navigation/action visibility.

- [ ] Add tests for unauthorized, authorized, flag-only, and flag-plus-authorized behavior.
- [ ] Run focused tests and confirm existing tier visibility fails the new expectations.
- [ ] Replace privileged tier visibility and action gates with snapshot selectors.
- [ ] Run focused tests to green.

### Task 6: Compatibility retirement governance and verification

**Files:**
- Modify: `docs/governance/compatibility-debt-registry.md`
- Modify or create: a frontend authorization drift check under `apps/web/scripts/`.

**Interfaces:**
- Produces: explicit deletion criteria and CI protection against new authorization authorities.

- [ ] Document that compatibility hooks are removed after guard, navigation, actions, tests, and fixtures directly use the provider and repository search finds no production imports.
- [ ] Add a check forbidding authorization fetches outside the provider and role/tier-to-permission tables.
- [ ] Run focused backend/frontend tests, lint, typecheck, contract checks, and `make verify`.
- [ ] Commit with a conventional commit and `Co-authored-by: Ona <no-reply@ona.com>`.
