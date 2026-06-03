# Test Quality Audit Report

**Date**: 2026-04-19  
**Scope**: Frontend Vitest Tests  
**Total Test Files**: 32  
**Status**: 27 passed, 5 failed, 15 tests failing

---

## Failing Test Files Summary

| File | Failed | Total | Issue Category |
|------|--------|-------|----------------|
| useModels.test.tsx | 2 | 16 | Error type mismatch (assertion issue) |
| WfPrimitives.test.tsx | 7 | 26 | DOM queries failing (component structure drift) |
| MyModels.test.tsx | 2 | 13 | Component rendering (sidebar elements missing) |
| useGraphQuery.test.ts | 3 | 12 | MSW handler issues / async timeouts |
| useValuePacks.test.tsx | 1 | 6 | Skipped test (error handling) |

---

## Detailed Audit

### 1. useModels.test.tsx

**Failed Test**: `should handle API error state` (line 129-144)

**Issue**: 
- Test expects `error` to be instance of `ModelApiError`
- Hook returns generic `Error` when API call fails
- Error class transformation is missing in hook

**Severity**: P1 - Test is correct, implementation needs fix

**Principle Violations**:
- Maintainable: Test is valid but hook doesn't fulfill contract

**Fix**: Update `useModels.ts` to wrap errors in `ModelApiError`

---

### 2. WfPrimitives.test.tsx

**Failed Tests** (7 tests):
- EntityBadge rendering
- StatusBadge icons
- MetricCard trend display
- PageHeader breadcrumbs
- SectionCard custom className
- Btn button role
- Tabs aria-selected

**Issue**: 
- DOM queries failing - component structure has drifted
- `screen.getByText` not finding elements
- `container.firstElementChild` returning wrong element

**Severity**: P1 - Tests need updating to match current component structure

**Principle Violations**:
- Maintainable: Tests coupled to DOM structure
- Brittle Selectors: Using container queries instead of role/text

**Fix**: Update queries to use accessible selectors (getByRole, getByLabelText)

---

### 3. MyModels.test.tsx

**Failed Tests** (2 tests):
- `should render folder list with counts` (line 246-283)
- Sidebar folder elements not found

**Issue**:
- `screen.getByText("All Models")` fails - element not in document
- Component may not render sidebar as expected

**Severity**: P1 - Component behavior or test setup issue

**Fix**: Debug component rendering, check if sidebar is conditional on auth/state

---

### 4. useGraphQuery.test.ts

**Failed Tests** (3 tests):
- `executes graph query successfully`
- `fetches entity context with default hops`
- `fetches full graph data`

**Issue**:
- MSW handlers not matching actual API endpoints
- Tests timeout waiting for `isSuccess` to become true
- Handler URLs may not match hook implementation

**Severity**: P1 - Handler configuration drift

**Fix**: Align MSW handler URLs with actual hook endpoints

---

## Prioritized Fix Queue

### P1 - Critical (Fix First)
1. **useModels.test.tsx**: Fix error type handling in hook
2. **useGraphQuery.test.ts**: Fix MSW handler URL matching
3. **WfPrimitives.test.tsx**: Update queries to accessible selectors
4. **MyModels.test.tsx**: Debug component rendering issue

### P2 - Improvement
- Add `createWrapperWithRetry` usage for error state tests
- Extract common mock patterns
- Add more specific assertions instead of snapshot-like checks

---

## Quality Principles Assessment

| File | Behavior | Clear | Focused | Deterministic | Isolated | Meaningful | Maintainable | Score |
|------|----------|-------|---------|---------------|----------|------------|--------------|-------|
| useModels.test.tsx | 4 | 4 | 4 | 3 | 4 | 4 | 3 | 26/35 |
| WfPrimitives.test.tsx | 4 | 3 | 5 | 4 | 4 | 3 | 2 | 25/35 |
| MyModels.test.tsx | 4 | 4 | 4 | 3 | 3 | 4 | 3 | 25/35 |
| useGraphQuery.test.ts | 4 | 4 | 4 | 2 | 3 | 4 | 3 | 24/35 |

**Average**: 25/35 (Fair - needs improvement)

---

## Root Cause Analysis

1. **API Contract Drift**: Hook error handling doesn't match test expectations
2. **DOM Structure Drift**: Component structure changed, tests use brittle selectors
3. **MSW Configuration Drift**: Handler URLs don't match actual API calls
4. **Test Isolation Issues**: Some tests may share state through MSW handlers

---

## Next Steps

1. Fix useModels error handling in hook
2. Align MSW handlers with actual endpoints
3. Update WfPrimitives tests to use accessible queries
4. Debug MyModels sidebar rendering
5. Re-run full test suite to verify fixes
