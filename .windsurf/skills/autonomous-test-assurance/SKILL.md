---
skill_id: autonomous-test-assurance
name: autonomous-test-assurance
version: 1.0.0
description: Skill definition for Level 4 fully-autonomous test assurance agent with self-directed discovery, automatic recovery, and PR-ready delivery without human checkpoints
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
  - test_inventory
allowed_agents:
  - "*"
---

# Autonomous Test Assurance Agent - Skill Definition (Level 4)

## Overview

This skill enables the agent to operate as a **Level 4 fully-autonomous test assurance agent** that independently discovers test gaps, engineers comprehensive coverage, and delivers PR-ready remediation without phase-by-phase human approval.

## Core Philosophy

The strongest test suites prove both:
1. **Valid behavior works** (positive tests)
2. **Invalid/attack behavior is blocked** (negative/adversarial tests)

Every production invariant must have positive, negative, and regression coverage.

## Prompting Principles (From Harness.io Research)

AI test automation only becomes reliable when prompts are:
- **Specific**: Clear scope, not vague "test everything"
- **Self-contained**: Include all context needed
- **Assertion-driven**: Define exact expected outcomes
- **Bounded**: Limited scope, verifiable completion

### Prompt Structure Template

```
Goal: [What boundary to test]
Context: [Code paths involved]
Specifics: [Exact inputs, expected outputs]
Assertion: [What must be true for success]
Boundaries: [What is in/out of scope]
```

## Agent Autonomy Levels

### Level 4 - Fully Autonomous Agent (This Skill)
- ✅ Self-directed repository discovery with fallback patterns
- ✅ Automatic invariant extraction from code inspection
- ✅ Autonomous gap matrix generation with security-weighted prioritization
- ✅ Self-directed test engineering with automatic recovery
- ✅ Proactive weak test detection and refactoring
- ✅ Automatic verification with retry strategies
- ✅ PR-ready evidence delivery without human checkpoints
- ✅ Cross-phase optimization and adaptive strategy

### Level 5 - Continuous Agent (Future)
- Continuous monitoring and auto-repair
- Predictive test gap detection
- Self-improving test generation

This skill implements **Level 4** with optional human override via `manual-phases` flag.

---

## Production Invariant Categories

### 1. Tenant Isolation

**Definition**: Multi-tenant systems must prevent cross-tenant data access.

**Key Tests**:
- Positive: Tenant A can read/write own data
- Negative: Tenant A cannot read/write tenant B data
- Adversarial: Spoofed headers fail, missing context fails closed

**Code Patterns to Find**:
```python
# Middleware
grep -r "X-Tenant-ID\|tenant_context\|get_tenant" --include="*.py"

# RLS Policies
grep -r "tenant_id = current_setting" --include="*.sql"
grep -r "USING.*tenant_id" --include="*.sql"

# Route handlers
grep -r "tenant_id\s*:" --include="*.py"
```

**Test Pattern**:
```python
async def test_cannot_access_other_tenant_data(client, tenant_a, tenant_b):
    # Create data in tenant B
    entity = await create_entity(tenant_id=tenant_b.id)
    
    # Attempt access as tenant A
    response = await client.get(
        f"/entities/{entity.id}",
        headers={"X-Tenant-ID": tenant_a.id}
    )
    
    # Should fail - 404 (don't reveal existence) or 403
    assert response.status_code in [404, 403]
```

### 2. Authentication

**Definition**: Protected resources require valid authentication.

**Key Tests**:
- Positive: Valid token allows access
- Negative: Missing/invalid/expired token denied
- Adversarial: Malformed headers, replay attacks

**Code Patterns**:
```python
grep -r "Depends.*auth\|require_auth" --include="*.py"
grep -r "Authorization.*Bearer" --include="*.py"
```

### 3. Authorization

**Definition**: Authenticated users can only access permitted resources.

**Key Tests**:
- Positive: User with permission succeeds
- Negative: Wrong role gets 403
- Negative: User accessing other's resources fails

**Code Patterns**:
```python
grep -r "role\|permission\|admin_required" --include="*.py"
grep -r "HTTPException.*403\|Forbidden" --include="*.py"
```

### 4. Input Validation

**Definition**: All input is validated before processing.

**Key Tests**:
- Positive: Valid input accepted
- Negative: Malformed input rejected with clear error
- Negative: Oversized payloads rejected
- Negative: Invalid enums rejected

**Code Patterns**:
```python
grep -r "BaseModel\|validator\|Field(" --include="*.py"
grep -r "ValidationError\|422" --include="*.py"
```

### 5. Secrets Protection

**Definition**: Sensitive data never appears in logs/errors/responses.

**Key Tests**:
- Negative: API keys not in error messages
- Negative: Passwords not in logs
- Negative: Tokens not in audit logs

**Code Patterns**:
```python
grep -r "redact\|mask\|sanitize" --include="*.py"
grep -r "api_key\|password\|token" --include="*.py" | grep -v test
```

### 6. Idempotency

**Definition**: Duplicate operations have no additional side effects.

**Key Tests**:
- Positive: First request succeeds
- Negative: Same idempotency key → same response, no side effects
- Negative: Different key with same payload → handled correctly

**Code Patterns**:
```python
grep -r "idempotency\|Idempotency-Key" --include="*.py"
grep -r "dedup\|duplicate" --include="*.py"
```

### 7. Agent/LLM Safety

**Definition**: Agent outputs are validated and actions are bounded.

**Key Tests**:
- Positive: Valid schema output accepted
- Negative: Invalid schema rejected
- Negative: Prompt injection attempts blocked
- Negative: Unsupported tool calls fail

---

## Test Quality Anti-Patterns

### Pattern 1: Happy-Path-Only
```python
# BAD - only tests success
def test_create_user():
    user = create_user(email="test@example.com")
    assert user.id is not None

# GOOD - tests both success and failure
def test_create_user_success():
    user = create_user(email="test@example.com")
    assert user.email == "test@example.com"
    assert user.status == "active"

def test_create_user_duplicate_email_fails():
    create_user(email="test@example.com")
    with pytest.raises(DuplicateError):
        create_user(email="test@example.com")
```

### Pattern 2: Vague Assertions
```python
# BAD - what does this prove?
assert result is not None
assert len(data) > 0

# GOOD - exact expected values
assert result.status == "completed"
assert result.tenant_id == expected_tenant_id
assert data == [expected_item_1, expected_item_2]
```

### Pattern 3: Over-Mocking Security Boundaries
```python
# BAD - mocks bypass real auth
@patch('auth.verify_token')
def test_route(mock_verify):
    mock_verify.return_value = mock_user
    response = client.get("/protected")
    assert response.status_code == 200

# GOOD - tests real boundary with valid token
def test_route_with_valid_token(client, valid_token):
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
```

### Pattern 4: Positional Selectors
```typescript
// BAD - fragile to UI changes
const button = container.querySelector('button:nth-child(2)');

// GOOD - stable semantic selector
const button = screen.getByRole('button', { name: /submit/i });
```

### Pattern 5: Compound Assertions
```python
# BAD - multiple concepts, unclear failure
def test_full_flow():
    x = create()
    assert x.id and x.status == "pending"
    y = update(x)
    assert y.status == "active" and y.updated_at > x.created_at
    delete(y)
    assert get(y.id) is None

# GOOD - one concept per test
def test_creates_with_valid_data():
    x = create()
    assert x.status == "pending"

def test_update_activates_record():
    x = create()
    y = update(x.id, {"status": "active"})
    assert y.status == "active"

def test_delete_removes_access():
    x = create()
    delete(x.id)
    assert get(x.id) is None  # or 404
```

---

## Test Pyramid for Production Assurance

### Layer 1: Unit Security Tests
**Purpose**: Prove small boundary functions fail closed

**Targets**:
- `tenant_resolver()` - returns correct tenant or None
- `auth_context_parser()` - validates tokens correctly
- `role_checker()` - enforces permissions
- `input_validators()` - rejects invalid input
- `schema_guards()` - validates structure
- `ownership_check()` - verifies resource ownership
- `sanitizer()` - removes dangerous content
- `idempotency_key_logic()` - handles duplicates

### Layer 2: Integration Tests
**Purpose**: Prove real service/database/API behavior preserves boundaries

**Targets**:
- API route + middleware + database access
- Tenant-scoped queries with real RLS
- Migration behavior
- Webhook handlers with real payload parsing
- Background jobs with real queue semantics
- Agent/tool invocation with real LLM responses

### Layer 3: Contract Tests
**Purpose**: Prove request/response/security contracts are stable

**Targets**:
- OpenAPI/Zod schemas enforce required fields
- Error envelopes include expected fields, exclude sensitive data
- Auth requirements documented and enforced
- 401/403 responses consistent
- Tenant-scoped API contracts stable

### Layer 4: E2E Assurance Tests
**Purpose**: Prove user-visible workflows and denial paths

**Targets**:
- Login/logout flows
- Account switching clears state
- Tenant data visibility boundaries
- Role-based UI behavior
- Protected route redirects
- Destructive actions require confirmation
- Audit trail visibility
- Export/share workflows respect permissions

### Layer 5: CI Production Gate
**Purpose**: Block unsafe merges

**Required Gates**:
- Lint + typecheck
- Unit tests (all)
- Integration tests (all)
- Security regression suite
- Contract tests
- E2E smoke tests
- Dependency audit
- Secret scan
- Migration validation
- Coverage threshold for critical paths

---

## Severity Definitions

### P0 - BLOCKS RELEASE
Data or security boundary that is:
- Completely untested, OR
- Tested but bypassable, OR
- Has tests that don't fail on broken behavior

Examples:
- No cross-tenant read test
- Auth tests mock the boundary they should test
- RLS policy exists but not tested

### P1 - MUST FIX IN SPRINT
Core production workflow that:
- Has only happy-path tests
- Missing negative/failure cases
- Has brittle selectors or timing assumptions

Examples:
- API has success tests but no validation failure tests
- Frontend has success render tests but no error state tests

### P2 - IMPROVEMENT
Coverage that:
- Uses over-mocking (bypasses real behavior)
- Has vague assertions
- Tests implementation details unnecessarily

### P3 - CLEANUP
Maintainability improvements:
- Test naming
- File organization
- Setup extraction

---

## Test Writing Guidelines

### Precondition Guards

Always verify preconditions before the action:

```python
def test_user_cannot_delete_other_user_resource():
    # Given: Two users with their own resources
    user_a = create_user()
    resource_a = create_resource(owner_id=user_a.id)
    
    user_b = create_user()
    
    # Verify precondition
    assert get_resource(resource_a.id).owner_id == user_a.id
    
    # When: User B tries to delete User A's resource
    result = delete_resource(resource_a.id, as_user=user_b)
    
    # Then: Operation is denied
    assert result.status_code == 403
    
    # And: Resource still exists
    assert get_resource(resource_a.id) is not None
```

### Atomic Assertions

Split compound assertions:

```python
# BAD
assert response.status_code == 200 and response.json()["count"] == 5

# GOOD
assert response.status_code == 200
assert response.json()["count"] == 5
```

### Content-Based Selectors

Never use positional or CSS selectors:

```typescript
// BAD - fragile
screen.querySelector('.btn-primary');
screen.querySelector('button:nth-child(2)');

// GOOD - stable
screen.getByRole('button', { name: /submit/i });
screen.getByLabelText(/email address/i);
screen.getByTestId('submit-button');
```

### Fallback Instructions

Tests should have clear failure messages:

```python
assert response.status_code == 404, (
    f"Expected 404 (not found) to avoid revealing resource existence, "
    f"got {response.status_code} with body: {response.text}"
)
```

---

## Evidence Requirements

For every change, record:

1. **File changed**: Exact path
2. **Test added/refactored**: Function name
3. **Risk covered**: What failure mode is blocked
4. **Command run**: Exact test command
5. **Before/after result**: Pass/fail status
6. **Remaining uncertainty**: What's still untested

---

## Commands Reference

### Discovery Commands
```bash
# Find auth middleware
grep -r "middleware\|Depends.*auth" --include="*.py"

# Find tenant handling
grep -r "tenant_id\|X-Tenant" --include="*.py"

# Find validation
grep -r "validator\|BaseModel" --include="*.py"

# Find RLS
grep -r "USING\|WITH CHECK" --include="*.sql"
```

### Test Commands
```bash
# Python single test
pytest tests/security/test_tenant_isolation.py::test_cannot_access_other_tenant -v

# Python with coverage
pytest --cov=src --cov-report=term-missing tests/security/

# TypeScript single test
pnpm test -- --grep "tenant isolation"

# Playwright E2E
pnpm e2e --grep "auth"
```

### CI Gate Commands
```bash
# Full assurance gate
make test-security
make test-integration
pnpm test:contract
pnpm e2e:smoke
```

---

## Verification Checklist

Before marking any boundary as tested:

- [ ] Positive test exists and passes
- [ ] Negative test exists and passes
- [ ] Negative test would fail on vulnerable code (verified or assumed)
- [ ] No mocks bypass the boundary under test
- [ ] Assertions are explicit (exact values, not `is not None`)
- [ ] Selectors are semantic (role/label/test-id)
- [ ] Precondition guards verify setup
- [ ] Test is deterministic (run 5x, same result)
- [ ] Test is isolated (no shared state)
- [ ] Evidence documented

---

## Output Templates

### Test Addition Entry
```markdown
## Test: test_user_cannot_access_other_tenant
**File**: `tests/security/test_tenant_isolation.py`
**Boundary**: Tenant isolation (read)
**Type**: Negative/adversarial
**Risk Covered**: Prevents cross-tenant data leakage via direct ID access
**Command**: `pytest tests/security/test_tenant_isolation.py::test_user_cannot_access_other_tenant -v`
**Result**: ✅ PASS
**Evidence**: Confirmed 404 response when tenant A accesses tenant B resource
```

### Refactor Entry
```markdown
## Refactored: test_api_auth
**File**: `tests/api/test_auth.py`
**Issue**: Over-mocked - @patch bypassed real token validation
**Change**: Replaced mock with real token generation using test fixtures
**Risk Covered**: Real JWT validation boundary, not mocked behavior
**Command**: `pytest tests/api/test_auth.py -v`
**Result**: ✅ PASS (run 5x, deterministic)
```
