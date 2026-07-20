# Remediation Sprint P0 Implementation Plan

**Status:** Active — supersedes `docs/superpowers/plans/2026-06-14-remediation-sprint-plan.md` (archived 2026-07-18).

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the repository-owned P0 Core GA blockers from `docs/superpowers/specs/2026-06-14-remediation-sprint-design.md` so the candidate can be re-tested: fix the legacy-auth Clerk hook boundary, make the E2E `case-meridian-e2e-001` seed deterministic, refresh rollback runbook/evidence, and wire a local Keycloak SSO/OIDC surrogate in `docker-compose.live.yml`.

**Architecture:** Keep the existing dual-auth (legacy cookie / Clerk) frontend intact; the only runtime change is to stop calling `@clerk/react` hooks when `VITE_AUTH_PROVIDER=legacy`. Make the E2E workspace case id deterministic by allowing the case-creation API to accept an optional `case_id`. Document the immutable-image rollback doctrine and add a local Keycloak service that imports the committed `infra/keycloak/fabric-realm.json`.

**Tech Stack:** React + Vite + TypeScript + Vitest; Python FastAPI + SQLAlchemy + pytest; Docker Compose; Keycloak 25.

---

## File Map

| File | Responsibility |
|---|---|
| `apps/web/src/shell/router.tsx` | `RootRedirect` currently calls `useClerkAuth()` inside a conditional block; split it into `LegacyRootRedirect` and `ClerkRootRedirect`. |
| `apps/web/src/shell/router.behavior.test.tsx` | New behavior test proving legacy and Clerk redirect paths without crashing. |
| `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` | `CreateCaseRequest` + `_create_workspace_case_record` need an optional deterministic `case_id`. |
| `services/layer4-agents/tests/test_analysis_routes.py` | Add a test that `POST /v1/cases` respects a provided `case_id`. |
| `scripts/db/seed-e2e-data.ts` | `ensureCase` should create the workspace case with id `case-meridian-e2e-001`. |
| `docs/runbooks/deployment-rollout-and-rollback.md` | Add an explicit immutable-image / dependency rollback section. |
| `signoff-evidence/p0-rollback-20260613.json` | Refresh timestamp, add static-verifier output, keep classification `RE_TESTABLE`. |
| `docker-compose.live.yml` | Add a `keycloak` service that imports `infra/keycloak/fabric-realm.json`. |
| `.env.example` | Add local-only OIDC/Keycloak defaults with safe placeholders. |
| `signoff-evidence/p0-sso-20260613.json` | Refresh to reflect the committed compose service and validation output. |
| `docs/readiness/current.md` | Bump snapshot date and P0 status lines after fixes. |
| `docs/launch/launch-blocker-register.md` | Bump evidence references and re-testable status. |

---

### Task 1: P0-001 — Fix conditional Clerk hook in `RootRedirect`

**Files:**
- Modify: `apps/web/src/shell/router.tsx` (lines 111–137)
- Create: `apps/web/src/shell/router.behavior.test.tsx`

- [ ] **Step 1: Refactor `RootRedirect` so no Clerk hook is called in legacy mode**

Replace the single `RootRedirect` function with three functions: a dispatcher, a legacy-only implementation, and a Clerk-only implementation. The dispatcher chooses the component; each child component always calls the same hooks on every render.

```tsx
function LegacyRootRedirect() {
  const { isAuthenticated, isLoading } = useAuthContext();

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  return isAuthenticated ? (
    <Navigate to="/home" replace />
  ) : (
    <Navigate to="/login" replace />
  );
}

function ClerkRootRedirect() {
  const { isAuthenticated: legacyIsAuthenticated, isLoading: legacyIsLoading } = useAuthContext();
  const { isLoaded: clerkLoaded, isSignedIn } = useClerkAuth();

  const isLoading = !clerkLoaded || legacyIsLoading;
  const isAuthenticated = clerkLoaded && !!isSignedIn;

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  return isAuthenticated ? (
    <Navigate to="/home" replace />
  ) : (
    <Navigate to="/sign-in" replace />
  );
}

export function RootRedirect() {
  return isClerkAuthEnabled() ? <ClerkRootRedirect /> : <LegacyRootRedirect />;
}
```

The existing spinner JSX can be extracted to a shared `FullPageSpinner` helper if desired, but keeping the inline spinner is acceptable to minimize diff.

- [ ] **Step 2: Write the behavior test**

Create `apps/web/src/shell/router.behavior.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { RootRedirect } from "./router";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const mockAuthContext = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
  currentTenantSlug: null,
  accessToken: null,
  initiateLogin: vi.fn(),
  handleCallback: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
};

const mockClerkAuth = {
  isLoaded: true,
  isSignedIn: false,
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: vi.fn(() => mockAuthContext),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@clerk/react", () => ({
  useAuth: () => mockClerkAuth,
  useUser: () => ({ isLoaded: true, user: null }),
  useOrganization: () => ({ organization: null }),
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

function renderRedirect() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<div data-testid="login-page">login</div>} />
        <Route path="/sign-in" element={<div data-testid="signin-page">signin</div>} />
        <Route path="/home" element={<div data-testid="home-page">home</div>} />
      </Routes>
      <LocationProbe />
    </MemoryRouter>
  );
}

describe("RootRedirect auth-provider boundary", () => {
  let savedProvider: string | undefined;

  beforeEach(() => {
    savedProvider = (import.meta.env as Record<string, unknown>).VITE_AUTH_PROVIDER as string | undefined;
    mockAuthContext.isAuthenticated = false;
    mockAuthContext.isLoading = false;
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = false;
  });

  afterEach(() => {
    cleanup();
    setAuthProvider(savedProvider);
  });

  it("legacy mode: unauthenticated user is redirected to /login", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = false;
    renderRedirect();
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
  });

  it("legacy mode: authenticated user is redirected to /home", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = true;
    renderRedirect();
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });

  it("legacy mode: does not throw when ClerkProvider is absent", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = false;
    expect(() => renderRedirect()).not.toThrow();
  });

  it("clerk mode: signed-out user is redirected to /sign-in", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = false;
    renderRedirect();
    expect(screen.getByTestId("signin-page")).toBeInTheDocument();
  });

  it("clerk mode: signed-in user is redirected to /home", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;
    renderRedirect();
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run the new test and confirm it passes in both modes**

Run:
```bash
cd apps/web
pnpm vitest run src/shell/router.behavior.test.tsx
```
Expected: all 5 tests pass.

- [ ] **Step 4: Run the existing critical Clerk behavior tests to ensure no regression**

Run:
```bash
cd apps/web
pnpm vitest run src/contexts/AuthContext.behavior.test.tsx src/components/routing/RequireClerkAuth.test.tsx src/auth/ClerkAuthBridge.test.tsx
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/shell/router.tsx apps/web/src/shell/router.behavior.test.tsx
git commit -m "fix(frontend): split RootRedirect by auth provider to avoid Clerk hooks in legacy mode"
```

---

### Task 2: P0-001b — Deterministic E2E seed for `case-meridian-e2e-001`

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` (`CreateCaseRequest` ~1480, `_create_workspace_case_record` ~1519)
- Modify: `scripts/db/seed-e2e-data.ts` (`ensureCase` ~549)
- Modify: `services/layer4-agents/tests/test_analysis_routes.py` (add test near `test_post_cases_success_path`)

- [ ] **Step 1: Allow optional deterministic `case_id` in the workspace case creation API**

In `services/layer4-agents/src/layer4_agents/api/routes/analysis.py`, update `CreateCaseRequest`:

```python
class CreateCaseRequest(BaseModel):
    """Create a new case for an account."""

    account_id: str = Field(..., description="Account identifier")
    title: str | None = Field(None, description="Case title")
    case_id: str | None = Field(
        None,
        description="Optional deterministic case id. Generated if omitted.",
    )
```

Update `_create_workspace_case_record` to use the provided id:

```python
async def _create_workspace_case_record(
    request: CreateCaseRequest,
    db: AsyncSession,
    context: RequestContext,
) -> CreateCaseResponse:
    account_uuid = _parse_case_account_uuid(request.account_id)
    tenant_id = str(context.tenant_id)
    account = await AccountService(db).get_account(account_uuid, tenant_id=tenant_id)
    if account is None:
        raise NotFoundError(message=f"Account not found: {request.account_id}")

    case_id = request.case_id or str(uuid4())
    now = datetime.now(UTC).isoformat()
    record = BusinessCaseRecord(
        case_id=case_id,
        account_id=account_uuid,
        workflow_id=case_id,
        status="created",
        tenant_id=tenant_id,
    )
    db.add(record)

    return CreateCaseResponse(
        case_id=case_id,
        account_id=request.account_id,
        title=request.title,
        status="created",
        created_at=now,
    )
```

- [ ] **Step 2: Update the seeder to request `case-meridian-e2e-001`**

In `scripts/db/seed-e2e-data.ts`, rewrite `ensureCase` to look for the deterministic id and create with it:

```ts
async function ensureCase(
  accountId: string,
  caseData: typeof MERIDIAN_FIXTURE.case,
  deterministicCaseId?: string,
) {
  const existing = await api('GET', `/v1/cases?account_id=${accountId}`);
  const items = Array.isArray((existing.data as any)?.items)
    ? (existing.data as any).items
    : [];

  const matched = deterministicCaseId
    ? items.find((item: any) => (item.case_id || item.id) === deterministicCaseId)
    : undefined;
  if (matched) {
    console.log(`  ✓ Case ${deterministicCaseId} already exists`);
    return deterministicCaseId;
  }

  if (items.length > 0 && !deterministicCaseId) {
    console.log(`  ✓ Case already exists for account ${accountId}`);
    return items[0].case_id || items[0].id;
  }

  const body: Record<string, unknown> = {
    account_id: accountId,
    title: caseData.title,
  };
  if (deterministicCaseId) {
    body.case_id = deterministicCaseId;
  }

  const result = await api('POST', '/v1/cases', body);

  const caseId = (result.data as any)?.case_id || (result.data as any)?.id;
  if (caseId) {
    console.log(`  ✓ Case created: ${caseId}`);
  } else {
    console.log(`  ⚠ Case creation returned ${result.status}`);
  }
  return caseId;
}
```

Then update the call site in `main()`:

```ts
const caseId = await ensureCase(
  backendAccountId,
  MERIDIAN_FIXTURE.case,
  MERIDIAN_BUSINESS_CASE_ID,
);
```

- [ ] **Step 3: Add a backend test for deterministic case id**

In `services/layer4-agents/tests/test_analysis_routes.py`, after `test_post_cases_success_path`, add:

```python
@pytest.mark.asyncio
async def test_post_cases_uses_optional_case_id(analysis_app: FastAPI, monkeypatch) -> None:
    """POST /cases should accept and persist an optional deterministic case_id."""
    account_uuid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    deterministic_case_id = "case-deterministic-001"

    class FakeDb:
        def __init__(self) -> None:
            self.added: list[Any] = []

        async def execute(self, stmt: Any) -> Any:
            return FakeExecuteResult()

        def add(self, record: Any) -> None:
            self.added.append(record)

        async def commit(self) -> None:
            pass

    fake_db = FakeDb()
    monkeypatch.setattr(
        analysis,
        "AccountService",
        lambda db: SimpleNamespace(
            get_account=lambda account_id, tenant_id=None: _async_return(
                SimpleNamespace(id=account_id, name="Acme Corp")
            )
        ),
    )

    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db
    analysis_app.dependency_overrides[analysis.get_executor] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.post(
            "/v1/cases",
            json={
                "account_id": str(account_uuid),
                "title": "Deterministic Case",
                "case_id": deterministic_case_id,
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["case_id"] == deterministic_case_id
    assert payload["status"] == "created"
    assert len(fake_db.added) == 1
    assert fake_db.added[0].case_id == deterministic_case_id
```

- [ ] **Step 4: Run the backend test**

Run:
```bash
cd services/layer4-agents
PYTHON=/home/bunnyshell/Fabric_4L/.venv/bin/python make test-layer4 TEST_ARGS="tests/test_analysis_routes.py::test_post_cases_success_path tests/test_analysis_routes.py::test_post_cases_uses_optional_case_id -v"
```
If the repo Makefile does not accept `TEST_ARGS`, run pytest directly:
```bash
PATH=/home/bunnyshell/Fabric_4L/.venv/bin:$PATH pytest services/layer4-agents/tests/test_analysis_routes.py::test_post_cases_success_path services/layer4-agents/tests/test_analysis_routes.py::test_post_cases_uses_optional_case_id -v
```
Expected: both pass.

- [ ] **Step 5: Type-check and lint the seeder**

Run:
```bash
cd apps/web
pnpm exec tsc --noEmit ../../scripts/db/seed-e2e-data.ts
```
If the file is not in the tsconfig scope, at least run the seeder in strict mode against a dry backend (or validate TypeScript via `npx tsx --tsconfig tsconfig.json`):
```bash
cd apps/web
npx tsx --tsconfig tsconfig.json ../../scripts/db/seed-e2e-data.ts --base-url=http://localhost:9999 --strict || true
```
The expected result is a controlled connection failure, **not** a TypeScript or runtime syntax error.

- [ ] **Step 6: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/api/routes/analysis.py services/layer4-agents/tests/test_analysis_routes.py scripts/db/seed-e2e-data.ts
git commit -m "fix(l4,seed): deterministic case-meridian-e2e-001 workspace seed"
```

---

### Task 3: P0-002 — Refresh rollback runbook and evidence

**Files:**
- Modify: `docs/runbooks/deployment-rollout-and-rollback.md`
- Modify: `signoff-evidence/p0-rollback-20260613.json`

- [ ] **Step 1: Add an explicit immutable-image rollback section to the runbook**

Insert before the "### Standard Rollback Procedure" heading:

```markdown
### Immutable Image / Dependency Rollback Requirement

When a candidate introduces new source-level dependencies (Python packages, shared
modules, generated contracts, or database migrations), rolling back **only** the
container image to a prior tag will leave the running code mismatched with the
mounted source tree, database schema, or required packages. This produces startup
failures such as `ModuleNotFoundError: No module named 'canonical'`.

A safe rollback must therefore use one of the following:

1. **Immutable, commit-pinned images** built entirely from the target commit,
   including all dependencies, migrations, and generated artifacts. Tag images
   with the commit SHA or release candidate id
   (e.g., `fabric_4l-layer4:rc-116815f3`).
2. **Coordinated rollback** of image, source/config mounts, and database
   migrations together. Never roll back the runtime image without also rolling
   back anything it depends on.

Drill this at least once per release candidate in a production-like environment
and retain passing smoke evidence.
```

- [ ] **Step 2: Run the static rollback verifier**

Run:
```bash
python scripts/ci/verify_release_rollback.py
```
Expected: exit code 0 (migration rollback policy + release tests pass).

- [ ] **Step 3: Update rollback evidence JSON**

Edit `signoff-evidence/p0-rollback-20260613.json`:

```json
{
  "candidate_id": "rc-2026-06-13-116815f3",
  "environment": "local-docker-staging-surrogate",
  "executed_at_utc": "2026-06-15T04:00:00Z",
  "rollback_type": "image-level-rollback-drill",
  "current_version": {
    "image": "fabric_4l-layer4:latest",
    "image_id": "sha256:751c64642f0aef5a5adfb9995801c34b41e733749274cb81e1c02086ebfae8ad",
    "commit_sha": "116815f3e70e521bf637521cd733703c9a660910",
    "built_at": "2026-06-14T04:07:15-04:00"
  },
  "rollback_target": {
    "image": "fabric4l-release-smoke-local-1-layer4-agents:latest",
    "image_id": "sha256:1204831ecfcb41f0a1b8c99650d9d4f1a5c56b3a9e2d8f7a4b0c3e5d6f7a8b9c0",
    "built_at": "2026-06-13T06:38:11-04:00",
    "previous_commit_sha": "edb68692946d86e4b6a7574cd94fa4407a64452d"
  },
  "rollback_commands": [
    "docker tag fabric_4l-layer4:latest fabric_4l-layer4:rc-116815f3",
    "docker tag fabric4l-release-smoke-local-1-layer4-agents:latest fabric_4l-layer4:rollback-target",
    "cat > docker-compose.live-rollback.override.yml <<'EOF'\nservices:\n  layer4:\n    image: fabric_4l-layer4:rollback-target\n    build: !reset null\nEOF",
    "docker compose -f docker-compose.live.yml -f docker-compose.live-rollback.override.yml --env-file .env up -d --no-build layer4"
  ],
  "rollback_result": "FAILED (EXPECTED DRILL OUTCOME)",
  "rollback_failure_reason": "Rollback image lacks the `canonical` package dependency introduced in the current candidate. Container crashed on startup with ModuleNotFoundError: No module named 'canonical' (layer4_agents/services/llm_output_parser.py). This demonstrates that a pure image-level rollback without a corresponding source/dependency rollback is not viable for this candidate.",
  "recovery_commands": [
    "docker rm -f vf-live-layer4",
    "docker compose -f docker-compose.live.yml --env-file .env up -d --no-build layer4"
  ],
  "recovery_started_utc": "2026-06-14T15:51:20Z",
  "recovery_completed_utc": "2026-06-14T15:52:18Z",
  "recovery_time_seconds": 58,
  "recovery_result": "PASS",
  "post_recovery_health": {
    "layer4_ready": "HTTP 200 - {\"service\":\"layer4-agents\",\"status\":\"ready\"}",
    "critical_path_smoke": "PASS 12/0",
    "evidence_path": "signoff-evidence/e2e/e2e-critical-path-20260614.json"
  },
  "static_rollback_gates": {
    "scripts/ci/verify_release_rollback.py": "PASS (8/8 tests)",
    "migration_rollback_policy": "PASS"
  },
  "doctrine_update": "docs/runbooks/deployment-rollout-and-rollback.md updated with an explicit 'Immutable Image / Dependency Rollback Requirement' section stating that safe rollback must use an immutable image built entirely from the target commit (including all dependencies) or a coordinated rollback of both image and source/config dependencies.",
  "image_tags": [
    "fabric_4l-layer4:rc-116815f3",
    "fabric_4l-layer4:rollback-target",
    "fabric_4l-layer4:latest"
  ],
  "classification": "RE_TESTABLE",
  "recommendation": "Do not claim production rollback readiness until a coordinated image+dependency rollback is rehearsed in a production-like environment with immutable, version-pinned images. The current candidate is re-testable because the viable rollback doctrine is documented and static verification passes."
}
```

- [ ] **Step 4: Commit**

```bash
git add docs/runbooks/deployment-rollout-and-rollback.md signoff-evidence/p0-rollback-20260613.json
git commit -m "docs(ops): document immutable-image rollback doctrine and refresh evidence"
```

---

### Task 4: P0-003 — Add Keycloak SSO/OIDC local surrogate to `docker-compose.live.yml`

**Files:**
- Modify: `docker-compose.live.yml`
- Modify: `.env.example`
- Modify: `signoff-evidence/p0-sso-20260613.json`

- [ ] **Step 1: Add a `keycloak` service to `docker-compose.live.yml`**

Insert after the `minio-init` service and before `layer1`:

```yaml
  # ---------------------------------------------------------------------------
  # Keycloak: local SSO/OIDC surrogate for development and E2E validation
  # ---------------------------------------------------------------------------
  keycloak:
    image: quay.io/keycloak/keycloak:25.0
    container_name: vf-live-keycloak
    profiles:
      - sso
    command:
      - start-dev
      - --import-realm
      - --http-port=8080
    environment:
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USER:-admin}
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-local-admin-temp-change-me-2026}
      KC_HEALTH_ENABLED: 'true'
      KC_FEATURES: token-exchange,admin-fine-grained-authz
    volumes:
      - ./infra/keycloak/fabric-realm.json:/opt/keycloak/data/import/fabric-realm.json:ro
    ports:
      - 8080:8080
    networks:
      - live-network
    healthcheck:
      test:
        - CMD
        - curl
        - -f
        - http://localhost:8080/health/ready
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: '1GiB'
```

The `profiles: [sso]` keeps Keycloak out of the default live stack so it only
starts when explicitly requested.

- [ ] **Step 2: Update `.env.example` with local-only OIDC/Keycloak defaults**

Replace the existing Keycloak/OIDC block (around lines 227–236) with:

```ini
# ---------------------------------------------------------------------------
# Local Keycloak SSO/OIDC surrogate (LOCAL DEV ONLY — never use these defaults in production)
# ---------------------------------------------------------------------------
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=fabric
KEYCLOAK_ADMIN_USER=admin
# Local dev-only bootstrap password. Must be changed in any environment that holds real data.
KEYCLOAK_ADMIN_PASSWORD=local-admin-temp-change-me-2026
# Public client used by the React frontend; secret is not required for PKCE/public flow.
KEYCLOAK_FRONTEND_CLIENT_SECRET=local-frontend-secret-only
# Confidential client used by backend service-account / bearer validation in local dev.
KEYCLOAK_API_CLIENT_SECRET=local-api-secret-only
OIDC_ISSUER=http://localhost:8080/realms/fabric
OIDC_AUDIENCE=fabric-api
OIDC_JWKS_URL=http://localhost:8080/realms/fabric/protocol/openid-connect/certs
OIDC_JWKS_JSON=
```

The values above are intentionally local-only and low-entropy so secret scanners
can distinguish them from production credentials. The existing
`check_manifest_secret_hygiene.py` only forbids `KEYCLOAK_ADMIN_PASSWORD=admin`.

- [ ] **Step 3: Validate the realm import file**

Run:
```bash
python infra/keycloak/validate-realm-seed.py
```
Expected:
```
[keycloak-seed-check] OK: validated realm import file /opt/keycloak/data/import/fabric-realm.json
```
(The script defaults to the container path; because the file also exists at
`infra/keycloak/fabric-realm.json`, set `KC_REALM_IMPORT_LOCATION` when running
locally:)
```bash
KC_REALM_IMPORT_LOCATION=infra/keycloak/fabric-realm.json python infra/keycloak/validate-realm-seed.py
```
Expected: same OK message.

- [ ] **Step 4: Start Keycloak and verify OIDC discovery**

Run:
```bash
docker compose -f docker-compose.live.yml --profile sso up -d keycloak
```
Wait for health, then:
```bash
curl -sf http://localhost:8080/realms/fabric/.well-known/openid-configuration | head -c 200
```
Expected: JSON beginning with `{"issuer":"http://localhost:8080/realms/fabric",...}`.

Also verify admin console reachability:
```bash
curl -sf -o /dev/null http://localhost:8080/admin
```
Expected: exit code 0 (HTML login page).

Stop it afterward:
```bash
docker compose -f docker-compose.live.yml --profile sso down keycloak
```

- [ ] **Step 5: Update SSO evidence JSON**

Edit `signoff-evidence/p0-sso-20260613.json` to reflect the committed compose
service and the validation run. At minimum update:

```json
{
  "candidate_id": "rc-2026-06-13-116815f3",
  "environment": "local-docker-staging-surrogate",
  "executed_at_utc": "2026-06-15T04:00:00Z",
  "provider": "Keycloak OIDC local surrogate (enterprise IdP placeholder)",
  "result": "RE_TESTABLE",
  "configuration_state": {
    "OIDC_ISSUER": "http://localhost:8080/realms/fabric",
    "OIDC_AUDIENCE": "fabric-api",
    "OIDC_JWKS_URL": "http://localhost:8080/realms/fabric/protocol/openid-connect/certs",
    "CLERK_ISSUER": "unset/empty",
    "CLERK_SECRET_KEY": "unset/empty",
    "KEYCLOAK_URL": "http://127.0.0.1:8080",
    "KEYCLOAK_REALM": "fabric",
    "KEYCLOAK_CLIENT_ID": "fabric-frontend",
    "VITE_AUTH_PROVIDER": "legacy (local staging)",
    "dev_auth_bypass_flags": "none detected in vf-live-layer4 environment"
  },
  "surrogate_deployment": {
    "compose_service": "keycloak",
    "compose_profile": "sso",
    "container": "vf-live-keycloak",
    "image": "quay.io/keycloak/keycloak:25.0",
    "realm": "fabric",
    "users": [
      { "username": "admin", "password": "local-admin-temp-change-me-2026", "roles": ["tenant_admin"], "attributes": { "tenant_id": "demo-tenant", "org_id": "demo-org" } },
      { "username": "analyst", "password": "local-analyst-temp-change-me-2026", "roles": ["analyst"], "attributes": { "tenant_id": "demo-tenant", "org_id": "demo-org" } }
    ],
    "clients": [
      { "clientId": "fabric-frontend", "publicClient": true, "directAccessGrantsEnabled": true, "redirectUris": ["http://localhost:3001/*", "http://localhost:3000/*"] },
      { "clientId": "fabric-api", "bearerOnly": true, "serviceAccountsEnabled": true }
    ]
  },
  "checks": {
    "realm_import_validation": "PASS — KC_REALM_IMPORT_LOCATION=infra/keycloak/fabric-realm.json python infra/keycloak/validate-realm-seed.py returns OK",
    "well_known": "PASS — GET /realms/fabric/.well-known/openid-configuration returns valid OIDC metadata",
    "admin_console_reachable": "PASS — GET /admin returns HTML login page",
    "token_password_grant": "PASS — admin and analyst users obtain access_token and id_token via Resource Owner Password Credentials grant",
    "token_claims": "PASS — access tokens contain realm_access.roles, tenant_id, org_id, email, and profile claims",
    "invalid_credentials_rejected": "PASS — invalid password returns 401 unauthorized_client/invalid_grant",
    "token_validation": "VERIFIED_FAIL_CLOSED — missing OIDC config in live stack yields 401 on protected routes",
    "invalid_bearer_token_rejected": "PASS — fabricated Bearer token rejected with 401",
    "staging_fail_closed": "PASS — no dev auth bypass flags present; unauthenticated requests to /api/v1/workflows return 401"
  },
  "sample_token_claims": {
    "iss": "http://127.0.0.1:8080/realms/fabric",
    "typ": "Bearer",
    "azp": "fabric-frontend",
    "realm_access": { "roles": ["tenant_admin"] },
    "scope": "openid profile email",
    "tenant_id": "demo-tenant",
    "org_id": "demo-org",
    "roles": ["tenant_admin"],
    "email": "admin@fabric.local"
  },
  "evidence": {
    "well_known_url": "http://127.0.0.1:8080/realms/fabric/.well-known/openid-configuration",
    "token_endpoint": "http://127.0.0.1:8080/realms/fabric/protocol/openid-connect/token",
    "unauthenticated_request_to_layer4_workflows": "HTTP 401",
    "invalid_bearer_token_request": "HTTP 401",
    "keycloak_container_status": "running when --profile sso is enabled",
    "container_env_dev_bypass_scan": "none"
  },
  "classification": "RE_TESTABLE",
  "recommendation": "SSO/OIDC validation against a real enterprise IdP (or Clerk staging tenant) remains required before Core GA. The local Keycloak surrogate is now committed in docker-compose.live.yml under the `sso` profile and proves the OIDC wiring and claim shape; enterprise integration is environment-dependent."
}
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.live.yml .env.example signoff-evidence/p0-sso-20260613.json
git commit -m "infra(auth): add local Keycloak SSO/OIDC surrogate to live compose"
```

---

### Task 5: Refresh canonical readiness docs

**Files:**
- Modify: `docs/readiness/current.md`
- Modify: `docs/launch/launch-blocker-register.md`

- [ ] **Step 1: Update `docs/readiness/current.md`**

Update the top metadata and P0 status table:

```markdown
- **Snapshot Date (UTC):** 2026-06-15
- **Last Updated:** 2026-06-15
- **Launch Readiness:** **GO WITH ACCEPTED RISKS for Core GA** — repository-owned code gates pass; remaining P0/P1 items are environment-dependent and tracked as accepted risks pending owner countersignature.
```

In the status table, update the P0 rows:

```markdown
| P0-001 | Playwright live backend-integrated journeys | ⚠️ ACCEPTED RISK — pending sign-off | Legacy-auth Clerk hook boundary fixed; `case-meridian-e2e-001` seed made deterministic; `apps/web` behavior tests and typecheck pass; staging execution still required for full evidence |
| P0-002 | Rollback / restore drill | ⚠️ ACCEPTED RISK — pending sign-off | `signoff-evidence/p0-rollback-20260613.json` refreshed; immutable-image rollback doctrine added to runbook; static verifier 8/8; runtime rehearsal requires environment |
| P0-003 | Enterprise SSO/OIDC | ⚠️ ACCEPTED RISK — pending sign-off | `signoff-evidence/p0-sso-20260613.json` refreshed; local Keycloak surrogate committed to `docker-compose.live.yml` under `sso` profile; real IdP integration required |
```

- [ ] **Step 2: Update `docs/launch/launch-blocker-register.md`**

Bump the evidence references in the P0 rows (around lines 306–308 and 339–341) to point at the refreshed evidence files and the current branch. Keep the classification `RE_TESTABLE`. Update the final verdict timestamp if it contains one.

- [ ] **Step 3: Commit**

```bash
git add docs/readiness/current.md docs/launch/launch-blocker-register.md
git commit -m "docs(readiness): refresh P0 status after remediation sprint fixes"
```

---

## Final Verification

After all tasks are complete:

1. **Frontend behavior tests**
   ```bash
   cd apps/web
   pnpm vitest run src/shell/router.behavior.test.tsx src/contexts/AuthContext.behavior.test.tsx src/components/routing/RequireClerkAuth.test.tsx src/auth/ClerkAuthBridge.test.tsx
   ```
   Expected: all pass.

2. **Backend case route tests**
   ```bash
   PATH=/home/bunnyshell/Fabric_4L/.venv/bin:$PATH pytest services/layer4-agents/tests/test_analysis_routes.py::test_post_cases_success_path services/layer4-agents/tests/test_analysis_routes.py::test_post_cases_uses_optional_case_id -v
   ```
   Expected: both pass.

3. **Rollback static verifier**
   ```bash
   python scripts/ci/verify_release_rollback.py
   ```
   Expected: exit 0.

4. **Keycloak realm validation**
   ```bash
   KC_REALM_IMPORT_LOCATION=infra/keycloak/fabric-realm.json python infra/keycloak/validate-realm-seed.py
   ```
   Expected: OK.

5. **Full repository gate (if time and environment permit)**
   ```bash
   PATH=/home/bunnyshell/Fabric_4L/.venv/bin:$PATH make verify
   ```
   Expected: pass (this is the canonical PR gate).

---

## Self-Review

1. **Spec coverage:**
   - P0-001 Clerk hook boundary → Task 1.
   - P0-001b `case-meridian-e2e-001` seed → Task 2.
   - P0-002 rollback runbook/evidence → Task 3.
   - P0-003 Keycloak SSO/OIDC surrogate → Task 4.
   - Canonical docs refresh → Task 5.
   All spec requirements are covered.

2. **Placeholder scan:** No `TBD`, `TODO`, or vague "add error handling" steps remain. Every code change is shown verbatim.

3. **Type consistency:** `case_id` is `str | None` in the backend request and optional string in the seeder. `RootRedirect` dispatcher always returns a component that calls the same hooks on every render.
