# Test Quality Remediation Report - 2026-04-19

## Phase 1: Discovery - Testing Landscape

### Repository Structure
```
Fabric_4L/
├── services/           # Backend (6 layers)
│   ├── layer1-ingestion/   # 15 test files
│   ├── layer2-extraction/  # 9 test files
│   ├── layer3-knowledge/   # 21 test files
│   ├── layer4-agents/      # 27 test files (1 import error)
│   ├── layer5-ground-truth/# 5 test files
│   └── layer6-benchmarks/  # 1 test file
├── frontend/               # Frontend (Vitest + Playwright)
│   ├── client/src/        # 18 .test.tsx files
│   └── e2e/               # 16 .spec.ts files
└── sdk/python/            # SDK tests (5 files, 48 tests passing)
```

### Frameworks Detected

| Component | Framework | Coverage Tool | CI Integration |
|-----------|-----------|---------------|----------------|
| L1-L6 | pytest | pytest-cov | GitHub Actions |
| Frontend Unit | Vitest | @vitest/coverage-v8 | pr-checks.yml |
| Frontend E2E | Playwright | built-in | e2e workflows |

### Test File Counts by Layer

| Layer | Unit Tests | Integration | E2E | Total |
|-------|------------|-------------|-----|-------|
| L1 | 12 | 3 | - | 15 |
| L2 | 7 | 2 | - | 9 |
| L3 | 10 | 8 | 3 | 21 |
| L4 | 15 | 10 | 2 | 27 |
| L5 | 3 | 2 | - | 5 |
| L6 | 1 | - | - | 1 |
| **Backend Total** | **48** | **25** | **5** | **78** |
| Frontend Unit | 18 | - | - | 18 |
| Frontend E2E | - | - | 16 | 16 |
| **Total** | **66** | **25** | **21** | **112** |

### Pre-existing Issues Identified

#### P0 - Critical (Blocking)
1. **L4 Import Error**: `tests/unit/test_workflow_state_machine.py` - ModuleNotFoundError importing 'src'
2. **Frontend**: 14 failing tests (3.1% failure rate per TEST_QUALITY_AUDIT.md)

#### P1 - Material
1. Frontend tests use brittle selectors (`document.querySelector`, `getByText` with exact strings)
2. Frontend tests mix `fireEvent` and `userEvent`
3. Frontend tests missing MSW handler resets

---

## Phase 2: Audit - Quality Assessment

### Frontend Audit (from TEST_QUALITY_AUDIT.md)

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| GraphExplorer.test.tsx | 12 | 4 FAILING | P0: Brittle selectors, P1: querySelector |
| ValuePacks.test.tsx | 8 | 3 FAILING | P0: Error assertions, P1: fireEvent usage |
| IngestionJobs.test.tsx | 6 | PASSING | P1: Direct API mocking |
| Other page tests | 420 | PASSING | P2: Minor issues |

**Frontend Scores (from audit)**:
- Behavior-Focused: 3/5 (tests implementation details)
- Clear/Readable: 3/5 (magic strings, unclear naming)
- Focused: 4/5 (generally single concern)
- Deterministic: 3/5 (timing issues)
- Isolated: 3/5 (MSW cleanup issues)
- Meaningful: 4/5 (good coverage)
- Maintainable: 2/5 (brittle selectors)

**Frontend Total: 22/35 (Fair - P1 rewrites recommended)**

### Backend Audit - Layer 4 (Sample)

| File | Tests | Status | Issues |
|------|-------|--------|--------|
| test_workflow_state_machine.py | ~20 | ERROR | P0: Import error, cannot run |
| test_checkpoint_resume.py | ~12 | Unknown | Need to verify |
| test_feature_flags.py | ~15 | Unknown | Need to verify |
| test_accounts_api.py | ~20 | Unknown | Need to verify |

---

## Phase 3: Prioritization

### Rewrite Priority Queue

#### P0 - Critical (Immediate)
1. [ ] **L4 test_workflow_state_machine.py** - Fix import error (blocking 20 tests)
2. [ ] **GraphExplorer.test.tsx** - Fix brittle selectors (4 tests failing)
3. [ ] **ValuePacks.test.tsx** - Fix error assertions (3 tests failing)

#### P1 - Material (This Sprint)
1. [ ] **GraphExplorer.test.tsx** - Replace querySelector, use userEvent
2. [ ] **ValuePacks.test.tsx** - Standardize on userEvent, add testid
3. [ ] **IngestionJobs.test.tsx** - Add MSW server reset
4. [ ] **Backend audit** - Check L4, L3 for similar issues

#### P2 - Improvement (Opportunistic)
1. [ ] Frontend - Extract common mock factories
2. [ ] Backend - Add edge case coverage
3. [ ] All - Standardize test naming conventions

---

## Phase 4: Rewrite Plan

### Target 1: L4 Import Error (P0)

**File**: `services/layer4-agents/tests/unit/test_workflow_state_machine.py`

**Issue**: Import error - module path incorrect

**Expected Fix**: Correct import paths for models and workflows

**Effort**: 15 minutes

### Target 2: GraphExplorer.test.tsx (P0)

**File**: `frontend/client/src/pages/GraphExplorer.test.tsx`

**Issues**:
- Line 120: `getByText('Layout: Force ▾')` - exact text match
- Line 153: `document.querySelector('svg')` - implementation coupling

**Fix Strategy**:
1. Replace `getByText` with `getByRole('button', {name: /layout/i})`
2. Replace `querySelector('svg')` with `getByTestId('graph-canvas')` or role
3. Add proper testid to GraphExplorer component

**Effort**: 30 minutes

### Target 3: ValuePacks.test.tsx (P0)

**File**: `frontend/client/src/pages/ValuePacks.test.tsx`

**Issues**:
- Line 326: Error state assertion too specific
- Line 54: `querySelectorAll('.animate-pulse')`
- Uses `fireEvent` instead of `userEvent`

**Fix Strategy**:
1. Assert error state presence, not exact message
2. Replace querySelector with `getByTestId`
3. Use `userEvent.setup()` pattern

**Effort**: 30 minutes

---

## Phase 5: Validation Plan

### Steps
1. Fix import error in L4
2. Run L4 tests - verify all pass
3. Fix GraphExplorer.test.tsx selectors
4. Run frontend tests - verify 4 tests pass
5. Fix ValuePacks.test.tsx
6. Run frontend tests - verify 3 more pass
7. Full suite validation

### Success Criteria
- [ ] L4: All tests pass (0 errors, 0 failures)
- [ ] Frontend: All 14 failing tests pass
- [ ] No P0 issues remain
- [ ] All P1 issues addressed or ticketed
- [ ] Test suite deterministic (run 5x consistently)

---

## Next Actions

1. **Immediate**: Fix L4 import error (15 min)
2. **Next**: Fix GraphExplorer.test.tsx (30 min)
3. **Then**: Fix ValuePacks.test.tsx (30 min)
4. **Finally**: Run full validation

Total estimated time: 2-3 hours for P0 fixes
