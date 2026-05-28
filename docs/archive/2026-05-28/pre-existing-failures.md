# Pre-Existing Test Failures

**Document Date:** 2026-04-19
**Context:** Phase 5 Validation of Test Quality Remediation

## Summary

During Phase 5 validation, the following failures were identified as **pre-existing issues** unrelated to the P0 fixes applied. These failures are due to environment/infrastructure issues, not code regressions from the test quality remediation work.

---

## Backend (Layer 4)

### Category: Docker Infrastructure Required

**Affected Tests:**
- `tests/test_accounts_api.py::test_list_accounts_empty`
- `tests/test_tenant_rate_limits.py` (collection phase - Docker check)
- Any test using `testcontainers`

**Error Pattern:**
```
docker.errors.DockerException: Error while fetching server API version
```

**Root Cause:**
Testcontainers library requires Docker Desktop or Docker daemon to be running. The test environment does not have Docker available.

**Action Taken:**
- Documented as pre-existing infrastructure requirement
- No code changes made - tests are valid but require Docker environment

---

## Frontend

### Category: Contract Test - Store Mocking Issue

**Affected File:**
- `client/src/pages/EntityBrowser.contract.test.tsx`

**Failure:**
```
TypeError: Cannot destructure property 'searchQuery' of 'useEntityUIStore(...)' as it is undefined.
```

**Count:** 2 tests failing

**Root Cause:**
The `useEntityUIStore` hook is not properly mocked in the contract test setup. This is a pre-existing test isolation issue, not related to the P0 brittle selector fixes applied.

**Action Taken:**
- Documented as pre-existing contract test issue
- Separate from the GraphExplorer and ValuePacks fixes (which are now passing)

---

## P0 Fixes Validation Status

| P0 Issue | Status | Validation Result |
|----------|--------|-------------------|
| 1. L4 Import Paths | ✅ Fixed | 31 tests collect successfully |
| 2. L3 Neo4j Community | ✅ Verified | SchemaInitializer correctly detects edition |
| 3. Frontend GraphExplorer | ✅ Fixed | 9/9 tests passing |
| 4. Frontend ValuePacks | ✅ Fixed | 19/19 tests passing |

**Note:** Docker-dependent tests cannot run in current environment but are valid tests requiring infrastructure.

---

## Recommendations

1. **Docker Environment:** Set up Docker Desktop for integration tests using testcontainers
2. **EntityBrowser Contract Test:** Add proper Zustand store mocking for `useEntityUIStore`
3. **CI/CD:** Ensure GitHub Actions runners have Docker available for full test suite
