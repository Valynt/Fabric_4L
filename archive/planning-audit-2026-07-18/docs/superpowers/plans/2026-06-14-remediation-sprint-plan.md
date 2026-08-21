# Remediation Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the fixable P0 blockers (legacy-auth ClerkProvider crash, missing E2E seed, deficient rollback procedure, local SSO/OIDC surrogate) so `rc-2026-06-13-116815f3` becomes re-testable.

**Architecture:** Keep all changes additive and environment-facing. Fix Clerk hook boundaries without changing Clerk-mode behavior. Extend the existing E2E seeder. Document/rehearse a viable rollback. Add an optional local Keycloak container to `docker-compose.live.yml`. Update canonical evidence and docs.

**Tech Stack:** React/TypeScript, Vite, Playwright, Python/FastAPI, Docker Compose, Keycloak, Git.

---

## File map

| File | Responsibility |
|---|---|
| `apps/web/src/contexts/AuthContext.tsx` | Conditionally skip Clerk hooks when `VITE_AUTH_PROVIDER=legacy`. |
| `apps/web/src/auth/ClerkAuthBridge.tsx` | Return `null` in legacy mode before calling Clerk hooks. |
| `apps/web/src/shell/router.tsx` | Conditionally skip `useClerkAuth()` in `RootRedirect`. |
| `apps/web/src/components/routing/RequireClerkAuth.tsx` | Verify short-circuit happens before any hook call. |
| `scripts/db/seed-e2e-data.ts` | Add `case-meridian-e2e-001` seed data and workflow state. |
| `docker-compose.live.yml` | Add optional `keycloak` service. |
| `.env.example` | Add safe-default Keycloak/OIDC vars for local surrogate. |
| `docs/runbooks/deployment-rollout-and-rollback.md` | Document viable rollback procedure. |
| `signoff-evidence/p0-rollback-20260613.json` | Update with new rollback evidence. |
| `signoff-evidence/p0-sso-20260613.json` | Update with Keycloak or explicit blocked evidence. |
| `docs/readiness/current.md` | Refresh status. |
| `docs/readiness/launch-decision-artifact.md` | Refresh recommendation. |
| `docs/launch/launch-blocker-register.md` | Update blocker statuses. |

---

## Task 1: Fix Clerk hook boundary in `AuthContext.tsx`

**Files:**
- Modify: `apps/web/src/contexts/AuthContext.tsx`
- Test: `apps/web/src/contexts/AuthContext.behavior.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a behavior test that renders `<AuthProvider>` in legacy mode without `<ClerkProvider>` and asserts no error is thrown.

```tsx
// apps/web/src/contexts/AuthContext.behavior.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { AuthProvider, useAuthContext } from '@/contexts/AuthContext';
import { setAuthProvider } from '@/test/utils/withAuthProvider';

describe('AuthProvider legacy mode', () => {
  it('does not throw when rendered without ClerkProvider', () => {
    setAuthProvider('legacy');
    const { result } = renderHook(() => useAuthContext(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.tenantSlug).toBe('demo');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test AuthContext.behavior.test.tsx`
Expected: FAIL with `@clerk/react: useAuth can only be used within the <ClerkProvider /> component`.

- [ ] **Step 3: Implement conditional Clerk hooks**

Edit `apps/web/src/contexts/AuthContext.tsx` so Clerk hooks are only called when `clerkMode` is true. In legacy/mock mode, return the mock state directly without invoking hooks.

Key changes:
- Move `useClerkAuth`, `useClerkUser`, and `useOrganization` calls behind a conditional that returns safe defaults when `!clerkMode`.
- Keep hooks called unconditionally at the top level when `clerkMode` is true to preserve Rules of Hooks.

Example structure:
```tsx
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const clerkMode = isClerkAuthEnabled();
  const mockAuthEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true' && !clerkMode;

  if (mockAuthEnabled || !clerkMode) {
    const value: AuthContextType = { ...MOCK_USER_INFO_VALUE, ... };
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  const { isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  // ... existing Clerk path
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test AuthContext.behavior.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run full frontend unit tests**

Run: `pnpm --dir apps/web test`
Expected: 1773/1773 pass (or no new failures).

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/contexts/AuthContext.tsx apps/web/src/contexts/AuthContext.behavior.test.tsx
git commit -m "fix(web): conditional Clerk hooks in AuthContext for legacy auth mode"
```

---

## Task 2: Fix Clerk hook boundary in `ClerkAuthBridge.tsx`

**Files:**
- Modify: `apps/web/src/auth/ClerkAuthBridge.tsx`
- Test: `apps/web/src/auth/ClerkAuthBridge.test.tsx`

- [ ] **Step 1: Add legacy-mode guard test**

```tsx
// apps/web/src/auth/ClerkAuthBridge.test.tsx
import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ClerkAuthBridge } from '@/auth/ClerkAuthBridge';
import { setAuthProvider } from '@/test/utils/withAuthProvider';

describe('ClerkAuthBridge legacy mode', () => {
  it('renders null without ClerkProvider', () => {
    setAuthProvider('legacy');
    const { container } = render(<ClerkAuthBridge />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test ClerkAuthBridge.test.tsx`
Expected: FAIL with missing ClerkProvider error.

- [ ] **Step 3: Add top-level legacy short-circuit**

Edit `apps/web/src/auth/ClerkAuthBridge.tsx`:

```tsx
export function ClerkAuthBridge(): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  // ... existing Clerk-mode implementation
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test ClerkAuthBridge.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/auth/ClerkAuthBridge.tsx apps/web/src/auth/ClerkAuthBridge.test.tsx
git commit -m "fix(web): legacy-mode short-circuit in ClerkAuthBridge"
```

---

## Task 3: Fix Clerk hook boundary in `RootRedirect`

**Files:**
- Modify: `apps/web/src/shell/router.tsx`

- [ ] **Step 1: Inspect `RootRedirect`**

Read `apps/web/src/shell/router.tsx` lines 111-132.

- [ ] **Step 2: Add conditional Clerk hook usage**

Change `RootRedirect` to only call `useClerkAuth()` when `isClerkAuthEnabled()` is true:

```tsx
function RootRedirect() {
  const { isAuthenticated: legacyIsAuthenticated, isLoading: legacyIsLoading } = useAuthContext();
  const clerkEnabled = isClerkAuthEnabled();
  const { isLoaded: clerkLoaded, isSignedIn } = clerkEnabled ? useClerkAuth() : { isLoaded: true, isSignedIn: false };

  const isLoading = clerkEnabled ? !clerkLoaded : legacyIsLoading;
  const isAuthenticated = clerkEnabled ? (clerkLoaded && !!isSignedIn) : legacyIsAuthenticated;

  // ... rest unchanged
}
```

- [ ] **Step 3: Verify frontend build**

Run: `pnpm --dir apps/web run build`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/shell/router.tsx
git commit -m "fix(web): conditional Clerk hook in RootRedirect for legacy auth"
```

---

## Task 4: Verify `RequireClerkAuth` short-circuit order

**Files:**
- Modify: `apps/web/src/components/routing/RequireClerkAuth.tsx`

- [ ] **Step 1: Read the file**

Confirm `isClerkAuthEnabled()` check happens before any `useAuth`/`useOrganization` call.

- [ ] **Step 2: Fix if needed**

If hooks are called before the short-circuit, refactor so the top-level `export function RequireClerkAuth` returns early without invoking hooks.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/routing/RequireClerkAuth.tsx
git commit -m "fix(web): ensure RequireClerkAuth short-circuits before Clerk hooks in legacy mode"
```

---

## Task 5: Add `case-meridian-e2e-001` to E2E seeder

**Files:**
- Modify: `scripts/db/seed-e2e-data.ts`

- [ ] **Step 1: Read the seeder**

Identify where `case-draft-001` and `case-e2e-approved-001` are created.

- [ ] **Step 2: Add the new case seed**

Insert a new business case with id `case-meridian-e2e-001` and the workflow state expected by `j1-golden-path-backend-integrated.spec.ts`. Example shape:

```typescript
const meridianCase = {
  id: 'case-meridian-e2e-001',
  name: 'Meridian E2E Case',
  tenant_id: seedTenantId,
  status: 'draft', // or appropriate state for the journey start
  workflow_state: {
    stage: 'opportunity_review',
    // any other fields expected by J1
  },
};
await session.execute(
  text(`INSERT INTO business_cases (id, tenant_id, name, status, workflow_state) VALUES (:id, :tenant_id, :name, :status, :workflow_state)`),
  meridianCase
);
```

- [ ] **Step 3: Run the seeder against local Layer 4**

Run:
```bash
SERVICE_AUTH_SECRET=dummy_service_auth_secret_for_tests_32_chars npx tsx scripts/db/seed-e2e-data.ts --base-url=http://localhost:8004
```

Expected: exit 0; `case-meridian-e2e-001` exists.

- [ ] **Step 4: Verify via API**

Run:
```bash
curl -s -H "Authorization: Bearer <service-jwt>" "http://localhost:8004/api/v1/business-cases/case-meridian-e2e-001" | python -m json.tool
```

Expected: returns the case.

- [ ] **Step 5: Commit**

```bash
git add scripts/db/seed-e2e-data.ts
git commit -m "chore(e2e): add case-meridian-e2e-001 seed for J1 golden path"
```

---

## Task 6: Re-run Playwright P0 backend-integrated journeys

**Files:**
- Create: `signoff-evidence/e2e/e2e-live-p0-20260614.json` (or update existing)

- [ ] **Step 1: Rebuild frontend**

```bash
pnpm --dir apps/web run build
```

- [ ] **Step 2: Restart frontend container**

```bash
docker compose -f docker-compose.live.yml --env-file .env up -d --build frontend
```

- [ ] **Step 3: Run the seeder**

```bash
SERVICE_AUTH_SECRET=dummy_service_auth_secret_for_tests_32_chars npx tsx scripts/db/seed-e2e-data.ts --base-url=http://localhost:8004
```

- [ ] **Step 4: Run P0 backend-integrated tests**

```bash
cd apps/web
E2E_SEED_DATA=false SERVICE_AUTH_SECRET=dummy_service_auth_secret_for_tests_32_chars npx playwright test --project=backend-integrated e2e/journeys/j1-golden-path-backend-integrated.spec.ts e2e/journeys/j11-business-case-lifecycle-backend-integrated.spec.ts
```

- [ ] **Step 5: Record evidence**

Write the result to `signoff-evidence/e2e/e2e-live-p0-20260614.json` with summary, passed/failed counts, and any remaining blockers.

- [ ] **Step 6: Commit**

```bash
git add signoff-evidence/e2e/e2e-live-p0-20260614.json
git commit -m "test(e2e): re-run P0 backend-integrated journeys after auth/seed fixes"
```

---

## Task 7: Rehearse viable rollback procedure

**Files:**
- Modify: `docs/runbooks/deployment-rollout-and-rollback.md`
- Modify: `signoff-evidence/p0-rollback-20260613.json`

- [ ] **Step 1: Document the procedure**

Add a section to the runbook stating that production rollback must use images built from the target commit including all dependencies, or roll back source mounts together with images. Do not rely on source-mount overlays across versions.

- [ ] **Step 2: Build a commit-pinned rollback image**

```bash
git checkout edb68692946d86e4b6a7574cd94fa4407a64452d
docker build -t fabric_4l-layer4:rollback-pinned -f services/layer4-agents/Dockerfile.live .
git checkout main
```

- [ ] **Step 3: Re-run rollback drill**

```bash
docker tag fabric_4l-layer4:rollback-pinned fabric_4l-layer4:latest
docker compose -f docker-compose.live.yml --env-file .env up -d --no-build layer4
sleep 20
curl -fsS http://localhost:8004/ready
PYTHONIOENCODING=utf-8 E2E_SERVICE_AUTH_SECRET=dummy_service_auth_secret_for_tests_32_chars python scripts/e2e/critical_path_smoke.py --host
```

- [ ] **Step 4: Update rollback evidence**

Update `signoff-evidence/p0-rollback-20260613.json` with the new rollback image, commands, timing, and PASS result. Keep the previous failure as historical context.

- [ ] **Step 5: Restore latest image**

```bash
docker compose -f docker-compose.live.yml --env-file .env up -d --build layer4
```

- [ ] **Step 6: Commit**

```bash
git add docs/runbooks/deployment-rollout-and-rollback.md signoff-evidence/p0-rollback-20260613.json
git commit -m "docs(ops): document and verify viable rollback procedure"
```

---

## Task 8: Add local Keycloak SSO/OIDC surrogate

**Files:**
- Modify: `docker-compose.live.yml`
- Modify: `.env.example`
- Create: `scripts/keycloak/keycloak-realm-config.json`
- Modify: `signoff-evidence/p0-sso-20260613.json`

- [ ] **Step 1: Add Keycloak service to compose**

In `docker-compose.live.yml`, add:

```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:25.0
    container_name: vf-live-keycloak
    command: ["start-dev", "--import-realm"]
    environment:
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USER:-admin}
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
      KC_HTTP_PORT: 8080
    volumes:
      - ./scripts/keycloak/keycloak-realm-config.json:/opt/keycloak/data/import/fabric-realm.json:ro
    ports:
      - 8080:8080
    networks:
      - live-network
    healthcheck:
      test: ["CMD-SHELL", "exec 3<<<EOF; echo -e 'GET /health/ready HTTP/1.1\r\nHost: localhost\r\n\r' >&3; timeout 5 cat <&3 | grep -q '200 OK'"]
      interval: 10s
      timeout: 5s
      retries: 10
```

- [ ] **Step 2: Create realm config**

Create `scripts/keycloak/keycloak-realm-config.json` with:
- Realm `fabric`
- Client `fabric-web` with redirect URI `http://localhost:3001/*`
- Test user `e2e-user@valuepact.ai` / password `e2e-password`
- Group/role mapping to tenant slug `demo`

- [ ] **Step 3: Update `.env.example`**

Add safe defaults:
```bash
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=fabric
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=admin
OIDC_ISSUER=http://localhost:8080/realms/fabric
OIDC_JWKS_URL=http://localhost:8080/realms/fabric/protocol/openid-connect/certs
OIDC_AUDIENCE=fabric-web
```

- [ ] **Step 4: Start Keycloak**

```bash
docker compose -f docker-compose.live.yml --env-file .env up -d keycloak
```

- [ ] **Step 5: Validate OIDC discovery**

```bash
curl -fsS http://localhost:8080/realms/fabric/.well-known/openid-configuration | python -m json.tool
```

Expected: returns JSON with `authorization_endpoint`, `token_endpoint`, `jwks_uri`.

- [ ] **Step 6: Validate token flow via client credentials or password grant**

```bash
curl -X POST http://localhost:8080/realms/fabric/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=fabric-web' \
  -d 'username=e2e-user@valuepact.ai' \
  -d 'password=e2e-password' \
  -d 'scope=openid'
```

Expected: returns access_token, id_token, refresh_token.

- [ ] **Step 7: Verify invalid token rejected**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer invalid" http://localhost:8004/api/v1/workflows
```

Expected: 401.

- [ ] **Step 8: Update SSO evidence**

Update `signoff-evidence/p0-sso-20260613.json` to `PASS` (or `PARTIAL` if frontend login is not fully wired) with discovery, token, and rejection evidence.

- [ ] **Step 9: Commit**

```bash
git add docker-compose.live.yml .env.example scripts/keycloak/keycloak-realm-config.json signoff-evidence/p0-sso-20260613.json
git commit -m "feat(ops): add local Keycloak SSO/OIDC surrogate for staging validation"
```

---

## Task 9: Update canonical readiness docs

**Files:**
- Modify: `docs/readiness/current.md`
- Modify: `docs/readiness/launch-decision-artifact.md`
- Modify: `docs/launch/launch-blocker-register.md`

- [ ] **Step 1: Update `docs/readiness/current.md`**

- Mark P0-001, P0-002, P0-003 as resolved/re-testable.
- Update launch recommendation to **CONDITIONALLY RE-TESTABLE** or **GO WITH ACCEPTED RISKS** depending on results.

- [ ] **Step 2: Update `docs/readiness/launch-decision-artifact.md`**

- Add runtime certification re-test evidence.
- Update final recommendation based on actual re-test results.

- [ ] **Step 3: Update `docs/launch/launch-blocker-register.md`**

- Update P0-001, P0-002, P0-003 statuses and evidence links.

- [ ] **Step 4: Commit**

```bash
git add docs/readiness/current.md docs/readiness/launch-decision-artifact.md docs/launch/launch-blocker-register.md
git commit -m "docs(readiness): update launch artifacts after remediation sprint"
```

---

## Task 10: Final verification gate

- [ ] **Step 1: Run critical-path smoke**

```bash
PYTHONIOENCODING=utf-8 E2E_SERVICE_AUTH_SECRET=dummy_service_auth_secret_for_tests_32_chars python scripts/e2e/critical_path_smoke.py --host
```

Expected: PASS 12/0.

- [ ] **Step 2: Run frontend tests**

```bash
pnpm --dir apps/web test
```

Expected: no new failures.

- [ ] **Step 3: Run static rollback verifier**

```bash
python scripts/ci/verify_release_rollback.py
```

Expected: PASS 8/8.

- [ ] **Step 4: Summarize and close**

Update `docs/superpowers/specs/2026-06-14-remediation-sprint-design.md` with final results and mark the sprint complete.

---

## Self-review

- **Spec coverage:**
  - P0-001 legacy auth boundary → Tasks 1-4.
  - P0-001b missing seed → Task 5.
  - P0-001 validation → Task 6.
  - P0-002 rollback → Task 7.
  - P0-003 SSO/OIDC → Task 8.
  - Docs/evidence update → Task 9.
  - Final verification → Task 10.
- **Placeholder scan:** No TBD/TODO; exact commands and file paths provided.
- **Type consistency:** `isClerkAuthEnabled()` used consistently; `case-meridian-e2e-001` matches test expectation.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-14-remediation-sprint-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach do you want to use?
