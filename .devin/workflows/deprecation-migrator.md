---
workflow_id: deprecation-migrator
name: Deprecation Migrator
version: 1.0.0
description: Migrate deprecated anti-pattern instances to canonical replacements defined in contract.md. Use when fixing tenant-id-as-parameter, direct-header-access, explicit-db-connect, inline-middleware, inline-tool-definition, tools-throwing-exceptions, json-parse-llm, imperative-navigation, url-concatenation, or raw-sql-tenant patterns. Targets ~280 instances tracked in DEPRECATIONS.md.
pattern: circuit-breaker
risk_level: medium
---

# Deprecation Migrator

Fixes individual anti-pattern instances from `DEPRECATIONS.md` using the canonical replacements in `contract.md`. Each invocation targets one anti-pattern category or one specific file.

## When to Use

- You are asked to "fix deprecations", "migrate anti-patterns", or "improve contract compliance"
- A file is flagged by `scripts/ci/check_deprecations.py`
- The DEPRECATIONS.md dashboard shows a layer below 80% compliance

## Anti-Pattern Registry (10 categories, ~280 instances)

| ID | Pattern | Canonical Replacement | Locations | Count |
|----|---------|----------------------|-----------|-------|
| AP-1 | `tenant_id` as function parameter | `getTenantContext()` from async scope (§2.1) | L2 services (12), L3 routes (18), L4 tools (8), FE hooks (9) | ~47 |
| AP-2 | `req.headers['x-tenant-id']` outside middleware | Auth middleware extracts once; use `getTenantContext()` (§2.1) | L1 middleware (5), L3 main (11), L4 agents (7) | ~23 |
| AP-3 | Raw SQL with `tenant_id` filtering | ORM automatic scoping via `db.getSession()` (§2.2) | L3 retrieval (8), L5 eval (4), scripts (3 whitelisted) | ~15 |
| AP-4 | `db.connect(tenantId)` / `db.withTenant()` | `db.getSession()` reads tenant from async scope (§2.2) | L2 db (12), L3 db (14), L4 db (5) | ~31 |
| AP-5 | `app.use(middleware)` inline in route files | Route manifest with declared phase pipeline (§2.3) | L3 routes (28), L4 api (14) | ~42 |
| AP-6 | Tools defined as lambdas in agent config | Central ToolRegistry with schema-first definitions (§2.4) | L4 agents (15), L4 workflows (4) | ~19 |
| AP-7 | Tools using `throw`/`raise` instead of structured error | Return `ToolResult` with `status: "error"` (§2.4) | L4 tools (18), L4 agents (9) | ~27 |
| AP-8 | `JSON.parse()` on LLM/agent response | Pydantic structured generation + validation (§2.5) | L4 agents (10), L4 orchestrator (3) | ~13 |
| AP-9 | `router.push()` / imperative navigation | `navigate()` from wouter (§2.6) | FE pages (38), FE components (18) | ~56 |
| AP-10 | URL string concatenation | Template literals or `navigate()` with params (§2.6) | FE pages (22), FE components (12) | ~34 |

## Workflow Steps

### Step 1: Select Target

Determine which anti-pattern to fix. Accept one of:
- An anti-pattern ID (e.g., `AP-1`)
- A file path (scan for all anti-patterns in that file)
- A layer name (e.g., `layer4`) to fix all instances in that layer

### Step 2: Scan for Instances

For the selected anti-pattern, grep for the deprecated pattern:

```
AP-1: grep -rn "def.*tenant_id" services/layer{2,3,4}*/src/ --include="*.py"
AP-2: grep -rn "headers\[.*tenant" services/layer*/src/ --include="*.py"
AP-3: grep -rn "tenant_id" services/layer*/src/ --include="*.py" | grep -i "select\|where\|insert\|update"
AP-4: grep -rn "db\.connect\|db\.withTenant\|db\.with_tenant" services/ --include="*.py"
AP-5: grep -rn "app\.use\|app\.add_middleware" services/layer*/src/api/ --include="*.py"
AP-6: grep -rn "lambda.*tool\|tools.*=.*\[" services/layer4-agents/src/agents/ --include="*.py"
AP-7: grep -rn "raise ToolError\|raise ValueError\|raise Exception" services/layer4-agents/src/tools/ --include="*.py"
AP-8: grep -rn "json\.loads\|JSON\.parse" services/layer4-agents/src/ --include="*.py"
AP-9: grep -rn "router\.push\|history\.push\|navigate(" frontend/client/src/ --include="*.tsx" --include="*.ts"
AP-10: grep -rn '+ "/' frontend/client/src/ --include="*.tsx" --include="*.ts"
```

### Step 3: Apply Migration (One Instance at a Time)

For each instance, apply the canonical replacement:

**AP-1 (tenant-id-as-parameter):**
1. Remove `tenant_id` parameter from function signature
2. Add `from shared.identity.context import get_tenant_context` at file top
3. Inside function body, add: `tenant_id = get_tenant_context().tenant_id`
4. Update all call sites to remove the tenant_id argument
5. If function is in a test file, use fixture injection instead

**AP-4 (explicit-db-connect):**
1. Replace `db.connect(tenant_id)` with `db.getSession()`
2. Ensure the calling context has tenant set via middleware
3. Verify ORM model has `tenant_id` column for RLS

**AP-7 (tools-throwing-exceptions):**
1. Wrap tool `execute()` body in try/except
2. Convert `raise ToolError(msg)` to `return OutputModel(success=False, error=msg)`
3. Ensure the output Pydantic model has `success: bool` and `error: str | None`
4. Set `recoverable=True` for transient errors, `False` for validation errors

**AP-9 (imperative-navigation):**
1. Replace `router.push("/path")` with `navigate("/path")` using wouter's `useLocation`
2. For components already importing `useLocation`, just use the existing `navigate`
3. For new imports: `const [, navigate] = useLocation();`

**AP-10 (URL concatenation):**
1. Replace `"/tenant/" + tenantId + "/dashboard"` with template literal `` `/tenant/${tenantId}/dashboard` ``
2. Better: use a route helper that validates the path exists in the route manifest

### Step 4: Verify Fix

After each migration:
1. Run the relevant layer's tests:
   - Python: `python -m pytest services/layer{N}/tests/ -x -q`
   - Frontend: `cd frontend && pnpm test --run`
2. Run contract tests: `python -m pytest tests/contract/ -x -q`
3. Run deprecation checker: `python scripts/ci/check_deprecations.py --format markdown`
4. Confirm instance count decreased by the expected amount

### Step 5: Update DEPRECATIONS.md

After successful migration:
1. Decrement the instance count for the migrated anti-pattern
2. If all instances are migrated, move the entry to "Completed Migrations" table
3. Update the Dashboard compliance scores

## Edge Cases

- **Whitelisted instances:** `scripts/analytics/*.py` raw SQL is whitelisted (AP-3) — skip these
- **Test files:** Don't migrate patterns in test mocks/fixtures unless the test is testing the pattern itself
- **Shared identity:** Never modify `shared/identity/` without security review (AGENTS.md P0 rule #2)
- **Migrations:** Never modify `services/layer4-agents/migrations/` by hand (AGENTS.md P0 rule #3)

## Verification Command

```bash
python scripts/ci/check_deprecations.py --format markdown
```

## See Also

- **Skill:** `skills/deprecation-migrator/SKILL.md` — Programmatic agent skill for anti-pattern migration
- **Related Workflows:**
  - `/contract-enforcement-auditor` — Identify anti-pattern violations before migration
  - `/dead-code-sweeper` — Remove code after successful migration
