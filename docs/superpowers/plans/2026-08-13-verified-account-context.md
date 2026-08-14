# Verified Account Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind the session-scoped selected-account presentation state to the backend-verified Fabric tenant and fail closed across every authentication transition.

**Architecture:** Export one versioned storage key, payload version, and payload type from the platform contract. Disable automatic Zustand hydration and make authentication invalidation and verified tenant resolution explicit store transitions, with the auth bridge clearing synchronously before replacement resolution and `useResolvedTenant` providing the authoritative `fabricTenantId`.

**Tech Stack:** TypeScript, React, Zustand persist middleware, TanStack Query, Clerk, Vitest, Testing Library, Playwright.

## Global Constraints

- Use one versioned `sessionStorage` key, defined once in the platform contract.
- Persist only `fabricTenantId` and `selectedAccountId`.
- Never persist or restore a selected account before backend tenant verification.
- Clear memory and storage synchronously on session/org changes and denied, expired, or unauthenticated authorization.
- Treat browser values as untrusted presentation input; exact-account backend authorization remains mandatory.

---

### Task 1: Canonical storage contract

**Files:**
- Modify: `packages/platform-contract/src/typescript/stores.contract-tests.ts`
- Modify: `packages/platform-contract/src/typescript/stores.ts`

**Interfaces:**
- Produces: `ACCOUNT_CONTEXT_STORAGE_KEY`, `ACCOUNT_CONTEXT_STORAGE_VERSION`, and `PersistedAccountContext`.

- [ ] **Step 1: Write failing contract tests** asserting the exact versioned key, version, and payload fields, and that no Clerk organization field exists.
- [ ] **Step 2: Run `pnpm --dir packages/platform-contract run contract:test:ts`** and confirm the missing exports fail compilation.
- [ ] **Step 3: Export the constants and payload interface** and update the canonical store example to use session storage, explicit verified/reset transitions, and disabled automatic hydration.
- [ ] **Step 4: Re-run the TypeScript contract test** and confirm it passes.

### Task 2: Fail-closed account-context store

**Files:**
- Modify: `apps/web/src/stores/accountContextStore.test.ts`
- Modify: `apps/web/src/stores/accountContextStore.ts`

**Interfaces:**
- Consumes: platform contract key, version, and payload.
- Produces: `authorizationIdentityChanged()`, `authorizationVerified(fabricTenantId)`, `authorizationUnavailable()`, `setSelectedAccountId()`, and `clearSelectedAccountId()`.

- [ ] **Step 1: Replace helper-specific tests with hostile lifecycle tests** for pre-verification writes, exact-tenant restore, tenant mismatch, malformed/tampered/wrong-version storage, synchronous clearing, and delayed hydration.
- [ ] **Step 2: Run `pnpm --dir apps/web exec vitest run src/stores/accountContextStore.test.ts`** and confirm failures identify the absent lifecycle.
- [ ] **Step 3: Remove the unused manual load/save helpers and implement the minimal explicit lifecycle** with `skipHydration`, strict payload parsing, synchronous storage removal, and verified-only persistence.
- [ ] **Step 4: Re-run the store test** and confirm it passes.

### Task 3: Authentication and tenant-resolution integration

**Files:**
- Modify: `apps/web/src/auth/ClerkAuthBridge.test.tsx`
- Modify: `apps/web/src/auth/ClerkAuthBridge.tsx`
- Modify: `apps/web/src/hooks/useResolvedTenant.test.ts`
- Modify: `apps/web/src/hooks/useResolvedTenant.ts`

**Interfaces:**
- Consumes: the account store lifecycle transitions from Task 2.
- Produces: synchronous reset before session/org replacement and verified/unavailable resolution wiring.

- [ ] **Step 1: Write failing bridge and resolver tests** for org switch, session switch/sign-out, verified `fabricTenantId`, and denied/expired/query-error clearing.
- [ ] **Step 2: Run the two focused Vitest files** and confirm lifecycle assertions fail.
- [ ] **Step 3: Wire the auth bridge to reset synchronously for identity changes** and wire the resolver to verify only successful active snapshots and clear every unavailable state.
- [ ] **Step 4: Re-run the focused tests** and confirm they pass.

### Task 4: E2E helpers, account denial, and documentation

**Files:**
- Modify: `apps/web/e2e/fixtures/account-helpers.ts`
- Modify: `apps/web/src/components/routing/UnifiedRouteGuard.test.tsx` or the nearest existing account-guard test
- Modify: `packages/platform-contract/CONTRACT.md`

**Interfaces:**
- Consumes: canonical key/version/payload and existing `useAccountAccess` backend snapshot.
- Produces: aligned test fixtures and explicit untrusted-presentation-state documentation.

- [ ] **Step 1: Add/strengthen a failing hostile route test** proving a selected account is denied when the exact-account backend authorization snapshot denies access.
- [ ] **Step 2: Run the focused guard test** and confirm the hostile assertion fails if account authorization is bypassed.
- [ ] **Step 3: Update helpers** to import the canonical constants and seed `{ state: { fabricTenantId, selectedAccountId }, version }`; require a verified tenant ID when selecting an account.
- [ ] **Step 4: Update `CONTRACT.md`** with the exact key, version, lifecycle, and backend authorization requirement.
- [ ] **Step 5: Run focused store, bridge, resolver, guard, and platform-contract tests** and confirm they pass.

### Task 5: Verification and delivery

**Files:**
- Modify only files required to resolve verification findings.

- [ ] **Step 1: Run `pnpm --dir apps/web run typecheck`.**
- [ ] **Step 2: Run `pnpm --dir apps/web run lint`.**
- [ ] **Step 3: Run the complete relevant Vitest suite and `pnpm --dir packages/platform-contract test`.**
- [ ] **Step 4: Run `git diff --check` and inspect the final diff for contract/lifecycle alignment.**
- [ ] **Step 5: Commit with a conventional commit and `Co-authored-by: Ona <no-reply@ona.com>`.**
- [ ] **Step 6: Create the pull request with the repository template sections and recorded validation evidence.**
