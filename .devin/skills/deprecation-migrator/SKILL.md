---
skill_id: deprecation-migrator
name: deprecation-migrator
version: 1.0.0
description: Migrate deprecated anti-pattern instances to canonical replacements defined in contract.md. Use when fixing tenant-id-as-parameter, direct-header-access, explicit-db-connect, inline-middleware, inline-tool-definition, tools-throwing-exceptions, json-parse-llm, imperative-navigation, url-concatenation, or raw-sql-tenant patterns. Targets ~280 instances tracked in DEPRECATIONS.md.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Deprecation Migrator

Fixes individual anti-pattern instances from `DEPRECATIONS.md` using the canonical replacements in `contract.md`.

## When to Use

- You are asked to "fix deprecations", "migrate anti-patterns", or "improve contract compliance"
- A file is flagged by `scripts/ci/check_deprecations.py`
- The DEPRECATIONS.md dashboard shows a layer below 80% compliance

## Anti-Pattern Registry

| ID | Pattern | Canonical | Locations | Count |
|----|---------|-----------|-----------|-------|
| AP-1 | `tenant_id` as function parameter | `getTenantContext()` (§2.1) | L2/L3/L4/FE | ~47 |
| AP-2 | `req.headers['x-tenant-id']` outside middleware | Auth middleware extracts once (§2.1) | L1/L3/L4 | ~23 |
| AP-3 | Raw SQL with `tenant_id` filtering | ORM automatic scoping via `db.getSession()` (§2.2) | L3/L5 | ~15 |
| AP-4 | `db.connect(tenantId)` / `db.withTenant()` | `db.getSession()` reads from async scope (§2.2) | L2/L3/L4 | ~31 |
| AP-5 | `app.use(middleware)` inline in route files | Route manifest with phase pipeline (§2.3) | L3/L4 | ~42 |
| AP-6 | Tools defined as lambdas in agent config | Central ToolRegistry with schema-first (§2.4) | L4 | ~19 |
| AP-7 | Tools using `throw`/`raise` | Return `ToolResult` with `status: "error"` (§2.4) | L4 | ~27 |
| AP-8 | `JSON.parse()` on LLM response | Pydantic structured generation (§2.5) | L4 | ~13 |
| AP-9 | `router.push()` / imperative navigation | `navigate()` from navigation service (§2.6) | FE | ~56 |
| AP-10 | URL string concatenation | Template literals or `navigate()` with params (§2.6) | FE | ~34 |

## Workflow Steps

### Step 1: Select Target

Accept one of:
- An anti-pattern ID (e.g., `AP-1`)
- A file path (scan for all anti-patterns in that file)
- A layer name (e.g., `layer4`) to fix all instances in that layer

### Step 2: Scan for Instances

For the selected anti-pattern, grep for the deprecated pattern:

**AP-1:** `grep -rn "def.*tenant_id" services/layer{2,3,4}*/src/ --include="*.py"`

**AP-2:** `grep -rn "headers\[.*tenant" services/layer*/src/ --include="*.py"`

**AP-4:** `grep -rn "db\.connect\|db\.withTenant\|db\.with_tenant" services/ --include="*.py"`

**AP-5:** `grep -rn "app\.use\|app\.add_middleware" services/layer*/src/api/ --include="*.py"`

**AP-6:** `grep -rn "lambda.*tool\|tools.*=.*\[" services/layer4-agents/src/agents/ --include="*.py"`

**AP-7:** `grep -rn "raise ToolError\|raise ValueError\|raise Exception" services/layer4-agents/src/tools/ --include="*.py"`

**AP-8:** `grep -rn "json\.loads\|JSON\.parse" services/layer4-agents/src/ --include="*.py"`

**AP-9:** `grep -rn "router\.push\|history\.push\|navigate(" frontend/client/src/ --include="*.tsx"`

**AP-10:** `grep -rn '+ "/' frontend/client/src/ --include="*.tsx"`

### Step 3: Apply Migration

**AP-1 (tenant-id-as-parameter):**
1. Remove `tenant_id` parameter from function signature
2. Add `from shared.identity.context import get_tenant_context`
3. Inside function: `tenant_id = get_tenant_context().tenant_id`
4. Update all call sites to remove the tenant_id argument

**AP-4 (explicit-db-connect):**
1. Replace `db.connect(tenant_id)` with `db.getSession()`
2. Ensure the calling context has tenant set via middleware

**AP-7 (tools-throwing-exceptions):**
1. Wrap tool `execute()` body in try/except
2. Convert `raise ToolError(msg)` to `return OutputModel(success=False, error=msg)`
3. Ensure output Pydantic model has `success: bool` and `error: str | None`

**AP-9 (imperative-navigation):**
1. Replace `router.push("/path")` with `navigate("/path")` using wouter's `useLocation`
2. Add import: `const [, navigate] = useLocation();`

### Step 4: Verify

After each migration:
1. Run layer tests: `python -m pytest services/layer{N}/tests/ -x -q`
2. Run contract tests: `python -m pytest tests/contract/ -x -q`
3. Run deprecation checker: `python scripts/ci/check_deprecations.py --format markdown`

### Step 5: Update DEPRECATIONS.md

Decrement instance count and move to "Completed Migrations" if all instances fixed.

## Edge Cases

- **Whitelisted instances:** `scripts/analytics/*.py` raw SQL is whitelisted (AP-3) — skip
- **Test files:** Don't migrate patterns in test mocks/fixtures unless testing the pattern itself
- **Shared identity:** Never modify `shared/identity/` without security review (AGENTS.md P0 #2)
- **Migrations:** Never modify `services/layer4-agents/migrations/` by hand (AGENTS.md P0 #3)

## Verification

```bash
python scripts/ci/check_deprecations.py --format markdown
```
