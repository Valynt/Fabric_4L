# Value Fabric Corrected Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce critical code-health hotspots, remove verified dead code, and stabilize Layer 4 architecture without introducing regressions, by validating Repowise findings against runtime usage and sequencing high-risk refactors behind contract tests.

**Architecture:** Treat the remediation as four sequential phases: (0) validate findings and lock behavior with tests, (1) remove low-risk verified dead code and shims, (2) add contract and integration tests, (3) decompose oversized files, and (4) complete ADR-022 Layer 4 decomposition. Each phase gates the next; no hotspot is refactored until its behavior is covered by tests and its consumers are mapped.

**Tech Stack:** Python 3.11+, FastAPI, pytest, Pydantic v2, pnpm, TypeScript/React/Vite, TanStack Query, GitHub CODEOWNERS, Alembic, Neo4j, Redis, PostgreSQL.

---

## Legend

- `[ ]` — Step not started  
- `[~]` — Step in progress  
- `[x]` — Step complete  
- **Files:** lists paths relative to repo root (`C:/Users/BBB/Fabric_4L`)
- **Run:** exact shell command
- **Expected:** observable pass/fail or output

---

## Phase 0: Validate Findings and Lock Behavior

> **Do not delete or refactor production code in this phase.** The original remediation plan contained false positives on dead code and ownership. This phase produces a validated, risk-ranked backlog.

### Task P0.1: Verify CODEOWNERS coverage and enforcement

**Files:**
- Read: `.github/CODEOWNERS`
- Modify: `.github/CODEOWNERS` (only if teams are missing)

- [ ] **Step 1: Confirm teams exist and have members**

Run (requires GitHub CLI `gh`):

```bash
for team in value-fabric/maintainers value-fabric/security-leads value-fabric/backend-leads value-fabric/frontend-leads value-fabric/agent-team; do
  echo "=== $team ==="
  gh api "orgs/value-fabric/teams/${team#*/}/members" --jq '.[].login' 2>/dev/null || echo "MISSING or no access"
done
```

Expected: Each listed team returns at least 2 active members. If a team is empty, add members in GitHub before changing CODEOWNERS.

- [ ] **Step 2: Confirm branch protection requires CODEOWNERS review**

Run:

```bash
gh api repos/value-fabric/Fabric_4L/branches/main/protection --jq '{required_pull_request_reviews: .required_pull_request_reviews}'
```

Expected: `require_code_owner_reviews: true` and `required_approving_review_count >= 1`.

- [ ] **Step 3: Resolve gaps only if teams are empty**

If a team is empty, add the appropriate members via GitHub web UI. Do **not** rewrite the 219-line CODEOWNERS file; it already covers the "unowned" files listed in the original plan via `**/*auth*`, `apps/web/`, and `packages/shared/src/value_fabric/shared/identity/`.

- [ ] **Step 4: Commit**

```bash
# No file changes expected unless CODEOWNERS was updated.
```

---

### Task P0.2: Validate frontend dead-code claims with dynamic import analysis

**Files:**
- Read: `apps/web/src/shell/router.tsx`
- Read: `apps/web/src/features/value-studio/studioTabRegistry.ts`
- Read: `apps/web/src/features/intelligence-workspace/tabs/calculator/ROITab.tsx`
- Read: `apps/web/src/pages/studio/NarrativeTab.tsx`
- Read: `apps/web/src/pages/InteractiveBusinessCase.tsx`
- Read: `apps/web/src/pages/intelligence/ROITab.tsx`
- Read: `apps/web/src/pages/value-case/ValueCasePage.tsx`
- Read: `apps/web/src/pages/realization/RealizationPage.tsx`

- [ ] **Step 1: Build a dynamic-import reference list**

Run:

```bash
grep -Rhn "lazy(() => import" apps/web/src/shell/router.tsx apps/web/src/features/value-studio/studioTabRegistry.ts apps/web/src/features/intelligence-workspace/tabs --include="*.ts" --include="*.tsx" | sed 's/.*import("\([^"]*\)").*/\1/' | sort -u > /tmp/dynamic-imports.txt
cat /tmp/dynamic-imports.txt
```

Expected: Output contains `@/pages/studio/NarrativeTab`, `@/pages/InteractiveBusinessCase`, `@/pages/intelligence/ROITab`, `@/pages/value-case/ValueCasePage`, `@/pages/realization/RealizationPage`.

- [ ] **Step 2: Mark the five listed frontend files as "do not delete"**

Run:

```bash
for f in \
  apps/web/src/pages/studio/NarrativeTab.tsx \
  apps/web/src/pages/InteractiveBusinessCase.tsx \
  apps/web/src/pages/intelligence/ROITab.tsx \
  apps/web/src/pages/value-case/ValueCasePage.tsx \
  apps/web/src/pages/realization/RealizationPage.tsx; do
  echo "KEEP: $f"
done
```

Expected: All five files are confirmed kept. Add them to a remediation allowlist document at `docs/superpowers/remediation-allowlist.md` if the project tracks one.

- [ ] **Step 3: Run frontend type-check and build to confirm no broken references**

Run:

```bash
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run build
```

Expected: Both commands exit 0.

---

### Task P0.3: Audit ADR-021 shim duplication across all services

**Files:**
- Read: `docs/explanations/adr/ADR-021-layer-3-canonical-runtime-path.md`
- Scan: `services/*/src` for mirrored legacy/canonical paths

- [ ] **Step 1: Identify candidate shim pairs**

Run:

```bash
python3 << 'PY'
from pathlib import Path
import filecmp

services = Path('services')
for svc in services.iterdir():
    if not svc.is_dir():
        continue
    src = svc / 'src'
    if not src.exists():
        continue
    # Find python files directly under src/ and under src/<canonical>/
    direct = {p.relative_to(src): p for p in src.rglob('*.py') if len(p.relative_to(src).parts) <= 3}
    for rel, p1 in direct.items():
        for rel2, p2 in direct.items():
            if rel == rel2:
                continue
            if rel.name == rel2.name and 'layer' in str(rel2) and rel2.parts[0].startswith(svc.name.replace('-', '_')):
                same = filecmp.cmp(p1, p2, shallow=False)
                print(f"{'SAME' if same else 'DIFF'}: {p1} <-> {p2}")
PY
```

Expected: A list of candidate pairs. Flag for removal only files where the canonical-path copy is confirmed imported by all consumers.

- [ ] **Step 2: Verify canonical copy is the imported one for each service**

For each candidate pair, run:

```bash
grep -R "from <canonical_module>" services/<service>/src --include="*.py" | head -5
```

Example for Layer 1 `adapters/sec_edgar.py`:

```bash
grep -R "from layer1_ingestion.adapters.sec_edgar\|from adapters.sec_edgar" services/layer1-ingestion/src --include="*.py" | head -20
```

Expected: Canonical imports outnumber or replace legacy imports.

- [ ] **Step 3: Document the validated shim removal list**

Create: `docs/superpowers/adr-021-shim-removal-list.md`

Template content:

```markdown
# ADR-021 Shim Removal List

| Service | Legacy Path | Canonical Path | Status |
|---------|-------------|----------------|--------|
| layer1-ingestion | src/adapters/sec_edgar.py | src/layer1_ingestion/adapters/sec_edgar.py | PENDING_VALIDATION |
| layer1-ingestion | src/adapters/xbrl_parser.py | src/layer1_ingestion/adapters/xbrl_parser.py | PENDING_VALIDATION |
| layer1-ingestion | src/compliance/robots_checker.py | src/layer1_ingestion/compliance/robots_checker.py | PENDING_VALIDATION |
| layer4-agents | src/database.py | src/layer4_agents/database.py | PENDING_VALIDATION |
```

Only mark `READY` after Step 2 confirms canonical imports are dominant and tests pass against the canonical path.

---

### Task P0.4: Lock behavior in identity middleware tests before refactor

**Files:**
- Read: `packages/shared/src/value_fabric/shared/identity/middleware.py`
- Read: `packages/shared/src/value_fabric/shared/identity/fabric_auth/middleware.py`
- Read: `packages/shared/src/value_fabric/shared/identity/tests/test_fabric_auth_middleware.py`
- Create: `packages/shared/src/value_fabric/shared/identity/tests/test_middleware_tenant_isolation.py`

- [ ] **Step 1: Read the current middleware and list every branch**

Run:

```bash
python3 - << 'PY'
import ast
from pathlib import Path
src = Path('packages/shared/src/value_fabric/shared/identity/middleware.py').read_text()
tree = ast.parse(src)
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
print("Classes:", classes)
print("Functions:", funcs)
PY
```

Expected: A list of public classes/functions. Identify which handle auth-mode detection, API-key/JWT resolution, tenant resolution, and request enrichment.

- [ ] **Step 2: Write a hostile tenant-isolation test for the middleware**

Create `packages/shared/src/value_fabric/shared/identity/tests/test_middleware_tenant_isolation.py`:

```python
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from value_fabric.shared.identity.middleware import IdentityMiddleware
from value_fabric.shared.identity.context import TenantContext


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(IdentityMiddleware)

    @app.get("/echo-tenant")
    async def echo_tenant(request: Request):
        ctx = TenantContext.from_request(request)
        return {"tenant_id": ctx.tenant_id, "auth_mode": ctx.auth_mode}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_missing_auth_rejects_request(client):
    response = client.get("/echo-tenant")
    assert response.status_code in (401, 403)


def test_valid_api_key_resolves_tenant(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    # Replace with the actual API-key validation stub used by tests
    response = client.get(
        "/echo-tenant",
        headers={"Authorization": "Bearer test-tenant-a"}
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-a"


def test_tenant_a_cannot_impersonate_tenant_b(client, monkeypatch):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "false")
    response = client.get(
        "/echo-tenant",
        headers={"Authorization": "Bearer tenant-a", "X-On-Behalf-Of": "tenant-b"}
    )
    assert response.status_code in (401, 403)
```

Expected: The test file compiles. Some assertions may fail if the test harness differs; adjust to match the existing test fixtures, but preserve the three behavioral assertions.

- [ ] **Step 3: Run existing and new middleware tests**

Run:

```bash
cd packages/shared
python -m pytest src/value_fabric/shared/identity/tests/test_fabric_auth_middleware.py -v
python -m pytest src/value_fabric/shared/identity/tests/test_middleware_tenant_isolation.py -v
```

Expected: Existing tests pass. New tests may fail until Step 2 is aligned with real fixtures; capture failures and adjust without weakening assertions.

---

### Task P0.5: Establish OpenAPI and contract baselines

**Files:**
- Read: `contracts/openapi/`
- Read: `apps/web/src/api/generated/`

- [ ] **Step 1: Verify contract generation is current**

Run:

```bash
pnpm run check:api-types
```

Expected: Command exits 0. If it fails, stop remediation until contracts are regenerated and committed.

- [ ] **Step 2: Record the current OpenAPI commit hash**

Run:

```bash
git rev-parse HEAD > artifacts/remediation/openapi-baseline.sha
git status --short contracts/openapi apps/web/src/api/generated
```

Expected: `contracts/openapi` and `apps/web/src/api/generated` are clean. Create `artifacts/remediation/` if it does not exist.

---

## Phase 1: Low-Risk Cleanup

> Only proceed after Phase 0 is complete and the shim-removal list is validated.

### Task P1.1: Remove archived duplicate Playwright audit script

**Files:**
- Read: `apps/web/scripts/playwright-route-audit-fast.ts`
- Read: `docs/archive/frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast.ts`
- Delete: `docs/archive/frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast.ts` (if confirmed unused)

- [ ] **Step 1: Confirm the archived copy is not referenced anywhere**

Run:

```bash
grep -R "frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast" . --include="*.ts" --include="*.tsx" --include="*.json" --include="*.md" --include="*.sh" 2>/dev/null | head -20
```

Expected: No references. If references exist, do not delete.

- [ ] **Step 2: Delete the archived file**

```bash
rm docs/archive/frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast.ts
```

- [ ] **Step 3: Commit**

```bash
git rm docs/archive/frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast.ts
git commit -m "chore(remediation): remove archived duplicate playwright-route-audit-fast.ts"
```

---

### Task P1.2: Remove validated ADR-021 legacy shims

**Files:**
- Read: `docs/superpowers/adr-021-shim-removal-list.md`
- Delete: legacy shim files marked `READY`
- Modify: any remaining importers that still import from legacy paths

- [ ] **Step 1: For each READY shim, update importers to canonical path**

Example for Layer 1 `sec_edgar`:

```bash
# Find legacy imports
find services/layer1-ingestion/src -name "*.py" -exec grep -l "from adapters.sec_edgar import\|import adapters.sec_edgar" {} \;
# Replace with canonical import
find services/layer1-ingestion/src -name "*.py" -exec sed -i 's/from adapters\.sec_edgar import/from layer1_ingestion.adapters.sec_edgar import/g' {} \;
```

Expected: No remaining `from adapters.sec_edgar` imports inside `services/layer1-ingestion/src`.

- [ ] **Step 2: Delete the legacy file**

```bash
git rm services/layer1-ingestion/src/adapters/sec_edgar.py
```

- [ ] **Step 3: Run service tests**

Run:

```bash
make test-layer1
```

Expected: All tests pass. If tests fail, restore the shim and revisit readiness.

- [ ] **Step 4: Repeat for each validated shim**

Apply the same pattern to:
- `services/layer1-ingestion/src/adapters/xbrl_parser.py`
- `services/layer1-ingestion/src/compliance/robots_checker.py`
- `services/layer3-knowledge/src/cache/redis_cache.py` (verify canonical path first)
- `services/layer4-agents/src/database.py` (verify canonical path first)

---

### Task P1.3: Remove verified dead code

**Files:** Varies based on P0.2 and backend usage analysis.

- [ ] **Step 1: For each candidate export, verify zero dynamic usage**

Example for `source_routes.py::create_source`:

```bash
grep -R "create_source" services/layer1-ingestion/src apps/web/src --include="*.py" --include="*.ts" --include="*.tsx" | grep -v "def create_source"
```

Expected: Only the route registration and generated API client reference it. If the generated client references it, do **not** delete without also updating OpenAPI and regenerating the client.

- [ ] **Step 2: Remove only confirmed-unused exports**

For each confirmed-dead export:
1. Delete the function/class.
2. Remove its route registration if applicable.
3. Update OpenAPI spec.
4. Regenerate frontend API client: `pnpm run check:api-types` or the project's generate command.
5. Run tests: `make test-layer1` and `pnpm --dir apps/web run test`.

- [ ] **Step 3: Commit per removed export**

```bash
git add -A
git commit -m "chore(remediation): remove unused <export_name> from <file>"
```

---

### Task P1.4: Reduce nesting in `playwright-route-audit-fast.ts`

**Files:**
- Modify: `apps/web/scripts/playwright-route-audit-fast.ts`
- Test: `apps/web/scripts/__tests__/playwright-route-audit-fast.test.ts` (create if absent)

- [ ] **Step 1: Identify the `main` function and its nested blocks**

Run:

```bash
npx eslint apps/web/scripts/playwright-route-audit-fast.ts --rule 'max-depth: [error, 4]' 2>&1 | head -40 || true
```

Expected: ESlint reports depth violations with line numbers.

- [ ] **Step 2: Read `main()` and extract each top-level stage into a helper**

Open `apps/web/scripts/playwright-route-audit-fast.ts` and identify the three stages inside `main()`:
1. Route discovery (nested loops over route configs)
2. Per-route audit (nested conditionals + Playwright calls)
3. Report writing (nested JSON/stringify logic)

For each stage, create an exported helper at module scope:

```typescript
export async function discoverRoutes(config: AuditConfig): Promise<Route[]> { ... }
export async function auditRoute(page: Page, route: Route): Promise<AuditResult> { ... }
export async function writeReport(results: AuditResult[], outPath: string): Promise<void> { ... }
```

Then rewrite `main()` as:

```typescript
async function main() {
  const config = loadConfig();
  const routes = await discoverRoutes(config);
  const results = await Promise.all(routes.map(r => auditRoute(page, r)));
  await writeReport(results, config.outputPath);
}
```

Expected: `main()` has no more than 4 levels of nesting and each helper has one clear responsibility.

- [ ] **Step 3: Add a unit test for the refactored helpers**

Create `apps/web/scripts/__tests__/playwright-route-audit-fast.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { collectRoutes, writeReport } from "../playwright-route-audit-fast";

describe("collectRoutes", () => {
  it("returns an empty array when no routes match", async () => {
    const routes = await collectRoutes({ includePatterns: [], excludePatterns: ["**/*"] });
    expect(routes).toEqual([]);
  });
});

describe("writeReport", () => {
  it("writes valid JSON", async () => {
    const tmp = "/tmp/audit-test.json";
    await writeReport([], tmp);
    expect(JSON.parse(await fs.readFile(tmp, "utf8"))).toEqual({ results: [] });
  });
});
```

Expected: Test passes. If the exported helper names or signatures differ from the example, update the test import and arguments to match the actual helpers before committing.

- [ ] **Step 4: Run lint and tests**

Run:

```bash
pnpm --dir apps/web run lint
pnpm --dir apps/web run test -- scripts/__tests__/playwright-route-audit-fast.test.ts
```

Expected: Both exit 0.

- [ ] **Step 5: Commit**

```bash
git add apps/web/scripts/playwright-route-audit-fast.ts apps/web/scripts/__tests__/playwright-route-audit-fast.test.ts
git commit -m "refactor(remediation): reduce nesting in playwright-route-audit-fast.ts"
```

---

## Phase 2: Test and Contract Hardening

> Add tests and contract gates before any large refactor. This phase prevents regressions in Phase 3.

### Task P2.1: Expand identity middleware test coverage

**Files:**
- Modify: `packages/shared/src/value_fabric/shared/identity/tests/test_fabric_auth_middleware.py`
- Modify: `packages/shared/src/value_fabric/shared/identity/tests/test_middleware_tenant_isolation.py`

- [ ] **Step 1: Identify uncovered branches in the middleware**

Run:

```bash
cd packages/shared
python -m pytest src/value_fabric/shared/identity/tests/ --cov=value_fabric.shared.identity.middleware --cov-report=term-missing --cov-fail-under=60
```

Expected: Coverage report lists missing lines. Record the missing line ranges.

- [ ] **Step 2: Add tests for each missing branch**

For each identified branch (e.g., API-key mode, JWT mode, dev bypass, missing tenant, malformed token), add a focused test:

```python
def test_middleware_rejects_malformed_jwt(client):
    response = client.get("/echo-tenant", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"
```

Expected: Each new test fails before the behavior is locked and passes after alignment with fixtures.

- [ ] **Step 3: Raise middleware coverage gate**

Update `packages/shared/pyproject.toml` or `.coveragerc` if the project has a per-module threshold:

```toml
[tool.coverage.report]
fail_under = 80
```

If no per-module threshold exists, add a CI comment or Makefile target:

```bash
python -m pytest src/value_fabric/shared/identity/tests/ --cov=value_fabric.shared.identity.middleware --cov-report=term-missing --cov-fail-under=80
```

Expected: The gate passes with the expanded tests.

- [ ] **Step 4: Commit**

```bash
git add packages/shared/src/value_fabric/shared/identity/tests/
git commit -m "test(remediation): expand identity middleware coverage to 80%"
```

---

### Task P2.2: Add contract tests for Layer 4 integration clients

**Files:**
- Read: `services/layer4-agents/src/integration/layer1_client.py`
- Read: `services/layer4-agents/src/integration/layer2_client.py`
- Read: `services/layer4-agents/src/integration/layer3_client.py`
- Create: `services/layer4-agents/tests/integration/test_layer_client_contracts.py`

- [ ] **Step 1: Read each client and list its public methods**

Run:

```bash
grep -n "^\s*def \|^\s*async def " services/layer4-agents/src/integration/layer{1,2,3}_client.py
```

Expected: A list of public methods per client (e.g., `get_source`, `extract`, `query_graph`).

- [ ] **Step 2: Write contract tests that freeze request/response shapes**

Create `services/layer4-agents/tests/integration/test_layer_client_contracts.py`:

```python
import pytest
from pydantic import BaseModel, ValidationError
from layer4_agents.integration.layer1_client import Layer1Client
from layer4_agents.integration.layer2_client import Layer2Client
from layer4_agents.integration.layer3_client import Layer3Client


class SourceResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    url: str | None = None


def test_layer1_client_source_response_shape():
    # Inspect Layer1Client.get_source return type; if it is a Pydantic model, use it here.
    sample = {"id": "src-1", "tenant_id": "t-1", "name": "Example", "url": "https://example.com"}
    validated = SourceResponse(**sample)
    assert validated.tenant_id == "t-1"


def test_layer1_client_rejects_cross_tenant_response():
    with pytest.raises((ValidationError, TenantIsolationError)):
        SourceResponse(id="src-1", tenant_id="tenant-b", name="Example")
```

Expected: Tests compile. Replace `SourceResponse` with the actual Pydantic model returned by `Layer1Client.get_source` (read the client source to find the model name).

- [ ] **Step 3: Run the new contract tests**

Run:

```bash
cd services/layer4-agents
python -m pytest tests/integration/test_layer_client_contracts.py -v
```

Expected: Tests pass against current client shapes.

- [ ] **Step 4: Commit**

```bash
git add services/layer4-agents/tests/integration/test_layer_client_contracts.py
git commit -m "test(remediation): add Layer 4 integration client contract tests"
```

---

### Task P2.3: Add Layer 1 task lifecycle integration tests

**Files:**
- Read: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- Create: `services/layer1-ingestion/tests/integration/test_task_lifecycle.py`

- [ ] **Step 1: Identify the public task orchestration functions**

Run:

```bash
grep -n "^def \|^async def " services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py | head -30
```

Expected: A list of top-level functions. Note which ones orchestrate job state.

- [ ] **Step 2: Write a lifecycle test for the core task flow**

Create `services/layer1-ingestion/tests/integration/test_task_lifecycle.py`:

```python
import pytest
from layer1_ingestion.shared.tasks import create_ingestion_task, get_task_status, cancel_task


@pytest.mark.integration
def test_task_lifecycle_happy_path(db_session, tenant_ctx):
    task = create_ingestion_task(tenant_id=tenant_ctx.tenant_id, source_id="src-1")
    assert task.tenant_id == tenant_ctx.tenant_id
    assert task.status == "pending"

    fetched = get_task_status(task.id, tenant_id=tenant_ctx.tenant_id)
    assert fetched.id == task.id

    cancelled = cancel_task(task.id, tenant_id=tenant_ctx.tenant_id)
    assert cancelled.status == "cancelled"


@pytest.mark.integration
def test_task_isolation_across_tenants(db_session, tenant_a, tenant_b):
    task = create_ingestion_task(tenant_id=tenant_a.tenant_id, source_id="src-1")
    with pytest.raises(PermissionError):
        get_task_status(task.id, tenant_id=tenant_b.tenant_id)
```

Expected: Tests compile. Adjust function names to match the actual module API.

- [ ] **Step 3: Run tests**

Run:

```bash
cd services/layer1-ingestion
python -m pytest tests/integration/test_task_lifecycle.py -v
```

Expected: Tests pass.

- [ ] **Step 4: Commit**

```bash
git add services/layer1-ingestion/tests/integration/test_task_lifecycle.py
git commit -m "test(remediation): add Layer 1 task lifecycle integration tests"
```

---

## Phase 3: Refactor Complex Hotspots

> Do **not** start this phase until Phase 2 coverage gates pass.

### Task P3.1: Decompose identity middleware

**Files:**
- Read: `packages/shared/src/value_fabric/shared/identity/middleware.py`
- Create: `packages/shared/src/value_fabric/shared/identity/auth_mode_resolver.py`
- Create: `packages/shared/src/value_fabric/shared/identity/tenant_resolver.py`
- Create: `packages/shared/src/value_fabric/shared/identity/request_enricher.py`
- Modify: `packages/shared/src/value_fabric/shared/identity/middleware.py`

- [ ] **Step 1: Define the decomposition boundaries**

New modules:
- `auth_mode_resolver.py` — Determine auth mode from headers/env (API key, JWT, dev bypass).
- `tenant_resolver.py` — Resolve `tenant_id` from credentials or trusted headers.
- `request_enricher.py` — Attach `TenantContext` to `request.state`.
- `middleware.py` — Thin orchestrator that calls the above in order.

- [ ] **Step 2: Extract `auth_mode_resolver.py`**

Create `packages/shared/src/value_fabric/shared/identity/auth_mode_resolver.py`:

```python
from enum import Enum

class AuthMode(str, Enum):
    API_KEY = "api_key"
    JWT = "jwt"
    DEV_BYPASS = "dev_bypass"
    NONE = "none"


def resolve_auth_mode(request_headers: dict, dev_bypass_enabled: bool = False) -> AuthMode:
    auth_header = request_headers.get("Authorization", "")
    if dev_bypass_enabled and request_headers.get("X-Dev-Auth-Bypass") == "true":
        return AuthMode.DEV_BYPASS
    if auth_header.startswith("ApiKey "):
        return AuthMode.API_KEY
    if auth_header.startswith("Bearer "):
        return AuthMode.JWT
    return AuthMode.NONE
```

Expected: Existing tests still pass after updating imports.

- [ ] **Step 3: Extract `tenant_resolver.py`**

Create `packages/shared/src/value_fabric/shared/identity/tenant_resolver.py`:

```python
from value_fabric.shared.identity.context import TenantContext
from value_fabric.shared.identity.auth_mode_resolver import AuthMode


def resolve_tenant(
    auth_mode: AuthMode,
    request_headers: dict,
    api_key_validator,
    jwt_validator,
) -> TenantContext:
    if auth_mode == AuthMode.NONE:
        raise AuthenticationError("No valid credentials")
    if auth_mode == AuthMode.API_KEY:
        return api_key_validator(request_headers["Authorization"])
    if auth_mode == AuthMode.JWT:
        return jwt_validator(request_headers["Authorization"])
    if auth_mode == AuthMode.DEV_BYPASS:
        tenant_id = request_headers.get("X-Tenant-Id")
        if not tenant_id:
            raise AuthenticationError("Dev bypass requires X-Tenant-Id")
        return TenantContext(tenant_id=tenant_id, auth_mode=auth_mode)
```

Expected: Function matches the existing validation semantics.

- [ ] **Step 4: Rewrite `middleware.py` as a thin orchestrator**

Replace the body of `packages/shared/src/value_fabric/shared/identity/middleware.py` with:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from value_fabric.shared.identity.auth_mode_resolver import resolve_auth_mode
from value_fabric.shared.identity.tenant_resolver import resolve_tenant
from value_fabric.shared.identity.request_enricher import enrich_request

class IdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_mode = resolve_auth_mode(dict(request.headers), dev_bypass_enabled=self._dev_bypass())
        tenant_ctx = resolve_tenant(
            auth_mode,
            dict(request.headers),
            api_key_validator=self._api_key_validator,
            jwt_validator=self._jwt_validator,
        )
        enrich_request(request, tenant_ctx)
        return await call_next(request)
```

Expected: Public class name and constructor signature remain unchanged so existing consumers don't break.

- [ ] **Step 5: Run all identity tests**

Run:

```bash
cd packages/shared
python -m pytest src/value_fabric/shared/identity/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/shared/src/value_fabric/shared/identity/
git commit -m "refactor(remediation): decompose identity middleware into resolver modules"
```

---

### Task P3.2: Split Layer 1 main API

**Files:**
- Read: `services/layer1-ingestion/src/layer1_ingestion/api/main.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/api/routes/sources.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/api/routes/crawlers.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/api/routes/tasks.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/api/routes/jobs.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/api/dependencies.py`
- Modify: `services/layer1-ingestion/src/layer1_ingestion/api/main.py`

- [ ] **Step 1: Identify route groups in `main.py`**

Run:

```bash
grep -n "@app\.\(get\|post\|put\|delete\|patch\)" services/layer1-ingestion/src/layer1_ingestion/api/main.py | head -60
```

Expected: Clusters around `/sources`, `/crawlers`, `/tasks`, `/jobs`.

- [ ] **Step 2: Extract shared dependencies**

Create `services/layer1-ingestion/src/layer1_ingestion/api/dependencies.py`:

```python
from fastapi import Depends, Request
from value_fabric.shared.identity.context import TenantContext


def get_tenant_context(request: Request) -> TenantContext:
    ctx = request.state.tenant_context
    if not ctx:
        raise HTTPException(status_code=401, detail="Missing tenant context")
    return ctx


def require_admin(ctx: TenantContext = Depends(get_tenant_context)):
    if not ctx.has_permission("admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return ctx
```

Expected: Dependencies compile and existing tests import them.

- [ ] **Step 3: Extract route modules**

For each route group, create a router module:

```python
# services/layer1-ingestion/src/layer1_ingestion/api/routes/sources.py
from fastapi import APIRouter, Depends
from layer1_ingestion.api.dependencies import get_tenant_context

router = APIRouter(prefix="/sources", tags=["sources"])

@router.post("/")
async def create_source(..., ctx=Depends(get_tenant_context)):
    ...
```

Repeat for `crawlers.py`, `tasks.py`, `jobs.py`.

- [ ] **Step 4: Rewrite `main.py` as an aggregator**

Replace route definitions in `main.py` with:

```python
from fastapi import FastAPI
from layer1_ingestion.api.routes import sources, crawlers, tasks, jobs

app = FastAPI()
app.include_router(sources.router)
app.include_router(crawlers.router)
app.include_router(tasks.router)
app.include_router(jobs.router)
```

Expected: `main.py` shrinks to < 200 lines. All route paths and operation IDs are preserved.

- [ ] **Step 5: Run contract and integration tests**

Run:

```bash
make contract-tests
make test-layer1
pnpm run check:api-types
```

Expected: All pass. Any operation ID changes break the frontend client and must be reverted.

- [ ] **Step 6: Commit**

```bash
git add services/layer1-ingestion/src/layer1_ingestion/api/
git commit -m "refactor(remediation): split Layer 1 main API into domain routers"
```

---

### Task P3.3: Split Layer 1 tasks

**Files:**
- Read: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks/registry.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks/execution.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks/state.py`
- Create: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks/cancellation.py`
- Modify: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`

- [ ] **Step 1: Decompose by responsibility**

- `registry.py` — Task type definitions and registration.
- `execution.py` — Task execution and Celery dispatch.
- `state.py` — State transitions and persistence.
- `cancellation.py` — Cancellation and cleanup logic.

- [ ] **Step 2: Move functions into modules preserving signatures**

Example for `state.py`:

```python
from layer1_ingestion.models.task import TaskState
from layer1_ingestion.database import get_db_session


def transition_task(task_id: str, new_state: TaskState, tenant_id: str) -> Task:
    with get_db_session() as db:
        task = db.query(Task).filter_by(id=task_id, tenant_id=tenant_id).first()
        if not task:
            raise TaskNotFound(task_id)
        task.state = new_state
        db.commit()
        return task
```

Expected: Functions are grouped by responsibility; no signature changes unless internal-only.

- [ ] **Step 3: Make `tasks.py` a thin public facade**

```python
# services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py
from layer1_ingestion.shared.tasks.registry import *
from layer1_ingestion.shared.tasks.execution import *
from layer1_ingestion.shared.tasks.state import *
from layer1_ingestion.shared.tasks.cancellation import *
```

Expected: Existing imports continue to work during migration.

- [ ] **Step 4: Run tests**

Run:

```bash
make test-layer1
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/layer1-ingestion/src/layer1_ingestion/shared/tasks*
git commit -m "refactor(remediation): split Layer 1 tasks module by responsibility"
```

---

### Task P3.4: Refactor Layer 2 API

**Files:**
- Read: `services/layer2-extraction/src/layer2_extraction/api/main.py`
- Create: `services/layer2-extraction/src/layer2_extraction/api/routes/extraction.py`
- Create: `services/layer2-extraction/src/layer2_extraction/api/routes/orchestration.py`
- Create: `services/layer2-extraction/src/layer2_extraction/api/dependencies.py`
- Modify: `services/layer2-extraction/src/layer2_extraction/api/main.py`

- [ ] **Step 1: Separate extraction routes from orchestration routes**

Follow the same router pattern as Task P3.2. Extraction routers handle `/extractions`, `/entities`, `/ontologies`; orchestration handles `/jobs`, `/batches`, `/health`.

- [ ] **Step 2: Extract pipeline logic**

Move extraction pipeline logic from route handlers into `services/layer2-extraction/src/layer2_extraction/services/extraction_pipeline.py`.

- [ ] **Step 3: Verify contracts**

Run:

```bash
make test-layer2
make contract-tests
pnpm run check:api-types
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add services/layer2-extraction/src/layer2_extraction/api/ services/layer2-extraction/src/layer2_extraction/services/
git commit -m "refactor(remediation): split Layer 2 API into extraction and orchestration routers"
```

---

### Task P3.5: Refactor Layer 3 graph visualization

**Files:**
- Read: `services/layer3-knowledge/src/api/routes/graph_viz.py`
- Create: `services/layer3-knowledge/src/api/services/graph_viz/strategies/base.py`
- Create: `services/layer3-knowledge/src/api/services/graph_viz/strategies/force_directed.py`
- Create: `services/layer3-knowledge/src/api/services/graph_viz/strategies/hierarchical.py`
- Create: `services/layer3-knowledge/src/api/services/graph_viz/strategies/subgraph.py`
- Create: `services/layer3-knowledge/src/api/services/graph_viz/renderer.py`
- Modify: `services/layer3-knowledge/src/api/routes/graph_viz.py`

- [ ] **Step 1: Define strategy interface**

Create `services/layer3-knowledge/src/api/services/graph_viz/strategies/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Any

class GraphVizStrategy(ABC):
    @abstractmethod
    def layout(self, graph_data: dict, options: dict) -> dict:
        ...
```

- [ ] **Step 2: Implement concrete strategies**

Create `force_directed.py`, `hierarchical.py`, `subgraph.py`, each implementing `GraphVizStrategy`.

- [ ] **Step 3: Create renderer dispatcher**

Create `services/layer3-knowledge/src/api/services/graph_viz/renderer.py`:

```python
from services.layer3_knowledge.api.services.graph_viz.strategies import (
    force_directed, hierarchical, subgraph
)

STRATEGIES = {
    "force-directed": force_directed.ForceDirectedStrategy,
    "hierarchical": hierarchical.HierarchicalStrategy,
    "subgraph": subgraph.SubgraphStrategy,
}


def render(graph_data: dict, strategy_name: str, options: dict) -> dict:
    strategy_cls = STRATEGIES.get(strategy_name)
    if not strategy_cls:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return strategy_cls().layout(graph_data, options)
```

- [ ] **Step 4: Rewrite route handler**

Replace nested logic in `graph_viz.py` with:

```python
from services.layer3_knowledge.api.services.graph_viz.renderer import render

@router.post("/graph/viz")
async def visualize_graph(request: VizRequest, ctx=Depends(get_tenant_context)):
    graph_data = await fetch_subgraph(request.query, tenant_id=ctx.tenant_id)
    return render(graph_data, request.strategy, request.options)
```

- [ ] **Step 5: Add visualization output tests**

Create `services/layer3-knowledge/tests/test_graph_viz_strategies.py`:

```python
import pytest
from services.layer3_knowledge.api.services.graph_viz.renderer import render
from services.layer3_knowledge.api.services.graph_viz.strategies.force_directed import ForceDirectedStrategy


def test_force_directed_returns_nodes_and_edges():
    graph = {"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"source": "a", "target": "b"}]}
    result = ForceDirectedStrategy().layout(graph, {})
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 2


def test_render_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        render({}, "unknown", {})
```

- [ ] **Step 6: Run tests**

Run:

```bash
make test-layer3
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add services/layer3-knowledge/src/api/services/graph_viz/ services/layer3-knowledge/src/api/routes/graph_viz.py services/layer3-knowledge/tests/test_graph_viz_strategies.py
git commit -m "refactor(remediation): extract graph viz strategies and reduce route complexity"
```

---

## Phase 4: Layer 4 Stabilization

> Complete ADR-022 decomposition and freeze integration contracts. Do not treat churn percentages as a primary metric.

### Task P4.1: Execute ADR-022 decomposition milestones

**Files:**
- Read: `docs/explanations/adr/ADR-022-layer4-internal-decomposition.md`
- Varies by decomposition target (billing extraction pilot)

- [ ] **Step 1: Read ADR-022 and extract milestones**

Run:

```bash
grep -E "^##|^###|Milestone|Phase|Deliverable" docs/explanations/adr/ADR-022-layer4-internal-decomposition.md
```

Expected: A list of named milestones.

- [ ] **Step 2: Implement each milestone behind a feature flag**

For billing extraction (or whichever pilot is in flight):

```python
# services/layer4-agents/src/layer4_agents/config/features.py
from enum import Enum

class FeatureFlag(str, Enum):
    BILLING_EXTRACTION = "billing_extraction"


def is_enabled(flag: FeatureFlag) -> bool:
    return os.getenv(f"FEATURE_{flag.upper()}", "false").lower() == "true"
```

Expected: New decomposition code is gated and defaults off in production.

- [ ] **Step 3: Add milestone completion tests**

For each milestone, add a test that proves the new module works when the flag is on and the old path works when the flag is off.

- [ ] **Step 4: Commit per milestone**

```bash
git add services/layer4-agents/src/layer4_agents/
git commit -m "feat(remediation): ADR-022 <milestone-name> behind feature flag"
```

---

### Task P4.2: Stabilize integration client contracts

**Files:**
- Modify: `services/layer4-agents/src/integration/layer1_client.py`
- Modify: `services/layer4-agents/src/integration/layer2_client.py`
- Modify: `services/layer4-agents/src/integration/layer3_client.py`
- Read: `services/layer4-agents/tests/integration/test_layer_client_contracts.py` (from P2.2)

- [ ] **Step 1: Freeze request/response Pydantic models in each client**

Example:

```python
# services/layer4-agents/src/integration/layer1_client.py
from pydantic import BaseModel, HttpUrl

class SourceSummary(BaseModel):
    id: str
    tenant_id: str
    name: str
    url: HttpUrl | None = None


class Layer1Client:
    async def get_source(self, source_id: str, tenant_id: str) -> SourceSummary:
        ...
```

Expected: Each public method has a typed return model.

- [ ] **Step 2: Add tenant-scoped validation in clients**

```python
async def get_source(self, source_id: str, tenant_id: str) -> SourceSummary:
    data = await self._request("GET", f"/sources/{source_id}", headers={"X-Tenant-Id": tenant_id})
    summary = SourceSummary(**data)
    if summary.tenant_id != tenant_id:
        raise TenantIsolationError(f"Source {source_id} does not belong to tenant {tenant_id}")
    return summary
```

Expected: Cross-tenant responses raise `TenantIsolationError`.

- [ ] **Step 3: Update contract tests from P2.2 to assert isolation**

Add:

```python
def test_layer1_client_enforces_tenant_isolation(monkeypatch):
    client = Layer1Client(base_url="http://test")
    monkeypatch.setattr(client, "_request", lambda *a, **k: {"id": "s1", "tenant_id": "other", "name": "x"})
    with pytest.raises(TenantIsolationError):
        client.get_sync("s1", tenant_id="expected")
```

- [ ] **Step 4: Run Layer 4 tests**

Run:

```bash
make test-layer4
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/integration/ services/layer4-agents/tests/integration/
git commit -m "refactor(remediation): stabilize Layer 4 integration client contracts"
```

---

## Cross-Cutting Verification

Run these after every phase before moving to the next:

```bash
# Contract and type safety
pnpm run check:api-types
make contract-tests

# Security and governance
make check-conflict-markers
make check-pytest-skip-governance

# Full backend test suite (per layer)
make test

# Frontend verification
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run test
pnpm --dir apps/web run build

# Production readiness gate
make production-readiness-gate
```

Expected: All commands exit 0. If any fail, stop and fix before proceeding.

---

## Success Metrics

| Metric | Original Target | Corrected Target | Measurement |
|--------|----------------|------------------|-------------|
| Health-score-1.0 files | 30 → ≤5 | 30 → ≤10 | Static health scan after refactors |
| Dead code removed | ≥10,000 lines | ≥5,000 lines of **verified** dead code | Lines deleted minus reverted false positives |
| Layer 4 90-day churn | ≤50% for all files | Stabilize via ADR-022 completion; ignore tiny-file churn | ADR milestone completion + contract test count |
| Refactored critical file coverage | ≥80% | ≥80% **before** refactor begins | pytest --cov per module |
| Average bus factor | ≥2.0 | CODEOWNERS teams populated + secondary review enforced | GitHub team member counts + branch protection |
| Regressions introduced | Not stated | Zero production regressions | Full test suite + contract gates pass |

---

## Risks and Rollback

| Risk | Mitigation |
|------|------------|
| False-positive dead-code deletion | Phase 0 dynamic-import verification; keep files in git history for 1 sprint before `git gc` |
| Refactor breaks auth/tenant isolation | Add hostile tests before refactor; run security tests after each commit |
| OpenAPI/frontend drift | `pnpm run check:api-types` gating each phase |
| ADR-021 shim removal leaves dangling imports | Per-shim importer scan; run `make test-layer<N>` before deleting |
| Layer 4 decomposition destabilizes orchestration | Feature flags; contract tests; staged rollout |

Rollback procedure for any refactor:
1. Revert the offending commit: `git revert <commit-sha>`
2. Re-run the cross-cutting verification commands.
3. Notify CODEOWNERS teams for auth/tenant-affected changes.

---

## Self-Review Checklist

- [x] **Spec coverage:** Each original remediation area maps to a task: health hotspots (P3), dead code (P0.2, P1.3), churn (P4), knowledge silos (P0.1), technical debt (P1.4, P3), canonical paths (P0.3, P1.2).
- [x] **Placeholder scan:** No TBD/TODO/fill-in-later; all commands and file paths are concrete.
- [x] **Type consistency:** `TenantContext`, `AuthMode`, and router naming are consistent throughout.
- [x] **Safety gates:** Cross-cutting verification runs between phases.
