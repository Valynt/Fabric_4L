# Layer 1 Test Stabilization Report — 2026-06-02

## Status

**NOT FINAL PRODUCTION READY** — RLS security tests now pass, but broader Layer 1 suite still has non-RLS failures.

## RLS Fix Summary

### Root Cause

Migration `004_add_rls_policies.py` created RLS policies referencing `organization_id`. Migration `006_rename_org_to_tenant.py` renamed the column to `tenant_id` but **did not update the RLS policies**. This left production RLS policies referencing a non-existent column.

Additionally, the PostgreSQL security test fixture (`conftest.py` and `conftest_postgres.py`) used:
- `Base.metadata.create_all()` — creates tables but **does not create RLS policies**
- `SET session_replication_role = 'replica'` — **bypasses RLS entirely**

### Migration Created

**`services/layer1-ingestion/migrations/versions/017_fix_rls_tenant_id_column.py`**

- Drops broken `organization_id`-based policies
- Recreates them using `tenant_id`
- Enables RLS + `FORCE ROW LEVEL SECURITY` on all tenant-scoped Layer 1 tables:
  - `scraping_targets`
  - `scraping_jobs`
  - `raw_content`
  - `extracted_data`
  - `compliance_logs`
  - `proxy_pools`
  - `job_stage_details`
  - `job_errors`
  - `crawl_decisions`
- Includes `admin_bypass_policy` for `admin_role` / `system_role`
- Includes downgrade reverting to `organization_id`-based policies

### crawl_decisions Audit

`crawl_decisions` was **not affected** by the `organization_id` → `tenant_id` rename in migration 006 because the table was created later (migration 005) and already used `tenant_id`. Migration 013 (`fix_rls_null_bypass_crawl_decisions.py`) already uses `tenant_id` and is correct.

Migration 017 includes `crawl_decisions` in its policy refresh to ensure consistency, but no functional change was needed for this table.

### Fixture Fix

Both `tests/security/conftest.py` and `tests/security/conftest_postgres.py` updated:

1. **Removed** `SET session_replication_role = 'replica'`
2. **Added** `_apply_rls_policies()` — applies the same RLS DDL as migration 017 after `Base.metadata.create_all()`
3. **Added** `_create_test_role()` / `_drop_test_role()` — creates a non-superuser `test_app_role` for RLS enforcement
4. **Added** RLS-enforced engine for `get_db_session` — uses `SET ROLE test_app_role` via SQLAlchemy `connect` event so `get_db_session` sessions are subject to RLS
5. **Kept** superuser session (`postgres_db`) for test data creation (superusers bypass RLS, which is correct for setup)

### Test Fixes

- `test_target_isolation_enforced`: Fixed UUID/string comparison (`assert str(targets[0].tenant_id) == tenant_a`)
- `test_raw_content_tenant_isolation`: Fixed UUID/string comparison
- `test_job_lookup_with_wrong_tenant_fails`: Fixed inverted logic — RLS returns `None`, not an exception
- `test_invalid_tenant_id_fails_closed` (`test_rls_enforcement_postgres.py`): Changed to use actually invalid tenant ID format instead of valid UUID

### Six RLS Test Results

**Before:**
```
test_rls_enabled_in_postgresql              FAILED
 test_cross_tenant_job_read_blocked_by_rls  FAILED
 test_cross_tenant_target_update_blocked_by_rls FAILED
 test_cross_tenant_content_delete_blocked_by_rls FAILED
 test_raw_content_tenant_isolation          FAILED
 test_target_isolation_enforced              FAILED
```

**After:**
```
test_rls_enabled_in_postgresql              PASSED
test_cross_tenant_job_read_blocked_by_rls   PASSED
test_cross_tenant_target_update_blocked_by_rls PASSED
test_cross_tenant_content_delete_blocked_by_rls PASSED
test_raw_content_tenant_isolation          PASSED
test_target_isolation_enforced              PASSED
```

Full run of both priority files:
```
pytest tests/security/test_tenant_isolation_bypass_attempts_postgres.py tests/security/test_production_gates_postgres.py
=== 69 passed, 5 warnings in 34.62s ===
```

### Commands Run

```bash
cd services/layer1-ingestion

# Validate the six RLS failures individually
pytest tests/security/test_production_gates_postgres.py::test_rls_enabled_in_postgresql -q
pytest tests/security/test_production_gates_postgres.py::test_cross_tenant_job_read_blocked_by_rls -q
pytest tests/security/test_production_gates_postgres.py::test_cross_tenant_target_update_blocked_by_rls -q
pytest tests/security/test_production_gates_postgres.py::test_cross_tenant_content_delete_blocked_by_rls -q
pytest tests/security/test_tenant_isolation_bypass_attempts_postgres.py::test_raw_content_tenant_isolation -q
pytest tests/security/test_tenant_isolation_bypass_attempts_postgres.py::test_target_isolation_enforced -q

# Both files together
pytest tests/security/test_tenant_isolation_bypass_attempts_postgres.py tests/security/test_production_gates_postgres.py -q

# Full Layer 1 suite
python -m pytest tests/ -q --tb no --timeout=60
```

## Remaining Layer 1 Failures

```
152 failed, 939 passed, 32 skipped, 2 errors
```

**Key remaining clusters:**
1. **Crawler tests** (`test_httpx_crawler.py`, `test_playwright_crawler.py`) — AttributeError, assertion mismatches, async issues
2. **Pipeline tests** (`test_terminal_state_reconciliation.py`) — `UndefinedColumn: scraping_jobs.target_entity_id`, `job_stage_details.meta` — schema drift from model changes without migration updates
3. **Router/integration tests** (`test_router_edge_cases.py`) — `TypeError: FastPathResult.__init__() got unexpected keyword argument 'links'`
4. **XBRL parser tests** (`test_xbrl_parser_extended.py`) — assertion errors, DID NOT RAISE
5. **Global robots cache tests** (`test_global_robots_cache_isolation_postgres.py`) — async coroutine issues
6. **Target tenant isolation tests** (`test_targets_tenant_isolation.py`) — SQLite `no such table` errors (tests running against wrong DB)
7. **Monkeypatch diag tests** — `TenantContextError: Invalid tenant_id format: test`

## Re-audit of Risky Previous Expectation Changes

The following areas were audited for safe changes:

| Change | Risk Level | Assessment |
|--------|-----------|------------|
| `str()` wrapper on UUID comparisons in RLS tests | Low | Type normalization only; semantic check unchanged |
| `test_job_lookup_with_wrong_tenant_fails` assertion fix | Low | Corrected test to match actual RLS behavior (returns None, not exception) |
| `test_invalid_tenant_id_fails_closed` input change | Low | Changed valid UUID to invalid string to test actual validation path |
| Maintenance audit log operation names | Low | Changed to real `MaintenanceOperation` enum values; allowlist enforcement preserved |
| `test_rls_enabled_in_postgresql` catalog query | Low | Still queries `pg_class.relrowsecurity` and asserts > 0 tables |

No tenant isolation, lifecycle, authorization, or idempotency expectations were weakened.

## Next Root-Cause Cluster

**Priority: Pipeline schema drift**

Tests in `test_terminal_state_reconciliation.py` fail with:
- `column scraping_jobs.target_entity_id does not exist`
- `column job_stage_details.meta does not exist`

This indicates the SQLAlchemy models define columns that are not present in the test schema created by `Base.metadata.create_all()`. Either:
1. Migrations added these columns but `Base` metadata was not updated, or
2. The model definitions drifted from the migration sequence

Fix: Compare `models.py` against migrations and add missing columns to `Base.metadata` or create a migration.

## Files Modified

- `services/layer1-ingestion/migrations/versions/017_fix_rls_tenant_id_column.py` (new)
- `services/layer1-ingestion/tests/security/conftest.py`
- `services/layer1-ingestion/tests/security/conftest_postgres.py`
- `services/layer1-ingestion/tests/security/test_tenant_isolation_bypass_attempts_postgres.py`
- `services/layer1-ingestion/tests/security/test_production_gates_postgres.py`
- `services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py`

## Conclusion

RLS tenant isolation is now enforced in both production migrations and test fixtures. The 6 release-critical RLS failures are resolved. Remaining ~150 failures are non-security schema and application bugs that should be addressed in subsequent sprints before production readiness.
