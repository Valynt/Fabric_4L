# Frontend Test Remediation Plan

**Status:** Root cause fixed, triage phase initiated  
**Root Cause:** URL composition bug - duplicate `/v1/` from mismatched `VITE_API_BASE` and fallback prefixes  
**Impact:** 7 test failures eliminated, 1 test file restored

---

## Executive Summary

The "MSW unhandled request" errors were not mock configuration drift. They were **URL composition failures** caused by:

- `.env.test`: `VITE_API_BASE=/api/v1` (includes version)
- `client.ts` fallback: `L6_PREFIX='/v1/benchmarks'` (also includes version)
- Result: `/api/v1/v1/benchmarks/datasets` → 404 → "unhandled"

Fix applied: Removed `/v1` from all hardcoded fallback prefixes to align with environment contract.

---

## Ticket List (Exact)

### P0 - Fix Now (URL Contract Protection)

| ID | Title | Scope | AC |
|----|-------|-------|-----|
| **FE-001** | Add URL construction unit tests for apiClient | `frontend/client/src/api/client.test.ts` | Test matrix: base+prefix combinations, trailing slash normalization, edge cases |
| **FE-002** | Audit all .env.* files for prefix consistency | `frontend/.env.*` | Document expected pattern: base includes /v1, prefixes do not |
| **FE-003** | Add runtime URL validation in apiClient (dev only) | `frontend/client/src/api/client.ts` | Detect duplicate /v1/ at request time, warn in development |

### P1 - Triage This Week (Remaining Failures)

| ID | Title | Current Failure | Hypothesis | Verification |
|----|-------|-----------------|------------|--------------|
| **FE-004** | Triage ValuePacks.test.tsx 400 errors | 400 on `/api/v1/value-packs` | Handler reached but payload/method mismatch OR intentional error test | Inspect test intent, add explicit error state assertions |
| **FE-005** | Fix EntityBrowser.contract.test.tsx brittle selectors | Multiple elements matched by text | Missing scoped queries, async timing issues | Replace text selectors with role+name, add `within()` scoping |
| **FE-006** | Verify benchmark handler paths post-fix | Ensure mocks align with new URL pattern | `/api/v1/benchmarks/datasets` vs old `/api/v1/v1/...` | Confirm handlers.ts uses correct paths |

### P2 - Fix Later (Test Hygiene)

| ID | Title | Scope | Notes |
|----|-------|-------|-------|
| **FE-007** | Audit all MSW handlers for path drift | `frontend/test/mocks/handlers.ts` | Background task: ensure mocks stay aligned with apiClient patterns |
| **FE-008** | Add integration test for full request lifecycle | `frontend/e2e/` | End-to-end: component → hook → MSW → response |
| **FE-009** | Document URL construction contract in CONVENTIONS.md | `docs/` | Prevent future developers from re-introducing /v1 duplication |

---

## Severity Ordering (RICE Scored)

| Ticket | Reach | Impact | Confidence | Effort | RICE | Priority |
|--------|-------|--------|------------|--------|------|----------|
| FE-001 | All apiClient users | Prevents regression | High | 2h | 15 | **P0** |
| FE-004 | ValuePacks feature | Blocks feature validation | Medium | 1h | 8 | **P1** |
| FE-005 | EntityBrowser tests | Noise in CI | High | 2h | 6 | **P1** |
| FE-002 | All env configurations | Prevents config drift | High | 1h | 6 | **P0** |
| FE-003 | Dev experience | Early warning | High | 30m | 8 | **P0** |
| FE-006 | Benchmark feature | Verify fix completeness | High | 30m | 10 | **P1** |
| FE-007 | All mock handlers | Long-term stability | Medium | 4h | 3 | **P2** |
| FE-008 | Full stack | Integration safety | Medium | 4h | 2 | **P2** |
| FE-009 | Documentation | Knowledge preservation | High | 30m | 4 | **P2** |

---

## Fix Now vs Later Split

### Fix Now (This Sprint)

**FE-001: URL Construction Tests** ✅ IMPLEMENTED  
Added `client.test.ts` with explicit test matrix covering:
- All 6 layer prefixes (l1-l6)
- Duplicate /v1/ detection (regex assertion)
- Per-layer URL composition validation

**FE-002: Environment Audit**  
Verify and document:
- `.env.development`: `VITE_API_BASE=/api` (no /v1), prefixes have /v1 → valid
- `.env.test`: `VITE_API_BASE=/api/v1` (has /v1), prefixes no /v1 → valid (POST-FIX)
- `.env.production`: Check actual deployment config

**FE-003: Runtime Validation**  
Add to apiClient request method:

```typescript
if (process.env.NODE_ENV === 'development') {
  if (url.includes('/v1/v1/')) {
    console.warn(`[ApiClient] Duplicate /v1/ detected in URL: ${url}. Check VITE_API_BASE and prefix configuration.`);
  }
}
```

### Fix Later (Next Sprint)

**FE-007 through FE-009**  
Background hygiene work. Schedule when P0/P1 queue is clear.

---

## Test Additions to Prevent Regression

### 1. Unit Test: URL Construction (FE-001) ✅ COMPLETE

**File:** `frontend/client/src/api/client.test.ts` (updated)

**Coverage:**
- All 6 layer prefixes (l1-l6)
- Duplicate /v1/ detection via regex
- Per-layer URL composition validation

**Test Cases Added:**
- `never produces duplicate /v1/ segments` - Scans all captured URLs for `/v1/v1/`
- `correctly composes /api/v1 + /benchmarks -> /api/v1/benchmarks` - Specific regression case
- `correctly composes all layer prefixes` - Matrix test for l1-l6

### 2. Integration Test: Request Lifecycle (FE-008)

**File:** `frontend/e2e/api-contract.spec.ts` (new)

**Coverage:**
- Component renders → hook fetches → MSW responds → UI updates
- Error boundary triggers on 500
- Loading states appear during fetch

**Scope:** 3 critical paths (benchmarks, value-packs, entities)

### 3. Contract Test: Handler Alignment (FE-006)

**File:** `frontend/test/mocks/handlers.contract.test.ts` (new)

**Coverage:**
- Every handler path matches apiClient pattern
- No orphaned handlers (paths not called by any hook)
- No missing handlers (hooks calling unmocked paths)

**Approach:** Static analysis - parse handlers.ts and hook files, compare path constants

---

## Success Metrics

| Metric | Before | After Fix | Target (Post-Remediation) |
|--------|--------|-----------|---------------------------|
| Failed Tests | 54 | 47 | <10 |
| Failed Files | 18 | 17 | <5 |
| Unhandled Request Errors | 12 | 3 | 0 |
| URL-related Failures | 7 | 0 | 0 |
| Test Duration | 31s | 31s | <25s |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Other env files have same bug | Medium | High | FE-002 audit |
| Backend expects old URL pattern | Low | Critical | Verify in staging before prod |
| Test fix masks real product bug | Medium | High | FE-004 explicit error assertions |
| Future dev re-introduces /v1 | Medium | Medium | FE-001 regression test, FE-003 runtime warning |

---

## Immediate Next Action

**Execute FE-004:** Triage ValuePacks.test.tsx 400 errors  
**Time Estimate:** 30 minutes  
**Steps:**
1. Read test file to determine if 400 is expected (error case test) or unexpected
2. If expected: add explicit error state assertion instead of relying on console noise
3. If unexpected: inspect handler path vs actual request, fix mismatch

**Merge Criteria:** PR includes either explicit error assertions OR handler path fix + test intent documented in comments

---

## Evidence Chain

1. **Prior State:** Tests failed with "Unhandled request to /api/v1/v1/benchmarks/datasets"
2. **Root Cause:** Double `/v1/` from `VITE_API_BASE=/api/v1` + `L6_PREFIX='/v1/benchmarks'`
3. **Fix Applied:** Removed `/v1` from all fallback prefixes in `client.ts`
4. **Result:** 7 test failures eliminated, "unhandled request" errors reduced from 12 to 3
5. **Protection Added:** FE-001 regression tests now enforce URL construction contract

---

*Plan Version: 1.0*  
*Created: 2026-04-23*  
*FE-001 Status: ✅ Complete*  
*Next: FE-004 (ValuePacks triage)*
