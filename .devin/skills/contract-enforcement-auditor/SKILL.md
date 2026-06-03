---
skill_id: contract-enforcement-auditor
name: contract-enforcement-auditor
version: 1.0.0
description: Scan for contract violations and enforcement gaps across all 6 canonical contracts in contract.md. Use when auditing compliance, checking if ESLint rules are actually running, verifying CI gates are blocking, or assessing the gap between documented contracts and runtime enforcement. Reports on the 58% enforcement rate identified in CONTRACT_ENFORCEMENT_ASSESSMENT.md.
side_effects: read
timeout_ms: 30000
required_context:
  - project_graph
  - test_inventory
allowed_agents:
  - "*"
---

# Contract Enforcement Auditor

Scans codebase for violations of the 6 canonical contracts in `contract.md` and identifies enforcement gaps.

## When to Use

- Before release to verify contract compliance
- After changes to `contract.md`, `DEPRECATIONS.md`, or ESLint rules
- When CI passes but you suspect enforcement gaps
- Periodic compliance review (weekly)

## Contract Registry

| § | Contract | ESLint Rules | CI Gate? | Runtime | Score |
|---|----------|-------------|----------|---------|-------|
| 2.1 | Tenant Context Propagation | `no-tenant-id-parameter`, `no-req-tenant-access` | No | Partial | ~60% |
| 2.2 | DB Session Isolation | `no-raw-tenant-query`, `no-explicit-db-connect` | No | None | ~40% |
| 2.3 | Middleware/Auth Flow | `no-inline-middleware` | No | Single middleware | ~50% |
| 2.4 | Tool Invocation Boundary | `no-inline-tool-definition`, `no-throw-in-tool` | No | None | ~55% |
| 2.5 | Agent Output Shape | `no-json-parse-agent-output` | No | OTel partial | ~50% |
| 2.6 | UI State Progression | `no-imperative-navigation`, `no-url-concatenation` | ESLint | wouter | ~65% |

## Workflow Steps

### Step 1: Choose Scope

- Contract number (e.g., `§2.1`)
- Layer name (e.g., `layer4`)
- `all` for full audit

### Step 2: Run Automated Checks

#### 2a. ESLint Plugin Status

```bash
ls frontend/node_modules/eslint-plugin-fabric-contracts/ 2>/dev/null || echo "NOT INSTALLED"
grep -A2 "fabric-contracts" frontend/.eslintrc.js
```

Verify these rules are `"error"`:
- `no-tenant-id-parameter`, `no-req-tenant-access`
- `no-raw-tenant-query`, `no-explicit-db-connect`
- `no-inline-middleware`
- `no-inline-tool-definition`, `no-throw-in-tool`
- `no-json-parse-agent-output`
- `no-imperative-navigation`, `no-url-concatenation`

#### 2b. CI Pipeline Enforcement

```bash
grep -n "continue-on-error" .github/workflows/*.yml
```

Check `.github/workflows/pr-checks.yml` lint step has NO `continue-on-error: true`.

#### 2c. Contract Test Coverage

```bash
python -m pytest tests/contract/ -v --tb=short --co -q 2>&1 | head -50
```

#### 2d. Runtime Guard Scan

**§2.1:** `grep -rn "getTenantContext\|get_tenant_context" services/layer*/src/ --include="*.py" | wc -l`

**§2.2:** `grep -rn "getSession\|get_session\|TenantAwarePool" services/layer*/src/ --include="*.py" | wc -l`

**§2.4:** `grep -rn "ToolResult\|ToolGateway" services/layer4-agents/src/ --include="*.py" | wc -l`

### Step 3: Scan for Violations

**§2.1:**
```bash
grep -rn "def.*tenant_id.*:" services/layer*/src/ --include="*.py"
grep -rn "headers\[.*tenant" services/layer*/src/ --include="*.py"
```

**§2.2:**
```bash
grep -rn "db\.connect\|db\.withTenant" services/layer*/src/ --include="*.py"
grep -rn "WHERE.*tenant_id" services/layer*/src/ --include="*.py"
```

**§2.3:**
```bash
grep -rn "app\.use\|app\.add_middleware\|@app\.middleware" services/layer*/src/api/ --include="*.py"
```

**§2.4:**
```bash
grep -rn "lambda.*tool\|tools.*=.*\[" services/layer4-agents/src/agents/ --include="*.py"
grep -rn "raise ToolError\|raise ValueError" services/layer4-agents/src/tools/ --include="*.py"
```

**§2.5:**
```bash
grep -rn "json\.loads\|json\.parse\|JSON\.parse" services/layer4-agents/src/ --include="*.py"
```

**§2.6:**
```bash
grep -rn "navigate\|useLocation\|router\.push" frontend/client/src/ --include="*.tsx"
grep -rn '+ "/' frontend/client/src/ --include="*.tsx"
```

### Step 4: Generate Report

```markdown
## Contract Enforcement Audit

| Contract | Documented | Lint | CI | Runtime | Violations |
|----------|-----------|------|----|---------|------------|

### §2.1 Tenant Context
**Violations:** {count}
{file:line list}

**Gaps:**
- [ ] ESLint rule `no-tenant-id-parameter` is {enabled|disabled}
- [ ] CI gate is {blocking|non-blocking}
- [ ] Runtime guard covers {X}% of routes

**Fixes:**
1. Enable ESLint rule in `.eslintrc.js`
2. Remove `continue-on-error` from `pr-checks.yml`
3. Migrate instances using `/deprecation-migrator AP-1`
```

### Step 5: Create Fix Actions

| Gap | Fix |
|-----|-----|
| ESLint rule disabled | Change `"off"` → `"error"` in `.eslintrc.js` |
| CI non-blocking | Remove `continue-on-error: true` |
| No runtime guard | Create middleware/decorator |
| Missing test | Create `tests/contract/test_{contract}.py` |
| Ref not imported | Wire `examples/canonical/` to production |

## Key Files

- `contract.md` — Canonical contracts
- `DEPRECATIONS.md` — Anti-pattern tracking
- `CONTRACT_ENFORCEMENT_ASSESSMENT.md` — Previous audit
- `eslint-plugin-fabric-contracts/src/rules/` — ESLint rules
- `frontend/.eslintrc.js` — ESLint config
- `.github/workflows/pr-checks.yml` — CI
- `tests/contract/` — Contract tests
- `examples/canonical/` — Reference implementations
