# PostgreSQL Helper Extraction Analysis

Generated for PR 4: PostgreSQL Helper Extraction (Low-Risk Only)

## Executive Summary

After analyzing the database implementations across L1, L4, and L5, the recommendation is **to skip helper extraction** for the following reasons:

1. **Canonical contract already exists**: `packages/platform-contract/src/python/canonical/database.py` already provides the core tenant validation and context setting functions
2. **Service-specific safety checks**: L4 and L5 have additional production safety checks (`_assert_rls_safe_database_url`) that are not in the canonical contract
3. **Divergent patterns**: L1 uses sync SQLAlchemy while L4/L5 use async, making shared helpers complex
4. **User guidance**: The user explicitly rejected premature consolidation and prefers service-specific lifecycle management

## Similar Patterns Identified

### L4 and L5 - Nearly Identical Implementations

The following functions are nearly identical between L4 and L5:

#### 1. RLS Safety Check
- **L4**: `_assert_rls_safe_database_url()` (lines 220-236)
- **L5**: `_assert_rls_safe_database_url()` (similar implementation)
- **Purpose**: Validates PostgreSQL URL scheme and username in production environments
- **Schemes validated**: `postgresql+asyncpg://`, `postgresql://`, `postgres://`, `postgresql+psycopg://`
- **Superuser names blocked**: `postgres`, `admin`, `root`, `superuser`

#### 2. Tenant Context Marking
- **L4**: `_mark_session_tenant_context()`, `_mark_session_tenant_bypass()` (lines 244-253)
- **L5**: `_mark_session_tenant_context()`, `_mark_session_tenant_bypass()` (similar)
- **Purpose**: Marks session.info with tenant context state for enforcement

#### 3. Tenant Context Assertion
- **L4**: `_assert_session_has_tenant_context()` (lines 256-262)
- **L5**: `_assert_session_has_tenant_context()` (lines 195-201)
- **Purpose**: Fails closed if SQL executes before tenant context is set

#### 4. TenantEnforcedAsyncSession
- **L4**: `TenantEnforcedAsyncSession` class (lines 265-282)
- **L5**: `TenantEnforcedAsyncSession` class (lines 204-219)
- **Purpose**: AsyncSession wrapper that blocks SQL execution before tenant context
- **Behavior**: Nearly identical, both track pool timeout metrics

#### 5. Statement Detection
- **L4**: `_statement_sets_tenant_context()` (lines 239-241)
- **L5**: `_statement_sets_tenant_context()` (similar)
- **Purpose**: Detects if a statement sets tenant context (to allow RLS statements)

#### 6. Pool State Tracking
- **L4**: `_record_pool_state()` (lines 340-358)
- **L5**: `_record_pool_state()` (similar)
- **Purpose**: Tracks pool size, active connections, idle connections for metrics

### L1 - Different Pattern

L1 uses sync SQLAlchemy and has a different pattern:
- Sync engine with psycopg2
- Different tenant context validation
- Statement timeout configuration (not in L4/L5)
- No `TenantEnforcedAsyncSession` (sync pattern)

## Canonical Contract Analysis

The canonical contract at `packages/platform-contract/src/python/canonical/database.py` provides:

### Already Available
- `validate_tenant_id()` - Validates tenant_id format (UUID or reserved keyword)
- `set_tenant_context()` - Sets `SET LOCAL app.tenant_id` on session
- `TenantEnforcedAsyncSession` concept via `_LifecycleManagedSession`
- Lifecycle-managed sessions that block manual commit/rollback

### Not in Canonical Contract
- `_assert_rls_safe_database_url()` - Production safety check for URL scheme/username
- Pool state tracking metrics
- Pool timeout metrics
- Pool wait time metrics
- Privileged session metrics
- SQLite UUID handling (L5-specific)

## Recommendation: Skip Extraction

### Rationale

1. **Canonical contract covers core functionality**: The essential tenant validation and context setting already exists in the canonical contract. Services could adopt these if they want to reduce duplication.

2. **Service-specific safety checks are valuable**: The `_assert_rls_safe_database_url()` check is a production safety feature that should remain service-specific until we have a shared production safety policy.

3. **Metrics integration is service-specific**: Pool state tracking, timeout metrics, and wait time metrics are tied to each service's monitoring setup. Extracting these would require a shared metrics infrastructure.

4. **Sync/async divergence**: L1 uses sync SQLAlchemy while L4/L5 use async. Shared helpers would need to support both patterns, adding complexity.

5. **User guidance**: The user explicitly rejected premature consolidation and prefers service-specific lifecycle management.

### Alternative Approach

Instead of extracting shared helpers, recommend:

1. **Adopt canonical contract where applicable**: Services could use `canonical.database.validate_tenant_id()` and `canonical.database.set_tenant_context()` instead of their own implementations.

2. **Document the similarity**: This analysis document serves as evidence that L4 and L5 have nearly identical implementations, which can inform future consolidation if needed.

3. **Focus on production-readiness gaps**: PR 5 should focus on adding missing engine disposal, health checks, and lifespan management rather than helper extraction.

## Production-Readiness Gaps (Priority for PR 5)

Based on the inventory, the following gaps should be addressed in PR 5:

### Critical
- **L4**: Add engine disposal function (missing)
- **L1**: Add engine disposal function (missing)
- **L1**: Add health check implementation (missing)
- **L4**: Add health check implementation (missing)
- **L5**: Add health check implementation (missing)
- **L6**: Sanitize health check to remove DSN from response (security issue)

### Medium
- **L4**: Add explicit pool timeout configuration
- **L1**: Integrate lifespan management with FastAPI
- **L4**: Integrate lifespan management with FastAPI
- **L5**: Integrate lifespan management with FastAPI (function exists but not wired)

### Low
- Add PostgreSQL integration tests for L1, L4, L5
- Add Neo4j production-readiness tests for L6

## Conclusion

PR 4 should be **skipped**. The canonical contract already provides the core functionality, and the service-specific implementations have valuable production safety checks and metrics integration that should remain service-specific. The focus should shift to PR 5: addressing production-readiness gaps.
