# Layer 1 Test Failure Analysis

## Summary

- **Total Tests**: 1,123 (892 passed, 199 failed, 32 skipped)
- **Duration**: 146.74s
- **Failed Tests**: 199

---

## 1. Database Schema Mismatch — `scraping_jobs.job_type` Column Missing

**Impact**: ~60+ tests failed directly, cascading to many more.
**Error**: `psycopg2.errors.UndefinedColumn: column scraping_jobs.job_type does not exist`

**Affected Test Files**:
- `tests/security/test_production_gates_postgres.py` (9 failures)
- `tests/security/test_celery_tenant_isolation_postgres.py` (5 failures)
- `tests/security/test_rls_enforcement_postgres.py` (8 failures)
- `tests/security/test_maintenance_tenant_enumeration.py` (2 failures)
- `tests/security/test_crawl_decisions_tenant_isolation_postgres.py` (4 failures)
- `tests/pipeline/test_terminal_state_reconciliation.py` (6 failures — cascade from SQLite `created_by` issue)
- `tests/api/test_targets_execute_idempotency.py` (likely affected)

**Root Cause**: The SQLAlchemy model for `ScrapingJob` defines a `job_type` column that does not exist in the actual database schema. The model was updated but the migration was not applied (or was never created).

---

## 2. Database Integrity — `created_by` NOT NULL Violation

**Impact**: ~20+ tests
**Errors**:
- `sqlite3.IntegrityError: NOT NULL constraint failed: scraping_jobs.created_by`
- `psycopg2.errors.NotNullViolation: null value in column "created_by" of relation "scraping_targets"`

**Affected Test Files**:
- `tests/pipeline/test_terminal_state_reconciliation.py` (6 failures)
- `tests/unit/test_database_optional_tenant_security.py` (2 failures)
- Various integration tests creating `ScrapingJob` or `ScrapingTarget` without `created_by`

**Root Cause**: The `created_by` field was made NOT NULL but test fixtures/job creation helpers do not populate it.

---

## 3. Missing `tenant_id` Parameter in Refactored Task Functions

**Impact**: ~40+ tests
**Error**: `TypeError: <function>() missing 1 required positional argument: 'tenant_id'`

**Affected Functions & Test Files**:
- `storage_stage()` — `tests/integration/test_skill_pipeline.py` (8 failures)
- `notification_stage()` — `tests/unit/test_event_outbox.py` (5 failures), `tests/integration/test_skill_pipeline.py`
- `validation_stage()` — `tests/unit/test_validation.py` (7 failures)
- `dispatch_outbox_event()` — `tests/unit/test_event_outbox.py` (4 failures)
- `compliance_check_stage()` — `tests/unit/test_celery_tasks.py` (3 failures)
- `cleanup_old_content()` — `tests/unit/test_celery_tasks.py` (2 failures)
- `crawl_url_with_routing()` — `tests/unit/test_celery_tasks.py`, `tests/security/test_celery_tenant_isolation_postgres.py`

**Root Cause**: Task functions were refactored to require an explicit `tenant_id` parameter for tenant isolation, but existing test callers were not updated.

---

## 4. Broken Import / Module Path Issues

**Impact**: ~25+ tests
**Errors**:
- `AttributeError: module 'src' has no attribute 'crawler'`
- `ModuleNotFoundError: No module named 'src.shared.database'`
- `ModuleNotFoundError: No module named 'shared.config'; 'shared' is not a package`
- `AttributeError: <module 'layer1_ingestion.shared.tasks'> does not have the attribute 'validate_tenant_id'`

**Affected Test Files**:
- `tests/unit/test_playwright_crawler.py` (13 failures)
- `tests/unit/test_crawler_telemetry.py` (6 failures)
- `tests/unit/test_import_surface.py` (1 failure)
- `tests/unit/test_h03_security_config.py` (9 failures)
- `tests/security/test_tenant_isolation_bypass_attempts_postgres.py` (2 failures)
- `tests/unit/test_m02_exception_remediation.py` (2 failures — `REDIS_AVAILABLE` import)

**Root Cause**: Compatibility shims (`src.crawler`, `src.shared.database`) are broken or incomplete. The `shared.config` module path is wrong. `validate_tenant_id` was removed/renamed from `tasks.py`.

---

## 5. System Maintenance Authorization Failures

**Impact**: ~20+ tests
**Error**: `SystemMaintenanceAuthorizationError: Invalid or missing system maintenance identity`

**Affected Test Files**:
- `tests/security/test_system_maintenance_authorization_postgres.py` (13 failures)
- `tests/unit/test_celery_tasks.py` (2 failures — `cleanup_old_content`)
- `tests/security/test_maintenance_tenant_enumeration.py` (2 failures)

**Root Cause**: Maintenance operations now require a valid system maintenance identity token, but tests do not provide one or mock it incorrectly.

---

## 6. `robots_txt_cache` Tenant Isolation Issues

**Impact**: ~10 tests
**Errors**:
- `psycopg2.errors.NotNullViolation: null value in column "tenant_id" of relation "robots_txt_cache"`
- `AssertionError: assert None is not None`
- `ValueError: a coroutine was expected, got None`

**Affected Test Files**:
- `tests/security/test_global_robots_cache_isolation_postgres.py` (9 failures)

**Root Cause**: `robots_txt_cache` table now requires `tenant_id` NOT NULL, but the robots cache is supposed to be global/shared. Tests try to insert with `tenant_id=None` or expect global access.

---

## 7. Model / API Signature Mismatches

**Impact**: ~15 tests
**Errors**:
- `TypeError: FastPathResult.__init__() got an unexpected keyword argument 'links'`
- `TypeError: Response.__init__() got an unexpected keyword argument 'xml'`
- `TypeError: 'url' is an invalid keyword argument for ScrapingJob`
- `TypeError: 'url' is an invalid keyword argument for RawContent`
- `AttributeError: 'HttpxCrawler' object has no attribute '_validate_public_url'`
- `TypeError: object RoutingDecision can't be used in 'await' expression`

**Affected Test Files**:
- `tests/benchmarks/test_router_performance.py` (3 failures)
- `tests/integration/test_fast_path_pipeline.py` (6 failures)
- `tests/crawler/test_httpx_crawler.py` (10 failures)
- `tests/integration/test_router_edge_cases.py` (4 failures)
- `tests/crawler/test_quality_gate.py` (2 failures)

**Root Cause**: Data models and internal APIs were refactored (e.g., `FastPathResult` no longer takes `links`, `Response` no longer takes `xml`, `ScrapingJob` no longer takes `url`, `RoutingDecision` is no longer awaitable, `_validate_public_url` was removed or renamed).

---

## 8. Async / Coroutine Issues

**Impact**: ~10 tests
**Errors**:
- `ValueError: a coroutine was expected, got None`
- `RuntimeWarning: coroutine '<func>' was never awaited`
- `TypeError: object RoutingDecision can't be used in 'await' expression`

**Affected Test Files**:
- `tests/security/test_global_robots_cache_isolation_postgres.py` (3 failures)
- `tests/unit/test_celery_tasks.py` (6 warnings/failures)
- `tests/integration/test_fast_path_pipeline.py`

**Root Cause**: Functions changed from async to sync (or vice versa) without test updates. `RoutingDecision` is now synchronous. `_get_cached_robots_txt` returns `None` instead of a coroutine.

---

## 9. Robots Checker / Compliance Logic Errors

**Impact**: ~5 tests
**Errors**:
- `AssertionError: assert '' == 'example.com'` (domain is empty)
- `httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol.`
- `AssertionError: assert 'parse error' in 'robots.txt fetch failed (strict mode): internal error'`

**Affected Test Files**:
- `tests/compliance/test_strict_robots_mode.py` (5 failures)

**Root Cause**: `robots_checker.py` passes an empty domain string when constructing the robots.txt URL, causing protocol errors. The error message for parse failures was changed from "parse error" to "internal error".

---

## 10. Event Outbox Logic Failures

**Impact**: ~6 tests
**Errors**:
- `AssertionError: assert 'failed' == 'dead_letter'`
- `AssertionError: assert 0 == 1` (attempts not incremented)
- `AssertionError: assert 'connection refused' in ''` (last_error is None)

**Affected Test Files**:
- `tests/unit/test_event_outbox.py` (6 failures)

**Root Cause**: Event outbox failure handling logic does not increment attempts, record error messages, or transition to `dead_letter` status as expected.

---

## 11. Miscellaneous Assertion & Logic Failures

**Impact**: ~15 tests
**Errors**:
- `AssertionError: assert 'PENDING' == 'VALIDATING'` (`test_compliance_check_stage_updates_job_status`)
- `AssertionError: assert 404 in {200, 401, 503}` (`test_standard_observability_probes_and_correlation_header`)
- `AssertionError: DB session must be entered`
- `AssertionError: Regex pattern did not match.`
- `AssertionError: Expected 'authorize_maintenance_operation' to be called once. Called 0 times.`
- `ValueError: badly formed hexadecimal UUID string`
- `AssertionError: Security error ... was caught by generic except`
- `AssertionError: assert 0 >= 1` (queue position)
- `NameError: name 'text' is not defined`

---

## 12. Test Infrastructure Warnings (Non-Fatal)

**Warnings**:
- Unknown pytest marks: `benchmark`, `requires_postgres`, `slow`
- SQLAlchemy 2.0 deprecation warnings (`Query.get()`, `on_event`)
- FastAPI deprecation warnings (`regex` → `pattern`)
- Pydantic V2 deprecation warnings (class-based `config`)
- `SAWarning: transaction already deassociated from connection`

---

## Root Cause Clustering

| Category | Count | Fix Strategy |
|----------|-------|--------------|
| DB Schema (`job_type` missing) | ~60 | Create/run migration OR remove column from model |
| DB Integrity (`created_by`) | ~20 | Update test fixtures to include `created_by` |
| Missing `tenant_id` in task calls | ~40 | Update all test callers to pass `tenant_id` |
| Broken imports / module paths | ~25 | Fix compatibility shims or update imports |
| Maintenance authorization | ~20 | Add proper mock tokens / auth context in tests |
| Model/API signature changes | ~25 | Update model instantiation and API usage in tests |
| Async/sync mismatches | ~10 | Add/remove `await` / `asyncio.run` as needed |
| Robots checker logic | ~5 | Fix domain extraction / error messages in source |
| Event outbox logic | ~6 | Fix outbox failure handling in source code |
| Misc assertions | ~15 | Fix individually |

---

## Recommended Fix Priority

### P0 — Block the Most Tests
1. **Fix `scraping_jobs.job_type` schema mismatch** — Running a migration or removing the field from the model will unblock ~60+ tests.
2. **Fix `created_by` NOT NULL** — Update the `ScrapingJob` / `ScrapingTarget` creation helpers in tests to provide `created_by`.

### P1 — Widespread Signature / Import Issues
3. **Update task signatures** — `storage_stage`, `notification_stage`, `validation_stage`, `dispatch_outbox_event` all need `tenant_id` passed in tests.
4. **Fix compatibility import shims** — `src.crawler`, `src.shared.database`, `shared.config` need to resolve correctly.

### P2 — Logic & Authorization
5. **Fix system maintenance auth mocking** — Tests need to provide a valid maintenance identity context.
6. **Fix `robots_txt_cache` tenant handling** — Decide if robots cache is global (allow NULL tenant) or per-tenant and adjust schema/tests.
7. **Fix robots checker domain extraction** — Empty domain causes URL protocol errors.

### P3 — Individual Test Fixes
8. Fix event outbox dead-letter / attempt logic.
9. Fix individual model signature mismatches (`FastPathResult`, `Response`, `RoutingDecision`).
10. Fix async/sync mismatches in `HttpxCrawler` and `PlaywrightCrawler` tests.

