# Remediation Sprint Design — Convert Core GA NO GO to Re-Testable Candidate

**Date:** 2026-06-14  
**Candidate:** `rc-2026-06-13-116815f3`  
**Goal:** Close the fixable P0 blockers discovered during runtime launch certification so the candidate can be re-tested.  
**Out of scope (for this sprint):** Pre-existing repository-level test failures `R-2026-06-13-01` (`tests/contract`) and `R-2026-06-13-02` (`make test` Layer 1 / Layer 3) remain tracked separately.

---

## 1. Problem Summary

The runtime launch certification produced a **NO GO** for Core GA because:

| ID | Problem | Root cause | Proposed fix |
|---|---|---|---|
| P0-001 | Playwright backend-integrated journeys crash with `@clerk/react: useAuth can only be used within the <ClerkProvider /> component` | Frontend is configured for `VITE_AUTH_PROVIDER=legacy` + `VITE_ENABLE_MOCK_AUTH=true`, so `main.tsx` does not mount `<ClerkProvider>`, but `AuthContext.tsx`, `ClerkAuthBridge.tsx`, and `RootRedirect.tsx` call Clerk hooks unconditionally. | Make every Clerk hook consumer conditional on `isClerkAuthEnabled()`; return safe legacy defaults when Clerk is disabled. |
| P0-001b | Journeys expect `case-meridian-e2e-001` | E2E seeder only creates `case-draft-001` and `case-e2e-approved-001`. | Add `case-meridian-e2e-001` and its workflow state to `scripts/db/seed-e2e-data.ts`. |
| P0-002 | Image-only Layer 4 rollback fails with `ModuleNotFoundError: No module named 'canonical'` | Old release-smoke image lacks the `canonical` package introduced in the candidate. | Rehearse a source+dependency rollback (or document that production rollback must use immutable commit-pinned images that include the dependency). Update the runbook and evidence. |
| P0-003 | SSO/OIDC validation blocked | No IdP is configured in `docker-compose.live.yml`; OIDC/Clerk secrets are empty. | Add a local Keycloak container to `docker-compose.live.yml`, seed a test realm/client/user, and validate login/logout/tenant mapping. If not feasible, produce explicit blocked evidence. |

---

## 2. Design

### 2.1 Legacy-auth Clerk hook boundary fix

**Principle:** When `VITE_AUTH_PROVIDER=legacy`, no component should invoke Clerk hooks, because `<ClerkProvider>` is not mounted. When `VITE_AUTH_PROVIDER=clerk`, behavior remains unchanged.

**Files to modify:**

1. `apps/web/src/contexts/AuthContext.tsx`
   - Import Clerk hooks lazily or conditionally.
   - In legacy mode, skip Clerk hook calls entirely and return mock/legacy state directly.
   - Keep the existing `isClerkAuthEnabled()` gate logic already present for `mockAuthEnabled`.

2. `apps/web/src/auth/ClerkAuthBridge.tsx`
   - Short-circuit: if `!isClerkAuthEnabled()`, return `null` immediately and do not call `useAuth`/`useOrganization`.

3. `apps/web/src/shell/router.tsx` (`RootRedirect`)
   - Short-circuit: if `!isClerkAuthEnabled()`, skip `useClerkAuth()` and use legacy `AuthContext` state only.

4. `apps/web/src/components/routing/RequireClerkAuth.tsx`
   - Already short-circuits when Clerk is disabled; verify no hook is called before the short-circuit.

**Validation:**
- `VITE_AUTH_PROVIDER=legacy` + `VITE_ENABLE_MOCK_AUTH=true` builds and runs without the `<ClerkProvider>` error.
- `VITE_AUTH_PROVIDER=clerk` + valid key still works.
- Playwright P0 backend-integrated journeys can at least navigate past the auth crash.

### 2.2 E2E seed data fix

**File:** `scripts/db/seed-e2e-data.ts`

**Change:** Add a new seeded business case with id `case-meridian-e2e-001` and the workflow state expected by `j1-golden-path-backend-integrated.spec.ts`.

**Validation:**
- Re-run the seeder against the local Layer 4 API.
- Verify `case-meridian-e2e-001` exists in the database and is reachable from the frontend via the API.

### 2.3 Rollback procedure fix

**File:** `docs/runbooks/deployment-rollout-and-rollback.md`

**Change:** Add a section documenting that production rollback must either:
- Use immutable images built from the target commit (including all new dependencies), or
- Roll back source mounts / dependency layers together with the image.

**Validation:**
- Re-run the rollback drill using a commit-pinned image built from `edb68692946d86e4b6a7574cd94fa4407a64452d` (or the previous release-smoke image rebuilt with `canonical`), and confirm critical-path smoke passes.
- Update `signoff-evidence/p0-rollback-20260613.json` with the new result.

### 2.4 SSO/OIDC local surrogate

**File:** `docker-compose.live.yml`

**Change:** Add a `keycloak` service using the official Keycloak image, expose port 8080, seed a `fabric` realm, a `fabric-web` client, and a test user with a tenant mapping claim.

**Validation:**
- Keycloak admin console reachable at `http://localhost:8080/admin`.
- OIDC discovery endpoint reachable at `http://localhost:8080/realms/fabric/.well-known/openid-configuration`.
- Update `.env.example` with non-secret defaults for local Keycloak.
- Attempt login through the frontend or via curl; capture id/access token, validate signature, verify tenant mapping, invalid token rejected with 401, logout clears session.
- Update `signoff-evidence/p0-sso-20260613.json`.

If Keycloak integration cannot be wired quickly without changing the auth provider code path, we will produce a blocked evidence update with the exact gap.

---

## 3. Testing Strategy

1. **Frontend unit/behavior tests:** Run `pnpm --dir apps/web test` after the Clerk hook fix to ensure no regression in Clerk mode.
2. **Critical-path smoke:** Run `python scripts/e2e/critical_path_smoke.py --host` after all service changes.
3. **Playwright P0:** Run the backend-integrated P0 journeys after the auth and seed fixes.
4. **Rollback drill:** Re-run the rollback procedure with the updated approach.
5. **SSO/OIDC:** Validate Keycloak endpoints and token flow.

---

## 4. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Conditional Clerk hook logic introduces regressions in Clerk mode | Keep Clerk-mode path unchanged; add behavior tests for both modes. |
| Missing seed breaks other journeys | Only add data; do not remove existing seeds. Validate J11 still passes. |
| Keycloak adds significant resource use to local stack | Limit to single instance, 512 MB memory, only start when SSO validation is needed. |
| Re-test window is long | Run targeted validation first, then broaden only after targeted passes. |

---

## 5. Definition of Done

- [ ] Legacy-auth frontend builds and runs without ClerkProvider error.
- [ ] `case-meridian-e2e-001` seed exists and is reachable.
- [ ] P0 Playwright journeys can be re-run (not necessarily all passing, but no longer blocked by auth/seed).
- [ ] Rollback evidence is updated with a viable procedure.
- [ ] SSO/OIDC evidence is updated (either pass with Keycloak or explicit blocked gap).
- [ ] Canonical docs (`docs/readiness/current.md`, `docs/readiness/launch-decision-artifact.md`, `docs/launch/launch-blocker-register.md`) are refreshed.
- [ ] A new commit is made and the candidate is marked re-testable.
