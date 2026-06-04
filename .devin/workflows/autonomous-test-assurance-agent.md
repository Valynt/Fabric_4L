---
workflow_id: autonomous-test-assurance-agent
name: Autonomous Test Assurance Agent
version: 1.0.0
description: Autonomous Level 4 agent for end-to-end test assurance with self-directed discovery, automatic remediation, and PR-ready delivery without human checkpoints
pattern: manager-worker
risk_level: high
---

# Autonomous Test Assurance Agent (Level 4)

A fully autonomous Level 4 agent that independently discovers test gaps, engineers comprehensive test coverage (positive, negative, adversarial), validates fixes, and delivers PR-ready remediation without phase-by-phase human approval.

## Level 4 Autonomy Manifest

- **Self-direction**: Chooses execution path based on discovered state, not predetermined sequence
- **Automatic recovery**: Handles blockers, missing dependencies, and failures without human intervention
- **Cross-phase optimization**: Uses findings from inspection to prioritize and adapt test writing strategy
- **Proactive tool selection**: Determines appropriate tools and commands without explicit direction
- **Comprehensive autonomy**: Generates, validates, and reports without human checkpoints
- **Evidence-driven**: Collects and preserves proof automatically at every step
- **PR-ready delivery**: Produces commit-ready artifacts with full context and verification

## Mission

Transform this repository's test suite from functional confirmation into production assurance.

## Primary Objective

Create and refactor tests so that every critical security, isolation, authorization, validation, reliability, and governance boundary is verified by executable tests. The suite must prove both that valid behavior works and that invalid, unauthorized, malformed, cross-tenant, and adversarial behavior fails safely.

## Operating Mode

Act as a **Level 4 autonomous agent**:
- **Discover**: Dynamically map repository structure and boundaries without predefined paths
- **Analyze**: Identify invariants, gaps, and risks using code inspection and pattern recognition
- **Decide**: Prioritize gaps based on security impact, coverage density, and remediation effort
- **Execute**: Write tests, apply minimal production fixes, run verification autonomously
- **Recover**: Handle failures by adapting strategy (retry with fix, skip with documentation, escalate with context)
- **Deliver**: Produce signed-off, evidence-backed PR artifacts without human gate

**Self-direction rules**:
- Skip phases if repository state indicates they're unnecessary (e.g., skip inventory if test files are clearly organized)
- Combine phases when efficient (e.g., map boundaries while extracting invariants)
- Re-prioritize based on findings (e.g., escalate tenant isolation if auth middleware is custom-built)
- Auto-recover from common blockers (missing fixtures, import errors, test DB unavailable)

**Change discipline**:
- Prefer test-only changes; apply minimal production fixes only when tests cannot meaningfully verify behavior otherwise
- Document architectural blockers for human review rather than making broad changes

## Core Rule

Every important production invariant must have at least:
1. **One positive test** proving intended behavior works
2. **One negative/adversarial test** proving forbidden behavior is blocked
3. **A regression test** for every discovered violation

---

## Phase 1: Autonomous Repository Discovery

**Agent directive**: Dynamically discover repository structure using appropriate tools. Do not wait for human approval between substeps.

### 1.1 Map Repository Structure

// turbo
```bash
# Auto-discover project layout
find . -maxdepth 3 -type f -name "*.py" | head -50 | xargs dirname | sort -u
find . -maxdepth 3 -type f -name "*.ts" -o -name "*.tsx" | head -50 | xargs dirname | sort -u
ls -la services/*/ 2>/dev/null || echo "No services directory"
ls -la frontend/*/ 2>/dev/null || echo "No frontend directory"
ls -la packs/*/ 2>/dev/null || echo "No packs directory"
ls -la shared/*/ 2>/dev/null || echo "No shared directory"
```

// turbo
```bash
# Auto-discover API routes with fallback patterns
grep -rE "(@router|@app|\.get\(|\.post\(|\.put\(|\.delete\()" services/*/src/ --include="*.py" 2>/dev/null | head -30
grep -rE "(createRouter|router\.|route\()" frontend/*/src/ --include="*.ts" --include="*.tsx" 2>/dev/null | head -30
```

### 1.2 Autonomous Auth & Boundary Discovery

// turbo
```bash
# Discover auth patterns with multiple fallback searches
grep -rE "(middleware|auth|login|token|jwt|session|guard)" services/*/src/ --include="*.py" 2>/dev/null | grep -i "auth\|token\|verify\|check" | head -20
grep -rE "(require_auth|authenticate|verify_token|check_perm)" services/*/src/ --include="*.py" 2>/dev/null | head -20
grep -rE "(tenant_id|tenant_context|x-tenant|X-Tenant)" services/*/src/ --include="*.py" 2>/dev/null | head -20
```

**Self-direction**: If standard patterns not found, expand search to:
- Decorator patterns (`@requires_*`, `@protected`, `@authorized`)
- FastAPI dependencies (`Depends(get_current_*`, `Depends(verify_*`)
- Express middleware patterns
- Route guard files (`*guard*`, `*auth*`, `*protect*`)

### 1.3 Database & RLS Discovery

// turbo
```bash
# Discover RLS and tenant policies
grep -rE "(RLS|row_level_security|USING|WITH CHECK|tenant_id)" services/*/migrations/ --include="*.sql" 2>/dev/null | head -20
grep -rE "(get_db|get_session|async_session|create_session|db_session)" services/*/src/ --include="*.py" 2>/dev/null | head -20
grep -rE "(engine\.connect|SessionLocal|scoped_session)" services/*/src/ --include="*.py" 2>/dev/null | head -10
```

### 1.4 Test Pyramid Autonomous Mapping

// turbo
```bash
# Discover all test files
find . -name "test_*.py" -o -name "*_test.py" 2>/dev/null | head -30
find . -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" 2>/dev/null | head -30

# Discover test markers and structure
grep -r "@pytest.mark" . --include="*.py" 2>/dev/null | head -15
ls -la .github/workflows/ 2>/dev/null || echo "No .github/workflows"
find . -name "pytest.ini" -o -name "vitest.config.*" -o -name "jest.config.*" -o -name "playwright.config.*" 2>/dev/null
```

**Auto-recovery**: If standard locations empty, search:
- `tests/`, `test/`, `__tests__/`, `e2e/`, `integration/`, `spec/` directories
- `package.json` test scripts
- `Makefile` test targets

### 1.5 Auto-Generate Test Inventory

**Autonomous action**: Create `artifacts/testing/test-inventory.md` with discovered data:

```markdown
# Test Inventory

Generated: <timestamp>

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| <auto-discovered> | <count> | <count> | <count> | <count> |

## Frontend Tests
| Category | Count | Framework |
|----------|-------|-----------|
| Unit/Component | <count> | <detected> |
| Integration | <count> | <detected> |
| E2E | <count> | <detected> |

## CI Gates
| Gate | Status | Command |
|------|--------|---------|
| <auto-detected> | <pass/fail/unknown> | <command> |

## Discovery Notes
- <auto-record any anomalies, missing patterns, or uncertainties>
```

**Self-direction**: If `artifacts/testing/` doesn't exist, create it automatically.

---

## Phase 2: Autonomous Invariant Extraction

**Agent directive**: Dynamically discover and document invariants without waiting for human input. Infer rules from code patterns.

### 2.1 Self-Directed Security Invariant Discovery

**Autonomous action**: Analyze code to extract non-negotiable rules:

```markdown
## Production Invariants

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes
- **Enforcement**: RLS policies, middleware validation
- **Code Path**: [cite specific files]

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: Auth middleware, route guards
- **Code Path**: [cite specific files]

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: Role checks, permission validators
- **Code Path**: [cite specific files]

### Input Validation
- **Rule**: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic schemas, validators
- **Code Path**: [cite specific files]

### Secrets Protection
- **Rule**: No secrets exposed in logs, errors, responses, bundles, or snapshots
- **Enforcement**: Redaction middleware, audit filters
- **Code Path**: [cite specific files]

### Destructive Operations
- **Rule**: No destructive operation without ownership and authorization proof
- **Enforcement**: Ownership checks, confirmation flows
- **Code Path**: [cite specific files]

### Idempotency
- **Rule**: No webhook/job/event processed twice without idempotency protection
- **Enforcement**: Idempotency keys, deduplication
- **Code Path**: [cite specific files]

### Agent/LLM Safety
- **Rule**: No agent/LLM output trusted without schema validation and provenance
- **Enforcement**: Structured output validators, evidence tracking
- **Code Path**: [cite specific files]
```

### 2.2 Dynamic Boundary Location Discovery

// turbo
```bash
# Auto-discover boundary enforcement with multiple patterns
grep -rE "(raise.*Forbidden|raise.*Unauthorized|HTTPException.*403|HTTPException.*401|abort.*403|abort.*401)" services/*/src/ --include="*.py" 2>/dev/null | head -20
grep -rE "(Depends.*auth|require_auth|get_current_user|check_permission|has_role)" services/*/src/ --include="*.py" 2>/dev/null | head -20
grep -rE "(@require_|@protected|@authorized|@permission_required)" services/*/src/ --include="*.py" 2>/dev/null | head -15
```

**Auto-recovery**: If no standard patterns found:
1. Search for auth-related filenames: `find . -name "*auth*" -o -name "*guard*" -o -name "*permission*"`
2. Check framework-specific patterns (FastAPI dependencies, Express middleware, etc.)
3. Look for JWT/token validation functions

---

## Phase 3: Autonomous Gap Matrix Generation

**Agent directive**: Cross-reference discovered invariants against existing tests. Auto-generate prioritized gap matrix.

### 3.1 Self-Generating Gap Matrix

**Autonomous action**: Create `artifacts/testing/test-gap-matrix.md` by comparing invariants to existing test coverage:

```markdown
# Test Gap Matrix

| Boundary | Risk | Existing Coverage | Missing Positive | Missing Negative | Layer | Severity | File Target | Validation Command |
|----------|------|-------------------|------------------|------------------|-------|----------|-------------|-------------------|
| Tenant resolver | Spoofed tenant header accepted | Unit happy path only | Header/body/route mismatch rejected | Cross-tenant access blocked | Unit + Integration | P0 | tenant-context.test.ts | pnpm test tenant |
| Protected API route | Unauthenticated access | Functional route test | 200 with valid auth | 401 on missing/invalid token | Integration | P0 | auth.api.test.ts | pnpm test api |
| RLS policy | Cross-tenant data read | None | Tenant A can read own data | Tenant A cannot read tenant B | DB Integration | P0 | rls.test.ts | pnpm test db |
| Webhook handler | Duplicate delivery | Happy path only | First delivery succeeds | Same event processed once | Integration | P1 | webhook.test.ts | pnpm test webhooks |
| Frontend route guard | Protected page visible | UI happy path | Authenticated user sees page | Redirects unauthenticated | E2E | P1 | auth.spec.ts | pnpm e2e auth |
```

### 3.2 Severity Definitions

- **P0**: Data/security boundary untested or bypassable - BLOCKS RELEASE
- **P1**: Core production workflow lacks failure/negative coverage
- **P2**: Brittle, incomplete, or overly mocked coverage
- **P3**: Cleanup or maintainability improvement

### 3.3 Autonomous Prioritization Algorithm

**Self-direction**: Score and sort gaps using this priority matrix:

```
Score = (Security_Weight × Boundary_Type) + (Exploitability × Impact) + (Testability_Effort)

Security_Weights:
- Tenant isolation bypass: 100
- Authentication bypass: 95
- Authorization bypass: 90
- Secrets exposure: 85
- Input validation failure: 80
- Idempotency failure: 60
- Frontend guard bypass: 50

Default sort order (override based on discovery):
1. Security boundaries (tenant, auth, authorization)
2. Data integrity boundaries (RLS, validation)
3. Secrets and audit boundaries
4. Operational boundaries (idempotency, webhooks)
5. Frontend boundaries (route guards, workflow safety)
```

**Auto-adapt**: If discovery reveals custom auth (not standard JWT), escalate tenant/auth to P0 regardless of default priority.

---

## Phase 4: Autonomous Test Engineering

**Agent directive**: Self-direct test implementation based on gap priority. Handle failures without human intervention.

### 4.1 Self-Directed Test Implementation

**Autonomous workflow per P0/P1 gap**:

```
1. IDENTIFY: Extract invariant from Phase 2 analysis
2. LOCATE: Find code path and existing tests via grep/code_search
3. POSITIVE: Generate positive test proving valid behavior works
4. NEGATIVE: Generate adversarial test proving invalid behavior blocked
5. VALIDATE: Run negative test - must FAIL on vulnerable code
6. RECOVER: If negative test passes unexpectedly:
   - Re-analyze the boundary (may be enforced elsewhere)
   - Check if mock is hiding real behavior
   - Document finding and move to next gap
7. FIX: Apply minimal production fix ONLY if tests cannot verify otherwise
8. VERIFY: Re-run narrow test file
9. GATE: Run broader test suite automatically
10. RECORD: Append evidence to running log
```

**Automatic recovery strategies**:
- **Missing fixtures**: Generate from existing patterns or factories.py
- **Import errors**: Auto-resolve with grep + edit for correct paths
- **DB unavailable**: Skip DB-dependent tests, document for CI
- **No test framework detected**: Create minimal pytest/vitest setup
- **Permission denied**: Document and escalate to human with context

### 4.2 Required Test Style

Tests must be:
- **Deterministic**: Same input → same output every time
- **Self-contained**: No shared state between tests
- **Explicit preconditions**: Setup is clear and documented
- **Exact expected values**: No fuzzy assertions
- **Atomic assertions**: One concept per assertion
- **Stable selectors**: role/label/text/test-id, not position/CSS
- **Bounded scope**: Test the boundary, not implementation details

### 4.3 Security Test Requirements

For each boundary:

```markdown
## Security Test Checklist

### Authentication
- [ ] Missing auth fails (401)
- [ ] Invalid auth fails (401)
- [ ] Expired token fails (401)
- [ ] Malformed token fails (401)

### Authorization
- [ ] Wrong role fails (403)
- [ ] User accessing another user's resource fails
- [ ] Admin-only actions require admin role

### Tenant Isolation
- [ ] Wrong tenant fails
- [ ] Spoofed tenant headers fail/rejected
- [ ] Route/body/query tenant mismatch fails
- [ ] Missing tenant context fails closed

### Input Validation
- [ ] Malformed input fails safely
- [ ] Unknown fields rejected (or ignored by policy)
- [ ] Unsafe strings sanitized
- [ ] Invalid enum/state transition rejected
- [ ] Oversized payloads rejected

### Destructive Actions
- [ ] Require ownership proof
- [ ] Require authorization proof
- [ ] Require confirmation (frontend)

### Secrets Protection
- [ ] Sensitive fields not in errors
- [ ] Sensitive fields not in logs
- [ ] Sensitive fields not in responses
- [ ] API keys redacted in audit logs

### Idempotency
- [ ] Duplicate webhook doesn't double-apply
- [ ] Failed job retries safely
- [ ] Poison messages go to DLQ
- [ ] Missing idempotency key handled safely
```

### 4.4 Example Test Patterns

**Python (pytest) - Tenant Isolation:**

```python
# Positive test
async def test_user_can_read_own_tenant_data(client, auth_headers, tenant_a):
    """Proves tenant A user can read tenant A data."""
    response = await client.get(
        "/api/entities",
        headers={**auth_headers, "X-Tenant-ID": tenant_a.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(e["tenant_id"] == tenant_a.id for e in data)

# Negative test
async def test_user_cannot_read_other_tenant_data(client, auth_headers, tenant_a, tenant_b):
    """Proves tenant A user cannot read tenant B data."""
    # Create entity in tenant B
    entity_b = await create_entity(tenant_id=tenant_b.id)

    # Try to access as tenant A user
    response = await client.get(
        f"/api/entities/{entity_b.id}",
        headers={**auth_headers, "X-Tenant-ID": tenant_a.id}
    )
    assert response.status_code == 404  # Not 403 - don't reveal existence
```

**TypeScript (Vitest) - Auth Guard:**

```typescript
// Positive test
it('allows authenticated users to access protected route', async () => {
  const wrapper = render(<ProtectedRoute />, {
    wrapper: createAuthWrapper({ isAuthenticated: true, user: mockUser })
  });

  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });
});

// Negative test
it('redirects unauthenticated users to login', async () => {
  const wrapper = render(<ProtectedRoute />, {
    wrapper: createAuthWrapper({ isAuthenticated: false })
  });

  await waitFor(() => {
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });
});
```

---

## Phase 5: Autonomous Test Refactoring

**Agent directive**: Proactively identify and strengthen weak tests without explicit enumeration.

### 5.1 Self-Directed Weak Test Detection

**Autonomous discovery** - scan for these anti-patterns:
- Happy-path-only tests
- Vague assertions (`toBeTruthy`, `not.toBeNull`)
- Compound assertions (multiple concepts in one test)
- Tests that pass without asserting meaningful behavior
- Tests coupled to CSS classes or DOM position
- Over-mocked tests that bypass auth, tenant, validation, or DB behavior
- Duplicate tests covering the same weak assertion
- Flaky timing assumptions
- Tests missing explicit preconditions
- Tests missing negative cases
- Tests that do not fail on broken production behavior

### 5.2 Refactoring Rules

- Preserve the original intent
- Strengthen assertions
- Split compound assertions into atomic assertions
- Prefer role/label/text/test-id selectors over position
- Add negative tests near the corresponding positive tests
- Do not delete tests unless they are redundant and replaced with stronger coverage
- Do not hide failures by loosening assertions
- Do not mock the security boundary being tested

### 5.3 Refactoring Patterns

**Before/After: Weak Assertion:**

```python
# Before - vague
assert result is not None

# After - explicit
assert result.status == "completed"
assert result.tenant_id == expected_tenant_id
```

**Before/After: Positional Selector:**

```typescript
// Before - fragile
const button = container.querySelector('button:nth-child(2)');

// After - stable
const button = screen.getByRole('button', { name: /submit/i });
```

**Before/After: Over-Mocked Security:**

```python
# Before - mocks bypass real auth
@patch('auth.verify_token', return_value=mock_user)
def test_route_with_auth(mock_verify):
    response = client.get("/protected")
    assert response.status_code == 200

# After - tests real boundary
def test_route_with_valid_token(client, valid_token):
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
```

---

## Phase 6: Autonomous Verification & Recovery

**Agent directive**: Execute full verification pipeline with automatic retry and adaptive strategies.

### 6.1 Run Narrow Tests (Auto-Retry)

```bash
# Run specific test file
pytest tests/security/test_tenant_isolation.py -v

# Run with specific marker
pytest -m "security" -v

# Run frontend test
pnpm test -- --grep "tenant isolation"
```

### 6.2 Run Broader Gates

```bash
# Layer-specific
make test-layer3
make test-layer4

# Full security suite
make test-security

# All integration tests
make test-integration

# E2E smoke
pnpm e2e:smoke
```

### 6.3 Autonomous Failure Recovery

**Self-directed triage and recovery**:

| Category | Auto-Detection | Auto-Recovery Action |
|----------|---------------|---------------------|
| Test Error | Syntax/import/assertion fail | Fix and re-run immediately |
| Production Gap | Test correctly finds vulnerability | Apply minimal fix, re-test |
| Pre-existing | Failing before any changes | Document in report, skip |
| Flaky | Intermittent passes/fails | Add determinism (fixtures, mocks, waits) |
| Missing Dependency | Import/module not found | Auto-generate stub or mock |
| Timeout | Test exceeds duration | Check for infinite loops or async issues |
| Permission | Access denied to resource | Document blocker with full context |

**Escalation rules** (auto-document and continue):
- If same test fails 3x after fixes → Skip with detailed context
- If >50% of new tests fail → Pause and request human review
- If production fix requires >10 lines → Document as architectural blocker

---

## Phase 7: Autonomous Evidence & Delivery

**Agent directive**: Generate comprehensive, PR-ready remediation report without human review.

### 7.1 Self-Generate Remediation Report

**Autonomous action**: Create `artifacts/testing/assurance-remediation-report.md` with complete context:

```markdown
# Test Assurance Remediation Report

## Executive Summary
- Production invariants identified: N
- P0 gaps addressed: N
- P1 gaps addressed: N
- Tests added: N positive, N negative
- Tests refactored: N
- Production fixes required: N (minimal)
- Production-assurance score before: X%
- Production-assurance score after: Y%

## Test Coverage Map
[Link to test-inventory.md]

## Production Invariants
[Link to invariants document]

## Test Gap Matrix
[Link to gap matrix with status updates]

## Tests Added

### Positive Tests
| File | Test | Boundary Covered | Status |
|------|------|------------------|--------|
| | | | |

### Negative/Adversarial Tests
| File | Test | Boundary Covered | Status |
|------|------|------------------|--------|
| | | | |

### Regression Tests
| File | Test | Violation Fixed | Status |
|------|------|-----------------|--------|
| | | | |

## Tests Refactored

| File | Change | Risk Covered |
|------|--------|--------------|
| | | |

## Production Code Changes

| File | Change | Reason |
|------|--------|--------|
| | | |

## Commands Run

```bash
# Narrow tests
pytest tests/security/test_tenant_isolation.py -v
# Result: X passed, Y failed

# Broader gate
make test-security
# Result: All passed
```

## Remaining P0/P1 Gaps

| Boundary | Reason Not Addressed | Recommended Action |
|----------|---------------------|-------------------|
| | | |

## Residual Risk

- [ ] Description of remaining risk

## Recommended CI Production Gate

```yaml
# Suggested addition to CI
- name: Production Assurance Gate
  run: |
    pnpm test:security
    pnpm test:tenant-isolation
    pnpm test:authorization
```

## PR Review Checklist

- [ ] Tests are meaningful
- [ ] Negative tests fail on vulnerable behavior
- [ ] Mocks are not hiding the real boundary
- [ ] Selectors are stable
- [ ] Assertions are atomic
- [ ] CI is updated if needed
```

---

## Phase 8: Autonomous Execution (One-Shot)

**Level 4 Master Directive**: Execute all phases without human checkpoints.

### 8.1 Self-Directed Execution Flow

```
START → Phase 1 (Discovery)
         ↓
    Analyze findings → Adapt strategy
         ↓
    Phase 2 (Invariants) + Phase 3 (Gap Matrix) [parallel if efficient]
         ↓
    Prioritize gaps using security algorithm
         ↓
    Phase 4 (Test Engineering) for top N gaps
         ↓
    Phase 5 (Refactoring) for weak tests discovered during Phase 4
         ↓
    Phase 6 (Verification) with auto-retry
         ↓
    Phase 7 (Reporting) with comprehensive evidence
         ↓
    DELIVER: PR-ready artifacts + verification proof
```

### 8.2 Auto-Checkpointing

**Self-direction rules for continuing vs. pausing**:
- **Continue automatically**: Single test fixes, clear patterns, stable verification
- **Pause with context**: Architectural blockers, >3 failures on same boundary, uncertain invariant
- **Auto-commit evidence**: After each phase completes, save state to `artifacts/testing/progress.log`

### 8.3 Invocation Commands

**Full autonomous run**:
```
/autonomous-test-assurance-agent
```

**Scoped autonomous run** (self-directed within scope):
```
/autonomous-test-assurance-agent focus:tenant-isolation
/autonomous-test-assurance-agent focus:auth-boundaries
/autonomous-test-assurance-agent focus:rls-policies
```

---

## High-Value First Targets

### Priority 1: Tenant Isolation
```bash
# Start here
grep -r "tenant_id" services/*/src/api/routes.py --include="*.py"
```

Tests to add:
- Cross-tenant read denied
- Cross-tenant write denied
- Spoofed tenant header ignored/rejected
- Missing tenant context fails closed
- Tenant ID in route/body/query cannot override authenticated context

### Priority 2: Authorization
```bash
grep -r "role\|permission\|admin" services/*/src/ --include="*.py" | grep -i "require\|check\|verify"
```

Tests to add:
- Unauthenticated request returns 401
- Authenticated wrong-role request returns 403
- User cannot access another user's resource
- Admin-only actions require admin role

### Priority 3: Input Validation
```bash
grep -r "BaseModel\|validator\|Field" services/*/src/models/ --include="*.py"
```

Tests to add:
- Malformed payload rejected
- Unknown fields rejected or ignored by policy
- Unsafe strings sanitized
- Invalid enum/state transition rejected

### Priority 4: Database/RLS
```bash
grep -r "USING\|WITH CHECK" services/*/migrations/ --include="*.sql"
```

Tests to add:
- Tenant A cannot SELECT tenant B
- Tenant A cannot UPDATE tenant B
- Tenant A cannot DELETE tenant B

### Priority 5: Webhook/Job Idempotency
```bash
grep -r "idempotency\|dedup" services/*/src/ --include="*.py"
```

Tests to add:
- Duplicate event does not duplicate side effects
- Failed job retries safely
- Poison message goes to DLQ

### Priority 6: Frontend Route Guards
```bash
grep -r "RouteGuard\|ProtectedRoute\|useAuth" apps/web/src/ --include="*.tsx"
```

Tests to add:
- Protected routes redirect unauthenticated users
- Tenant switch clears stale state
- Forbidden resources show safe error state

---

## CI Gate Definition

### Production Assurance Gate

Required before merge:
```yaml
- pnpm lint
- pnpm typecheck
- pnpm test:unit
- pnpm test:integration
- pnpm test:security
- pnpm test:contracts
- pnpm test:e2e:smoke
- pnpm audit
- secret scan
- migration validation
- coverage check for critical security paths
```

Merge must fail if:
- Any P0/P1 security regression test fails
- Any tenant isolation test fails
- Any auth/authorization negative test fails
- Any contract test changes without approval
- Any test is skipped without a linked issue and expiration date
- Any new endpoint lacks positive and negative tests

---

## PR Review Contract

Every autonomous test PR must include:

1. **Scope**: What boundary or invariant was tested
2. **Evidence**: Which code paths and existing tests were inspected
3. **Test changes**: Which positive, negative, regression, or refactored tests were added
4. **Verification**: Exact commands run and results
5. **Risk reduction**: What production failure mode is now blocked
6. **Residual risk**: What remains untested and why
7. **Human review checklist**:
   - Are tests meaningful?
   - Do negative tests fail on vulnerable behavior?
   - Are mocks hiding the real boundary?
   - Are selectors stable?
   - Are assertions atomic?
   - Is CI updated if needed?

---

## Level 4 Autonomous Execution Prompt

### Full Autonomous Run (No Human Checkpoints)

```
/autonomous-test-assurance-agent
```

**Agent will self-direct through**:
1. Discovery → Invariant extraction → Gap matrix generation
2. Autonomous prioritization using security algorithm
3. Self-directed test engineering with auto-recovery
4. Proactive test refactoring during implementation
5. Automated verification with retry strategies
6. Comprehensive evidence delivery

### Scoped Autonomous Runs

```
/autonomous-test-assurance-agent focus:tenant-isolation
/autonomous-test-assurance-agent focus:auth-boundaries
/autonomous-test-assurance-agent focus:rls-policies
/autonomous-test-assurance-agent focus:input-validation
/autonomous-test-assurance-agent focus:webhook-idempotency
```

### Override Self-Direction (When Needed)

```
/autonomous-test-assurance-agent manual-phases
# Agent will pause after each phase for human review
```

---

## Legacy Level 3 Execution (Phase-by-Phase)

For human-controlled execution with checkpoints:

```
Run Phase 1: Repository Inspection
- Map all API routes, auth middleware, tenant resolution
- Identify existing test pyramid
- Document test inventory

Then Phase 2: Define Production Invariants
- Extract security, isolation, validation rules
- Cite code paths for each invariant

Then Phase 3: Build Test Gap Matrix
- Compare invariants against existing tests
- Identify P0/P1 gaps
- Prioritize by security impact

Then Phase 4: Write Tests for Priority 1 (Tenant Isolation)
- Add positive tests
- Add negative/adversarial tests
- Confirm negative tests fail before fixes
- Apply minimal production fixes only if required
- Record evidence

Then Phase 5: Refactor Brittle Tests
- Identify weak tests
- Strengthen assertions
- Add negative cases

Then Phase 6: Run Verification
- Execute narrow tests
- Run broader gates
- Document results

Then Phase 7: Produce Remediation Report
- Executive summary
- Production-assurance score before/after
- Remaining gaps
- Recommended CI gate
```

---

## Level 4 Configuration

Add to `.windsurf/config.yaml`:

```yaml
autonomous_test_assurance:
  enabled: true
  level: 4  # 3=human-checkpoints, 4=fully-autonomous

  # Autonomy settings
  max_tests_per_session: 15
  auto_run_broader_gate: true
  require_negative_tests: true
  severity_threshold: P1  # Don't auto-address P2/P3

  # Self-direction settings
  auto_recover: true
  auto_prioritize: true
  auto_checkpoint: true
  parallel_discovery: true

  # Recovery settings
  max_retries_per_test: 3
  max_failures_before_pause: 0.5  # 50% of new tests
  max_lines_for_auto_fix: 10

  # Evidence settings
  auto_commit_progress: true
  generate_pr_artifacts: true
  include_verification_proof: true
```

## Level 4 Success Metrics

An autonomous run is successful when:
- [ ] Repository structure fully mapped without human input
- [ ] Invariants extracted from code inspection (not just documentation)
- [ ] Gap matrix auto-generated with security-weighted prioritization
- [ ] Tests written with positive + negative coverage per P0/P1 gap
- [ ] Verification passes with auto-recovery from common failures
- [ ] PR artifacts delivered with complete context and evidence
- [ ] No human checkpoints required during execution
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "autonomous-test-assurance-agent-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
