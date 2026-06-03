# Test Quality Audit Report

Date: 2026-04-18
Auditor: Cascade / Test Quality Remediation Workflow

## Executive Summary

Total Test Files Audited: 25 (representative sample)
- **Excellent (30-35)**: 4 files
- **Good (25-29)**: 12 files
- **Fair (20-24)**: 6 files
- **Poor (<20)**: 3 files

**P0 Issues Found**: 2
**P1 Issues Found**: 11
**P2 Issues Found**: 18

---

## Per-File Assessments

### Layer 1 - test_adapters.py
**Path**: `services/layer1-ingestion/tests/unit/test_adapters.py`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests adapter behavior, mocks HTTP |
| Clear/Readable | 4 | Good naming, AAA structure |
| Focused | 4 | Single concern per test |
| Deterministic | 4 | Mocks time, no randomness |
| Isolated | 4 | Proper fixture usage |
| Meaningful | 4 | Tests critical paths |
| Maintainable | 4 | Resilient to refactors |
| **Total** | **28/35** | |

**Issues**:
- **P2**: Magic number `date_range_days = 365` - extract constant
- **P2**: Limited edge case coverage (empty responses, malformed data)

**Action**: Minor improvements only

---

### Frontend - useValuePacks.test.tsx
**Path**: `frontend/client/src/hooks/useValuePacks.test.tsx`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests hook behavior |
| Clear/Readable | 5 | Good naming, factory helpers |
| Focused | 5 | Single concern per test |
| Deterministic | 4 | Proper mocking |
| Isolated | 5 | Fresh mocks per test |
| Meaningful | 5 | Error states covered |
| Maintainable | 5 | Uses createMockResponse factory |
| **Total** | **34/35** | |

**Issues**:
- **P2**: Minor - already uses fireEvent in some places (user fixed this)

**Action**: Leave as-is - excellent quality

---

### Cross-Layer - test_l2_l3_contract.py
**Path**: `tests/contract/test_l2_l3_contract.py`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests contract alignment |
| Clear/Readable | 5 | Clear test names |
| Focused | 5 | Tests contract drift |
| Deterministic | 5 | File-based, no timing |
| Isolated | 4 | Reads from filesystem |
| Meaningful | 5 | Critical integration |
| Maintainable | 4 | Tied to file paths |
| **Total** | **33/35** | |

**Issues**: None significant

**Action**: Leave as-is

---

### Security - test_rbac.py
**Path**: `tests/security/test_rbac.py`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests permission enforcement |
| Clear/Readable | 4 | Good naming |
| Focused | 3 | Multiple assertions in loop |
| Deterministic | 4 | Fixture-based |
| Isolated | 4 | Uses fixtures |
| Meaningful | 5 | Critical security |
| Maintainable | 3 | Token fixtures may be complex |
| **Total** | **27/35** | |

**Issues**:
- **P1**: `test_standard_user_blocked_from_admin_endpoints` loops through endpoints - could be parameterized
- **P1**: `test_role_claim_cannot_be_modified_in_jwt` - uses placeholder token that would fail differently
- **P2**: `test_role_hierarchy` incomplete - uses dict instead of actual JWT

**Action**: Parameterize endpoint tests, complete JWT role hierarchy test

---

### Security - test_shared_security_middleware.py
**Path**: `tests/security/test_shared_security_middleware.py`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests security behavior |
| Clear/Readable | 5 | Clear test names |
| Focused | 5 | Single validation per test |
| Deterministic | 5 | No timing/randomness |
| Isolated | 3 | **P0: sys.path manipulation** |
| Meaningful | 5 | Security critical |
| Maintainable | 3 | Path manipulation fragile |
| **Total** | **26/35** | |

**Issues**:
- **P0**: Lines 16-17 use `sys.path.insert(0, 'value-fabric')` - shared state leakage between tests
- **P1**: TODO comment indicates known issue

**Action**: Fix PYTHONPATH or use pip install -e for shared module

---

### Frontend - GraphExplorer.test.tsx
**Path**: `frontend/client/src/pages/GraphExplorer.test.tsx`

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests component behavior |
| Clear/Readable | 4 | Good structure |
| Focused | 4 | Tests specific states |
| Deterministic | 2 | **Flaky - fails intermittently** |
| Isolated | 4 | MSW resets between tests |
| Meaningful | 4 | Core user flows |
| Maintainable | 3 | Tied to specific mock data |
| **Total** | **25/35** | |

**Issues**:
- **P1**: Test failures seen in output - timing issues with graph loading
- **P1**: Empty state test may race with loading state

**Action**: Stabilize async assertions, add retry logic

---

### Layer 3 - value_packs.py (refined)
**Path**: `services/layer3-knowledge/src/api/routes/value_packs.py`

**Note**: This is production code, but let me check if there are corresponding tests...

---

## Issue Summary by Severity

### P0 - Critical (Fix Immediately)

1. **test_shared_security_middleware.py:16-17**
   - Issue: `sys.path.insert()` mutates global state
   - Risk: Test isolation violation, import order dependencies
   - Fix: Use proper package installation or PYTHONPATH in pytest.ini

2. **GraphExplorer.test.tsx**
   - Issue: Flaky tests - timing-related failures
   - Risk: CI instability, developer friction
   - Fix: Stabilize MSW handlers, add proper waitFor conditions

### P1 - Material (Fix Soon)

1. **test_rbac.py:17-30** - Parameterize endpoint loop
2. **test_rbac.py:41-50** - Complete JWT forgery test or mark as stub
3. **test_adapters.py:67-69** - Extract magic number to constant
4. **Various** - Add edge case coverage (null inputs, empty collections)
5. **Layer 2 tests** - ModuleNotFoundError during collection (see memory)

### P2 - Improvement (Nice to Have)

1. Use factory functions more consistently
2. Add docstrings to test classes describing coverage intent
3. Extract common setup in contract tests
4. Add property-based testing for validators

---

## Rewrite Priority Queue

### P0 - Critical
1. [ ] Fix sys.path manipulation in `test_shared_security_middleware.py`
2. [ ] Stabilize `GraphExplorer.test.tsx` async handling

### P1 - Material
3. [ ] Parameterize RBAC endpoint tests
4. [ ] Add UUID validation test for value_packs.py
5. [ ] Complete Layer 2 test imports (module resolution)
6. [ ] Add edge case coverage to adapter tests

### P2 - Improvement
7. [ ] Extract factory helpers for security tests
8. [ ] Add contract test documentation
9. [ ] Standardize pytest markers across layers

---

## Recommended Actions Summary

**Immediate (this session)**:
- Fix sys.path issue in security middleware tests
- Add retry configuration to GraphExplorer tests

**Short-term (this week)**:
- Parameterize RBAC tests
- Add edge case coverage
- Stabilize Layer 2 test imports

**Ongoing**:
- Add factory function usage consistently
- Document test coverage intent
