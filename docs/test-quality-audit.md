> **STATUS: ARCHIVED** — historical audit snapshot (2026-05-01). See [docs/archive/INDEX.md](archive/INDEX.md). Current testing strategy lives in [reference/testing-strategy.md](reference/testing-strategy.md).

# Test Quality Audit - May 1, 2026

## Phase 1: Discovery Summary

| Layer | Framework | Test Files | Est. Tests |
|-------|-----------|------------|------------|
| **Backend (Python)** | pytest | 48+ | 500+ |
| **Frontend (TypeScript)** | Vitest | 53 | 300+ |
| **E2E** | Playwright | 20+ | 80+ |

### Test Configuration
- **Python**: `pytest.ini` with markers: `unit`, `integration`, `e2e`, `slow`, `flaky`, `requires_postgres`, `requires_redis`, `requires_neo4j`
- **Frontend**: `vitest.config.ts` with v8 coverage, jsdom environment, MSW for mocking
- **CI**: `.github/workflows/test.yml`, `pr-checks.yml`

---

## Phase 2: Audit Findings

### Critical Issues (P0)

None identified in sampled tests.

### Material Issues (P1)

#### 1. Skipped Frontend Tests (14 tests)
**Location**: Multiple files in `frontend/client/src/`

| File | Skipped Tests | Reason |
|------|---------------|--------|
| `ValuePacks.test.tsx` | 2 | Error state rendering issues, MSW unhandled rejection |
| `useGraphQuery.integration.test.ts` | 1 | Auth matrix - entire describe block skipped |
| `useGraphQuery.property.test.ts` | 3 | Property-based tests pending |
| `useGraphQuery.performance.test.ts` | 2 | Performance tests, flakiness guard |
| `usePlatformSettings.test.tsx` | 1 | Retry path test |
| `useOpportunities.test.ts` | 4 | ApiError throws before validation can rewrap |
| `useGraphQuery.test.ts` | 1 | Error handling - apiClient throws early |

**Impact**: Missing error handling coverage across multiple hooks.

#### 2. Python MCP Gateway Tests (10 tests)
**Location**: `shared/mcp_gateway/tests/unit/test_mcp_gateway_unit.py`

All OAuth/token exchange tests skipped with `@pytest.mark.skip(reason="Requires HTTP mocking")`

**Impact**: Core security flow untested.

#### 3. Weak Test Naming (Sampled)
**Location**: `services/layer1-ingestion/tests/unit/test_models.py`

- `test_create_scraping_job` → should be `test_creates_job_with_valid_configuration`
- `test_job_status_enum` → tests trivial enum values, not behavior
- `test_create_queue_item` → weak naming, no behavior description

#### 4. Missing Edge Case Coverage
**Location**: `services/layer3-knowledge/tests/test_api.py`

- Tests only validate status codes, not response structure
- No tests for malformed JSON, large payloads, or timeout scenarios

### Improvement Opportunities (P2)

#### 1. Test Organization
- Some test files mix unit and integration concerns
- AAA structure not always obvious

#### 2. Mock Data Realism
- Some tests use hardcoded mock data that may not reflect actual API responses

---

## Phase 3: Prioritization

### Rewrite Priority Queue

#### P1 - Material (Fix Soon)
1. **ValuePacks.test.tsx** - Unskip error state tests (2 tests)
2. **useOpportunities.test.ts** - Fix apiClient error wrapping (4 tests)
3. **test_mcp_gateway_unit.py** - Implement HTTP mocking for OAuth tests (10 tests)
4. **test_models.py** - Rename tests for clarity, remove trivial enum tests

#### P2 - Improvement (Nice to Have)
1. **test_api.py** - Add response structure validation
2. **useGraphQuery.*.test.ts** - Complete property-based and performance tests
3. General naming improvements across backend tests

---

## Recommendations

### Immediate Actions
1. Fix the 14 skipped frontend tests - many are due to apiClient throwing before hook can handle
2. Implement HTTP mocking for MCP gateway OAuth flow tests
3. Remove or rename trivial enum value tests

### Medium Term
1. Add contract validation tests that assert on response structure, not just status codes
2. Complete property-based testing for graph queries
3. Standardize test naming convention: `test_<action>_<condition>_<expected>`

### Testing Principles Score (Sampled Files)

| File | Behavior | Clear | Focused | Deterministic | Isolated | Meaningful | Maintainable | Total |
|------|----------|-------|---------|---------------|------------|------------|--------------|-------|
| test_models.py | 3 | 3 | 4 | 5 | 4 | 3 | 3 | 25/35 |
| test_api.py | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 27/35 |
| useValuePacks.test.tsx | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 28/35 |

**Scoring**: 25-29 = Good (minor P1 issues), Below 25 = Fair (P1 rewrites recommended)

---

## Next Steps

Proceed to Phase 4: Rewrite for highest priority items:
1. ValuePacks.test.tsx error state tests
2. useOpportunities.test.ts error handling tests
3. MCP gateway OAuth tests
