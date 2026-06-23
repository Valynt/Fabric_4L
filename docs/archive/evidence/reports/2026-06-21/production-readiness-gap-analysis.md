# Production-Readiness Gap Analysis

Generated for PR 1: Database and HTTPException Inventory

## Database Production-Readiness Gaps

### Layer 1 (Ingestion)

#### Critical Gaps
- **Engine disposal**: No explicit engine disposal implementation
- **Health check**: No health check implementation in database.py
- **Lifespan management**: Not integrated with FastAPI lifespan
- **PostgreSQL tests**: No explicit PostgreSQL integration tests

#### Medium Gaps
- **Pool timeout**: Not explicitly configured (uses SQLAlchemy defaults)
- **Pool recycle**: Not explicitly configured
- **DSN validation**: Basic URL parsing but no production safety checks
- **Metrics**: Metrics integration exists but pool state not tracked

#### Notes
- Uses sync SQLAlchemy (different from L4/L5 async pattern)
- Has statement timeout configuration (good for production)
- Pool configuration is explicit via environment variables (good)

### Layer 4 (Agents)

#### Critical Gaps
- **Engine disposal**: No explicit engine disposal implementation
- **Health check**: No health check implementation in database.py
- **Lifespan management**: Not integrated with FastAPI lifespan
- **PostgreSQL tests**: No explicit PostgreSQL integration tests

#### Medium Gaps
- **Pool timeout**: Not explicitly configured in settings
- **Pool recycle**: Not explicitly configured in settings
- **Metrics**: Pool state metrics tracked but may need verification

#### Strengths
- Production safety checks: `_assert_rls_safe_database_url()` validates scheme and username
- Async SQLAlchemy with asyncpg (modern pattern)
- Tenant enforcement via `TenantEnforcedAsyncSession`
- Comprehensive metrics tracking (pool state, wait time, timeouts, privileged sessions)
- Tenant validation metrics

### Layer 5 (Ground Truth)

#### Critical Gaps
- **Health check**: No health check implementation in database.py
- **Lifespan management**: Not integrated with FastAPI lifespan (manual call required)
- **PostgreSQL tests**: No explicit PostgreSQL integration tests

#### Medium Gaps
- **Engine disposal**: Function exists but requires manual call
- **Metrics**: Pool state metrics tracked but optional (may fail silently)

#### Strengths
- Production safety checks: `_assert_rls_safe_database_url()` validates scheme and username
- Async SQLAlchemy with asyncpg (modern pattern)
- Tenant enforcement via `TenantEnforcedAsyncSession`
- Comprehensive pool configuration (size, overflow, pre-ping, recycle, timeout)
- Engine disposal function exists
- SQLite UUID handling for test compatibility

### Layer 6 (Benchmarks)

#### Critical Gaps
- **DSN leakage**: Health check returns URI in response (security issue)
- **Production-readiness tests**: No Neo4j production-readiness tests

#### Medium Gaps
- **Health check**: Basic implementation but may need sanitization
- **Metrics**: No Prometheus metrics integration

#### Notes
- Uses Neo4j (not PostgreSQL) - different datastore
- Has retry logic with exponential backoff (good for production)
- Health check exists but needs DSN sanitization

## Error Handling Gaps

### Canonical Exception Usage

#### Current State
- 8 canonical exception classes defined in `packages/shared/src/value_fabric/shared/error_handling/exceptions.py`
- `register_exception_handlers` is called in most services
- ~200+ sites raise HTTPException directly instead of using canonical exceptions
- ErrorEnvelope contract exists but not consistently enforced

#### Gaps
- **Router/API boundary**: ~150+ sites use raw HTTPException
- **Database modules**: ~30 sites use raw HTTPException for tenant context errors
- **Internal logic**: ~15 sites use raw HTTPException for service errors
- **No CI gate**: No static check to prevent new raw HTTPException usage
- **No contract tests**: No tests verifying ErrorEnvelope rendering for canonical exceptions

### HTTPException Categorization Summary

#### High Priority (Router/API Boundary) - ~150 sites
- 401 Authentication: ~25 sites
- 403 Authorization: ~25 sites
- 404 Not Found: ~80 sites
- 400/422 Validation: ~40 sites
- 409 Conflict: ~15 sites
- 503 Service Unavailable: ~20 sites
- 500 Internal Server Error: ~15 sites
- 502/504 Gateway/Timeout: ~5 sites

#### Medium Priority (Database Module) - ~30 sites
- Layer 1 database.py: ~10 sites
- Layer 4 database.py: ~10 sites
- Layer 5 database.py: ~10 sites
- These handle tenant context, privileged access, isolation tier errors

#### Low Priority (Internal Logic) - ~15 sites
- Service layer code, tools, utilities
- Auth middleware, account authorization
- Tier enforcement

#### Excluded (Test Files) - ~50+ sites
- Intentional HTTPException usage for testing
- Should not be migrated

## Recommendations

### Database Standardization

#### Immediate (PR 4-5)
1. Add engine disposal to L4 (missing critical lifecycle management)
2. Add health check implementations to L1, L4, L5
3. Integrate lifespan management with FastAPI for all services
4. Sanitize L6 health check to remove DSN from response
5. Add explicit pool timeout configuration to L4

#### Post-Migration
1. Extract shared helpers for DSN validation (if patterns are similar)
2. Extract shared pool configuration model
3. Add PostgreSQL integration tests for L1, L4, L5
4. Add Neo4j production-readiness tests for L6

### Error Handling Migration

#### Immediate (PR 2-3)
1. Add ErrorEnvelope contract tests for all canonical exceptions
2. Create CI static check with baseline allowlist
3. Wire CI check into preflight workflow

#### Router Migration (PR 6)
1. Migrate 401 authentication errors first (highest visibility)
2. Migrate 403 authorization errors
3. Migrate 404 not found errors (largest category)
4. Migrate 400/422 validation errors
5. Migrate 409 conflict errors
6. Migrate 503 service unavailable errors
7. Migrate 500 internal server errors (last - may need different approach)

#### Database Module Migration (Separate PR)
1. Evaluate if database.py HTTPException sites should use canonical exceptions
2. May need different approach since these are infrastructure-level
3. Consider if these should remain as HTTPException for internal errors

#### Internal Logic Migration (Separate PR)
1. Migrate service layer HTTPException sites
2. Migrate auth middleware HTTPException sites
3. Migrate tool/utility HTTPException sites

## Risk Assessment

### High Risk
- **DSN leakage in L6 health check**: Security issue, should be fixed immediately
- **No engine disposal in L4**: Connection leak risk in production
- **No health checks**: Cannot monitor database health in production

### Medium Risk
- **No PostgreSQL integration tests**: Cannot verify production behavior
- **No CI gate for HTTPException**: New violations can be introduced
- **No ErrorEnvelope contract tests**: Cannot verify canonical exception behavior

### Low Risk
- **Pool configuration inconsistencies**: Can be addressed incrementally
- **Metrics gaps**: Nice to have but not blocking
- **Internal logic HTTPException**: Lower visibility, can be addressed later

## Success Criteria for PR 1

- [x] Database comparison matrix documents current state factually
- [x] HTTPException inventory categorizes all sites by type and priority
- [x] Gap analysis identifies production-readiness issues
- [x] Recommendations prioritize immediate vs post-migration work
- [x] Risk assessment highlights security and operational risks

## Next Steps (PR 2)

PR 1 is complete. Next step is PR 2: ErrorEnvelope Contract Tests
- Add contract tests for all 9 canonical exception classes
- Verify HTTP status code correctness
- Verify stable error code values
- Verify message shape and content
- Verify request ID presence
- Verify details shape
- Verify no raw exception leakage
- Verify no secrets/tokens/DSNs in response
