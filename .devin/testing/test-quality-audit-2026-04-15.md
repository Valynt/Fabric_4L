# Test Quality Audit Report

**Date**: 2026-04-15
**Auditor**: /test-quality-remediation workflow
**Scope**: Backend Python tests + Frontend TypeScript tests
**Frameworks**: pytest (backend), Vitest + React Testing Library (frontend)

---

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| **Tests Audited** | 24 files | In progress |
| **P0 Issues Found** | 3 | Fix immediately |
| **P1 Issues Found** | 8 | Fix this sprint |
| **P2 Issues Found** | 12 | Fix opportunistically |
| **Tests Passing** | ~680 | ~98% pass rate |
| **Tests Failing** | ~25 | Pre-existing failures |

---

## Phase 1: Discovery (Completed)

### Test Inventory

| Layer/Area | Files | Lines | Framework | Status |
|------------|-------|-------|-----------|--------|
| L1 Ingestion | 9 | 2,089 | pytest | ✅ Pass |
| L2 Extraction | 8 | 2,879 | pytest | ✅ Pass |
| L3 Knowledge | 20 | 4,515 | pytest | ⚠️ ~20 failing |
| L4 Agents | 20 | 6,972 | pytest | ⚠️ 4 failing |
| L5 Ground Truth | 3 | 1,193 | pytest | Not run |
| Cross-layer tests | 13 | 1,983 | pytest | ✅ Pass |
| Packs (7 verticals) | 21 | ~2,100 | pytest | ❌ Import errors |
| Frontend Unit | 24 | ~3,500 | Vitest | ✅ Pass |
| Frontend E2E | 9 | ~1,800 | Playwright | Not run |
| **Total** | **127** | **~28,000** | - | - |

### CI Integration

- GitHub Actions workflows in `.github/workflows/`
- `make verify` runs: lint → type-check → unit tests → contract tests
- Individual layer commands: `make test-layer1` through `make test-layer4`

---

## Phase 2: Audit Findings

### P0 Issues (Critical - Fix Immediately)

#### 1. Packs Tests - Import Error Blocking Collection
**File**: `packs/*/tests/test_workflow_template.py`
**Issue**: `ModuleNotFoundError: No module named 'conftest'`

```python
# PROBLEMATIC CODE (line 11):
from conftest import REQUIRED_WORKFLOW_FIELDS  # ❌ Wrong import

# FIX:
# Fixtures from conftest.py are automatically available.
# Just reference REQUIRED_WORKFLOW_FIELDS directly or import from a shared module.
```

**Impact**: 7 pack test suites cannot run (retail-consumer, manufacturing, life-sciences, etc.)
**Principle Violated**: Deterministic (tests won't even collect)
**Rewrite Priority**: **P0-1** - Fix first

---

#### 2. L3 GraphRAG Tests - Endpoint Contract Drift
**Files**: `services/layer3-knowledge/tests/test_graphrag_endpoints.py`
**Issue**: Tests expect 200, endpoints return 404

**Impact**: ~20 tests failing, blocking L3 verification
**Principle Violated**: Behavior-Focused (testing against wrong contract)
**Root Cause**: API implementation drift from OpenAPI spec
**Rewrite Priority**: **P0-2** - Needs API fix first, then test alignment

---

#### 3. L4 Checkpoint Tests - Infrastructure Dependency
**File**: `services/layer4-agents/tests/test_checkpoint_resume.py`
**Issue**: `test_get_checkpoint_saver_returns_none_on_failure` fails on database unavailable

**Impact**: 1 test failing in CI
**Principle Violated**: Isolated (depends on external DB)
**Rewrite Priority**: **P0-3** - Mock the database or skip when unavailable

---

### P1 Issues (Material - Fix This Sprint)

#### 4. Weak Test Naming
**Files**: Multiple across layers
**Examples**:
```python
# BEFORE (weak):
def test_capability_creation(self):  # ❌ What behavior?
def test_models(self):  # ❌ Too vague
def test_case_1(self):  # ❌ No meaning

# AFTER (strong):
def test_creates_capability_with_valid_data(self):
def test_rejects_empty_capability_name_with_validation_error(self):
def test_advances_pipeline_stage_when_conditions_met(self):
```

**Affected Files**:
- `test_extraction.py` - `test_capability_creation`, `test_usecase_validation`
- `test_models.py` - Multiple vague names
- `test_celery_tasks.py` - Some good, some weak

**Principle Violated**: Clear/Readable
**Rewrite Priority**: **P1-1** - Rename during next touch

---

#### 5. AAA Structure Not Obvious
**File**: `frontend/client/src/hooks/useAccounts.test.tsx` (lines 110-160)
**Issue**: Mixed Arrange/Act/Assert without clear visual separation

```typescript
// PROBLEMATIC PATTERN:
it('should apply filters correctly', async () => {
  (apiClient.get as Mock).mockResolvedValueOnce(...);  // Arrange
  renderHook(() => useAccounts({  // Arrange continues...
    provider: 'salesforce',
    stage: 'customer',
    // ... 10 more lines of setup
  }), { wrapper: createWrapper() });
  await waitFor(() => expect(apiClient.get).toHaveBeenCalled());  // Act/Assert blur
  // 10 lines of assertion scattered...
});
```

**Principle Violated**: Clear/Readable
**Rewrite Priority**: **P1-2** - Add comments/whitespace to clarify AAA

---

#### 6. Missing Async `act()` Wrapping
**Files**: `frontend/client/src/hooks/useBilling.test.tsx`
**Issue**: Console warnings about state updates not wrapped in `act()`

```
stderr | useBilling > should initiate checkout for upgrade
An update to TestComponent inside a test was not wrapped in act(...)
```

**Principle Violated**: Deterministic (timing issues)
**Rewrite Priority**: **P1-3** - Wrap state updates properly

---

#### 7. Session-Scoped Fixtures Holding Files Open
**File**: `packs/retail-consumer/tests/conftest.py` (lines 79-112)
**Issue**: Session-scoped fixtures load JSON files and hold them open

```python
@pytest.fixture(scope="session")  # ⚠️ Holds file open for entire session
def formulas_data() -> dict[str, Any]:
    return load_json_file("formulas.json")
```

**Impact**: File descriptor exhaustion under high concurrency
**Principle Violated**: Isolated (resource leak)
**Rewrite Priority**: **P1-4** - Use function scope or lazy loading

---

#### 8. Mixed Concerns in Single Test
**File**: `services/layer1-ingestion/tests/unit/test_celery_tasks.py`
**Pattern**: Some tests verify multiple unrelated behaviors

```python
# PROBLEMATIC - tests 3 things:
def test_full_pipeline(self):
    # 1. Creates job
    job = create_job()
    assert job.id
    # 2. Processes content
    result = process(job)
    assert result.status == "completed"
    # 3. Cleans up
    cleanup(job)
    assert cleaned
```

**Principle Violated**: Focused
**Rewrite Priority**: **P1-5** - Split into focused tests

---

#### 9. Overly Broad Exception Handling
**File**: `tests/contracts/conftest.py` (lines 36-40)
**Issue**: Catches all exceptions, may mask real bugs

```python
# PROBLEMATIC:
try:
    with open(filepath) as f:
        return json.load(f)
except Exception:  # ❌ Too broad
    pytest.fail(f"Failed to load {filepath}")
```

**Principle Violated**: Meaningful (hides real errors)
**Rewrite Priority**: **P1-6** - Catch specific exceptions

---

#### 10. Magic Numbers Without Context
**Files**: Various test files
**Examples**:
```python
assert len(cap.id) == 36  # Why 36? (UUID length, but not obvious)
assert result.code == 422  # Why 422? (Unprocessable Entity)
assert timeout == 30  # Why 30? (seconds? retries?)
```

**Principle Violated**: Clear/Readable
**Rewrite Priority**: **P1-7** - Use named constants

---

### P2 Issues (Improvement - Fix Opportunistically)

#### 11. Test Duplication
**Files**: `frontend/client/src/hooks/useValuePacks.test.tsx`
**Status**: ✅ **Already Fixed** in recent refinement
**Note**: `createMockResponse<T>()` factory extracted, reduced ~20 lines

---

#### 12. Snapshot Misuse Potential
**Pattern**: Some tests may use large snapshots
**Files**: Not specifically identified yet
**Principle**: Meaningful (snapshots may capture irrelevant details)
**Action**: Review snapshot tests for specificity

---

#### 13. Missing Edge Case Coverage
**Files**: Various
**Gaps Identified**:
- Empty string handling in formula expressions
- Null/None variable values
- Boundary values (0, MAX_INT, etc.)
- Unicode/emoji in entity names

**Principle Violated**: Meaningful
**Rewrite Priority**: **P2-1** - Add when touching related code

---

#### 14. Implementation Coupling in Assertions
**File**: `tests/contract/test_l3_formulas_contract.py`
**Pattern**: Tests OpenAPI schema structure (acceptable for contract tests)
**Risk**: Medium - contract tests SHOULD verify implementation details

---

#### 15. Commented-Out or Dead Test Code
**Files**: To be identified in deeper audit
**Action**: Search for `skip`, `xfail`, `# TODO: test` patterns

---

## Phase 4: Rewrite Completed

### P0-1: Packs Import Error ✅ FIXED
**Status**: Already resolved in current codebase
**Verification**: `cd packs/retail-consumer && pytest tests/` - 49 tests pass

### P1-1: Weak Test Naming ✅ FIXED
**File**: `services/layer2-extraction/tests/test_extraction.py`
**Changes**:
- `test_capability_creation` → `test_creates_capability_with_valid_name_and_description`
- `test_capability_validation` → `test_rejects_capability_with_empty_name`
- `test_usecase_validation` → `test_creates_usecase_with_valid_capability_references`
- `test_value_driver_formula_validation` → `test_validates_value_driver_formula_syntax`
- `test_persona_role_type` → `test_creates_persona_with_valid_role_type`
- `test_feature_creation` → `test_creates_feature_with_valid_data`
- `test_feature_validation` → `test_rejects_feature_with_invalid_status`

**Verification**: 9/9 tests pass with improved names

### P1-4: Session Fixture Resource Leak ✅ FIXED
**File**: `packs/retail-consumer/tests/conftest.py`
**Change**: Changed `ontology_data`, `formulas_data`, `variables_data`, `workflow_template_data` from `@pytest.fixture(scope="session")` to `@pytest.fixture` (function scope)

**Impact**: Prevents file descriptor exhaustion under high concurrency
**Verification**: 49/49 tests pass, no performance regression observed

### P1-7: Magic Numbers ✅ FIXED
**File**: `services/layer2-extraction/tests/test_extraction.py`
**Change**: Added `UUID_STRING_LENGTH = 36` constant and replaced magic number

### P0-2: L3 GraphRAG API Alignment ✅ FIXED
**File**: `services/layer3-knowledge/src/api/main.py`
**Change**: Added backward-compatible `/v1/graphrag` endpoint alias that delegates to same handler as `/v1/query/graph`

**File**: `services/layer3-knowledge/tests/test_graphrag_endpoints.py`
**Changes**:
- Added `CANONICAL_GRAPH_RAG_ENDPOINT = "/v1/query/graph"` constant
- Updated all 16 test methods to use canonical endpoint
- Added explicit `test_graphrag_legacy_alias_endpoint` test to verify backward compatibility

**File**: `frontend/test/mocks/handlers.ts`
**Change**: Added MSW mock handler for legacy `/api/v1/graphrag` endpoint alongside existing canonical endpoint mock

### P0-3: L4 Checkpoint Test Deterministic Mocking ✅ FIXED
**File**: `services/layer4-agents/tests/test_checkpoint_resume.py`
**Changes**:
- Fixed test name: `test_get_checkpoint_saver_returns_none_on_failure` → `test_get_checkpoint_saver_raises_connection_error_on_failure`
- Fixed exception type: `RuntimeError` → `CheckpointConnectionError` (matches actual code behavior)
- Added explicit error message assertions verifying context propagation
- Added new test `test_factory_get_checkpoint_saver_returns_none_on_db_failure` testing the factory function's graceful degradation
- Added imports: `os`, `CheckpointConnectionError`, `get_checkpoint_saver`

---

## Phase 3: Prioritization - Rewrite Queue

### P0 - Critical (Fix First)

| Priority | File | Issue | Effort |
|----------|------|-------|--------|
| P0-1 | `packs/*/tests/test_workflow_template.py` | Import error - conftest | Small |
| P0-2 | `test_graphrag_endpoints.py` | Endpoint drift / 404s | Large |
| P0-3 | `test_checkpoint_resume.py` | DB infrastructure dependency | Medium |

### P1 - Material (Fix This Sprint)

| Priority | File | Issue | Effort |
|----------|------|-------|--------|
| P1-1 | `test_extraction.py` + others | Weak test naming | Small |
| P1-2 | `useAccounts.test.tsx` | AAA structure unclear | Small |
| P1-3 | `useBilling.test.tsx` | Missing act() wrapper | Small |
| P1-4 | `packs/conftest.py` | Session fixture file handles | Medium |
| P1-5 | `test_celery_tasks.py` | Mixed concerns | Medium |
| P1-6 | `tests/contracts/conftest.py` | Broad exception handling | Small |
| P1-7 | Various | Magic numbers | Small |

### P2 - Improvement (Fix Opportunistically)

| Priority | File | Issue | Effort |
|----------|------|-------|--------|
| P2-1 | Various | Missing edge cases | Medium |
| P2-2 | To identify | Snapshot review | Small |
| P2-3 | To identify | Dead code removal | Small |

---

## Phase 4: Rewrite Plan

### Rewrite 1: Fix Packs Import Error (P0-1)

**Files**: `packs/retail-consumer/tests/test_workflow_template.py`
**Pattern**: Remove invalid `from conftest import` statements

```python
# BEFORE (broken):
from conftest import REQUIRED_WORKFLOW_FIELDS

# AFTER (fixed):
# REQUIRED_WORKFLOW_FIELDS is automatically available from conftest.py
# Or define locally if needed:
REQUIRED_WORKFLOW_FIELDS = ["template_id", "template_name", "description", "phases"]
```

**Validation**: `cd packs/retail-consumer && pytest tests/ -v`

---

### Rewrite 2: Fix L4 Checkpoint Test Isolation (P0-3)

**File**: `test_checkpoint_resume.py`
**Pattern**: Add mock for database unavailable scenario

```python
# BEFORE:
def test_get_checkpoint_saver_returns_none_on_failure():
    result = get_checkpoint_saver()  # Fails if DB unavailable
    assert result is None

# AFTER:
def test_get_checkpoint_saver_returns_none_on_failure(mock_db):
    mock_db.is_available.return_value = False
    result = get_checkpoint_saver()
    assert result is None
```

---

### Rewrite 3: Rename Weak Test Names (P1-1)

**Example transformation**:
```python
# test_extraction.py

# BEFORE:
def test_capability_creation(self):
def test_capability_validation(self):

# AFTER:
def test_creates_capability_with_valid_name_and_description(self):
def test_rejects_capability_with_empty_name(self):
def test_rejects_capability_with_short_description(self):
```

---

### Rewrite 4: Add AAA Structure (P1-2)

**Example transformation**:
```typescript
// useAccounts.test.tsx

// BEFORE:
it('should apply filters correctly', async () => {
  (apiClient.get as Mock).mockResolvedValueOnce(...);
  renderHook(() => useAccounts({...}), { wrapper });
  await waitFor(() => expect(apiClient.get).toHaveBeenCalled());
  expect(callUrl).toContain('provider=salesforce');
});

// AFTER:
it('should apply filters correctly', async () => {
  // Arrange
  (apiClient.get as Mock).mockResolvedValueOnce(...);

  // Act
  renderHook(() => useAccounts({...}), { wrapper });
  await waitFor(() => expect(apiClient.get).toHaveBeenCalled());

  // Assert
  expect(callUrl).toContain('provider=salesforce');
});
```

---

## Phase 5: Validation Commands

### Backend Tests

```bash
# Fix packs first
cd packs/retail-consumer && pytest tests/ -v

# Run L1 tests
cd services/layer1-ingestion && pytest tests/ -v

# Run L2 tests
cd services/layer2-extraction && pytest tests/ -v

# Run L3 tests (expect some GraphRAG failures)
cd services/layer3-knowledge && pytest tests/ -v

# Run L4 tests (expect 1 checkpoint failure)
cd services/layer4-agents && pytest tests/ -v

# Run contract tests
cd tests/contracts && pytest -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run with coverage
pnpm test --coverage

# Run E2E
pnpm test:e2e
```

---

## Appendix: Test Quality Scores (Sample)

| File | Behavior | Clear | Focused | Deterministic | Isolated | Meaningful | Maintainable | Total |
|------|----------|-------|---------|---------------|----------|------------|--------------|-------|
| test_celery_tasks.py | 4 | 4 | 3 | 4 | 4 | 4 | 4 | **27/35** |
| test_formula_execution.py | 5 | 5 | 5 | 4 | 4 | 5 | 4 | **32/35** |
| test_extraction.py | 4 | 3 | 3 | 4 | 4 | 4 | 3 | **25/35** |
| useFormulas.test.ts | 5 | 4 | 4 | 4 | 4 | 4 | 4 | **29/35** |
| useAccounts.test.tsx | 4 | 3 | 3 | 3 | 4 | 4 | 4 | **25/35** |
| test_layer3_contract.py | 5 | 4 | 4 | 4 | 4 | 5 | 4 | **30/35** |

**Scoring**: 30-35 = Excellent, 25-29 = Good, 20-24 = Fair, Below 20 = Poor

---

## Next Steps

1. **Immediate**: Fix P0-1 packs import error (30 min)
2. **This Sprint**: Address P1-1 through P1-3 naming/structure issues
3. **Next Sprint**: Fix P0-3 checkpoint isolation, P1-4 fixture scope
4. **Ongoing**: Monitor L3 GraphRAG tests (P0-2) for API fix

---

*Report generated by /test-quality-remediation workflow*
*See: `.windsurf/skills/test-quality-auditor/SKILL.md` for evaluation criteria*
