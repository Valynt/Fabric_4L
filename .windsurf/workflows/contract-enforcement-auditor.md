---
workflow_id: contract-enforcement-auditor
name: Contract Enforcement Auditor
version: 1.0.0
description: Scan for contract violations and enforcement gaps across all 6 canonical contracts in contract.md. Use when auditing compliance, checking if ESLint rules are actually running, verifying CI gates are blocking, or assessing the gap between documented contracts and runtime enforcement. Reports on the 58% enforcement rate identified in CONTRACT_ENFORCEMENT_ASSESSMENT.md.
pattern: human-in-the-loop
risk_level: high
---

# Contract Enforcement Auditor

Scans the codebase for violations of the 6 canonical contracts defined in `contract.md` and identifies enforcement gaps (documented vs actual). Produces actionable fix lists with file:line references.

## When to Use

- Before a release to verify contract compliance
- After changes to `contract.md`, `DEPRECATIONS.md`, or ESLint plugin rules
- When CI passes but you suspect enforcement gaps
- When asked to "check contract compliance" or "audit enforcement"
- Periodic compliance review (weekly recommended)

## Contract Registry

| § | Contract | ESLint Rules | CI Gate? | Runtime Guard? | Current Score |
|---|----------|-------------|----------|----------------|---------------|
| 2.1 | Tenant Context Propagation | `no-tenant-id-parameter`, `no-req-tenant-access` | No | `GovernanceMiddleware` (partial) | ~60% |
| 2.2 | DB Session Isolation | `no-raw-tenant-query`, `no-explicit-db-connect` | No | None | ~40% |
| 2.3 | Middleware/Auth Flow | `no-inline-middleware` | No | Single middleware (not 8-phase) | ~50% |
| 2.4 | Tool Invocation Boundary | `no-inline-tool-definition`, `no-throw-in-tool` | No | None (Python) | ~55% |
| 2.5 | Agent Output Shape | `no-json-parse-agent-output` | No | OTel partial | ~50% |
| 2.6 | UI State Progression | `no-imperative-navigation`, `no-url-concatenation` | ESLint exists | wouter (not state-machine) | ~65% |

## Workflow Steps

### Step 1: Choose Scope

Accept one of:
- A contract number (e.g., `§2.1`) — audit one contract
- A layer name (e.g., `layer4`) — audit all contracts for that layer
- `all` — full audit across all contracts and layers

### Step 2: Run Automated Checks

#### 2a. ESLint Plugin Status

Check if the ESLint plugin is actually installed and its rules are enabled:

```bash
# Check plugin installation
ls frontend/node_modules/eslint-plugin-fabric-contracts/ 2>/dev/null || echo "NOT INSTALLED"

# Check which rules are enabled vs disabled
grep -A2 "fabric-contracts" frontend/.eslintrc.js
grep -A2 "fabric-contracts" frontend/.eslintrc.cjs
```

Read `frontend/.eslintrc.js` (or `.cjs`) and verify each of these rules is set to `"error"`:
- `fabric-contracts/no-tenant-id-parameter`
- `fabric-contracts/no-req-tenant-access`
- `fabric-contracts/no-raw-tenant-query`
- `fabric-contracts/no-explicit-db-connect`
- `fabric-contracts/no-inline-middleware`
- `fabric-contracts/no-inline-tool-definition`
- `fabric-contracts/no-throw-in-tool`
- `fabric-contracts/no-json-parse-agent-output`
- `fabric-contracts/no-imperative-navigation`
- `fabric-contracts/no-url-concatenation`

If any rule is `"off"` or `"warn"`, flag it as an enforcement gap.

#### 2b. CI Pipeline Enforcement

Check if CI gates are blocking (not `continue-on-error`):

```bash
grep -n "continue-on-error" .github/workflows/*.yml
```

Read the following CI workflow files and verify:
- `.github/workflows/pr-checks.yml` — lint step must NOT have `continue-on-error: true`
- `.github/workflows/contract-enforcement.yml` (if exists) — must be a required check
- `.github/workflows/ai-evals-pipeline.yml` — verify eval failures block merge

#### 2c. Contract Test Coverage

```bash
python -m pytest tests/contract/ -v --tb=short --co -q 2>&1 | head -50
```

Cross-reference: each contract (§2.1-§2.6) should have at least one test file in `tests/contract/`.

#### 2d. Runtime Guard Scan

For each contract, check if runtime enforcement exists:

**§2.1 Tenant Context:**
```bash
grep -rn "getTenantContext\|get_tenant_context\|RequestContext" services/layer*/src/ --include="*.py" | wc -l
```

**§2.2 DB Session:**
```bash
grep -rn "getSession\|get_session\|TenantAwarePool" services/layer*/src/ --include="*.py" | wc -l
```

**§2.4 Tool Invocation:**
```bash
grep -rn "ToolResult\|tool_result\|ToolGateway" services/layer4-agents/src/ --include="*.py" | wc -l
```

### Step 3: Scan for Violations

For each contract in scope, grep for violations:

**§2.1 — Tenant passed as parameter:**
```bash
grep -rn "def.*tenant_id.*:" services/layer*/src/ --include="*.py"
grep -rn "headers\[.*tenant" services/layer*/src/ --include="*.py"
```

**§2.2 — Direct DB connect with tenant:**
```bash
grep -rn "db\.connect\|db\.withTenant" services/layer*/src/ --include="*.py"
grep -rn "WHERE.*tenant_id" services/layer*/src/ --include="*.py"
```

**§2.3 — Inline middleware:**
```bash
grep -rn "app\.use\|app\.add_middleware\|@app\.middleware" services/layer*/src/api/ --include="*.py"
```

**§2.4 — Inline tools / throwing tools:**
```bash
grep -rn "lambda.*tool\|tools.*=.*\[" services/layer4-agents/src/agents/ --include="*.py"
grep -rn "raise ToolError\|raise ValueError" services/layer4-agents/src/tools/ --include="*.py"
```

**§2.5 — JSON.parse on agent output:**
```bash
grep -rn "json\.loads\|json\.parse\|JSON\.parse" services/layer4-agents/src/ --include="*.py"
```

**§2.6 — Imperative navigation / URL concat:**
```bash
grep -rn "navigate\|useLocation\|router\.push" frontend/client/src/ --include="*.tsx" --include="*.ts"
grep -rn '+ "/' frontend/client/src/ --include="*.tsx" --include="*.ts"
```

### Step 4: Generate Report

Produce a structured report with:

```markdown
## Contract Enforcement Audit — {date}

### Summary
| Contract | Documented | Lint Enforced | CI Blocking | Runtime Guard | Violation Count | Score |
|----------|-----------|---------------|-------------|---------------|-----------------|-------|

### §2.1 Tenant Context Propagation
**Violations found:** {count}
{file:line list}

**Enforcement gaps:**
- [ ] ESLint rule `no-tenant-id-parameter` is {enabled|disabled}
- [ ] CI gate is {blocking|non-blocking|missing}
- [ ] Runtime guard `GovernanceMiddleware` covers {X}% of routes

**Fix suggestions:**
1. Enable ESLint rule in `.eslintrc.js` line {N}
2. Remove `continue-on-error: true` from `.github/workflows/pr-checks.yml` line {N}
3. Migrate {N} instances using `/deprecation-migrator AP-1`

### §2.2 ...
(repeat for each contract)
```

### Step 5: Create Fix Actions

For each enforcement gap found, create a concrete fix:

| Gap Type | Fix |
|----------|-----|
| ESLint rule disabled | Edit `.eslintrc.js` to change `"off"` → `"error"` |
| CI gate non-blocking | Edit `.github/workflows/*.yml` to remove `continue-on-error: true` |
| No runtime guard | Create middleware/decorator for the contract |
| Missing contract test | Create test in `tests/contract/test_{contract}.py` |
| Reference impl not imported | Wire `examples/canonical/` into production code |

## Key Files

- `contract.md` — Canonical contract definitions (§2.1-§2.6)

## See Also

- **Skill:** `skills/contract-enforcement-auditor/SKILL.md` — Programmatic agent skill for contract enforcement auditing
- **Related Workflows:**
  - `/deprecation-migrator` — Fix anti-pattern instances identified during audit
  - `/tool-contract-sync` — Ensure tools, skills, and manifests stay in sync
- `shared/identity/middleware.py` — Runtime auth middleware
