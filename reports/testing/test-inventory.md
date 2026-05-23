# Test Inventory

Generated: 2026-05-04 (Autonomous Test Assurance Agent — Phase 1 Complete)
Updated: 2026-05-05 (Sprint 1 Remediation - Layer-Specific Invariants)
Updated: 2026-05-23 (Phase 2 Invariant Extraction - Current Session)
Collection Status: **4623 tests collected, 0 collection errors**

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| layer1-ingestion | 12 test files | 3 test files | 2 test files + layer1_security_invariants.py | N/A |
| layer2-extraction | 4 test files | 2 test files | 1 test file + layer2_security_invariants.py (NEW) | N/A |
| layer3-knowledge | 14 test files | 4 test files | 3 test files + layer3_security_invariants.py (NEW) | N/A |
| layer4-agents | 28+ test files | 5 test files | 8 test files + layer4_security_invariants.py | N/A |
| layer5-ground-truth | 3 test files | 1 test file | 1 test file | N/A |
| layer6-benchmarks | 2 test files | N/A | layer6_security_invariants.py (NEW) | N/A |
| tests/ (shared) | ~40 test files | 10 test files | 52 test files + 5 P0 security tests | 3 test files |
| packages/shared | 16 test files | Contract tests | Security tests | MCP gateway tests |
| packs (7 packs) | 21 test files | Formula/ontology tests | Pack integrity | N/A |
| sdk/python | 7 test files | Integration tests | N/A | N/A |
| services/api | 10 test files | Auth/governance tests | Production safety | N/A |

**New Tests Added (Phase 4 - P0 Critical Gaps):**
- layer4-agents: test_tool_output_structure_validation.py (34 tests)
- layer4-agents: test_tool_execution_contract.py (19 tests)
- layer4-agents: test_agent_output_traceability.py (30 tests)
- layer4-agents: test_agent_workflow_traceability.py (18 tests)
- **Total New Tests: 101 tests across 4 files**

## Frontend Tests
| Category | Count | Framework |
|----------|-------|-----------|
| Unit/Component | 51 .test.ts files | Vitest |
| Integration | Contract tests (12 files) | Vitest |
| E2E | 57 .spec.ts files | Playwright |
| Deep Validation | 7 -deep.spec.ts files | Playwright (Phase 2 complete) |

## CI Gates
| Gate | Status | Command |
|------|--------|---------|
| pytest mandatory | Configured | pytest -m mandatory |
| playwright e2e | Configured | pnpm run test:e2e |
| playwright deep validation | Configured | pnpm run test:e2e:validation:deep |
| security gates | Configured | .github/workflows/security-gates.yml |
| contract compliance | Configured | .github/workflows/contract-compliance.yml |
| test-mandatory | Configured | .github/workflows/test-mandatory.yml |

## Discovery Notes
- **Repository uses 6-layer architecture** (layer1-ingestion through layer6-benchmarks)
- **Frontend uses React + Vite + Playwright** for E2E
- **Backend uses pytest** with extensive marker system (mandatory, unit, integration, e2e, contract, security, tenant_boundary, auth_boundaries, cross_tenant_write, etc.)
- **Auth pattern**: GovernanceMiddleware with JWT/API-key/X-Service-Auth resolution; FastAPI Depends with role/permission checks
- **Database**: AsyncSession with RLS enforcement via `SET LOCAL app.tenant_id`
- **OpenAPI specs** available in contracts/openapi/ for layer1, layer2, layer3
- **Migrations found** in all 6 services
- **RLS policies** enforced via SET LOCAL app.tenant_id in layer4-agents and layer5-ground-truth
- **Phase 2 E2E validation milestone complete**: 78 interaction-level tests across P0 production-gate suites
- **Collection errors fixed in this session**:
  1. `pytest_plugins` in non-top-level conftest (tests/layer1, tests/layer4)
  2. `pdf2image` missing in test_pdf_adapter.py
  3. `protego` missing in test_pii_scanner.py
  4. `playwright` missing in test_playwright_crawler.py
  5. `global_exception_handler` import path in test_exception_handlers.py
  6. `_extract_tenant_id` import path in test_tenant_context_extraction.py
  7. `_extract_tenant_id` import path in test_tenant_isolation.py
  8. `pytest_plugins` double-registration conflict in tests/conftest.py
  9. `redis` / `psutil` missing in services/layer3-knowledge/tests/conftest.py
  10. `MagicMock(spec=Request)` falsy issue in test_tenant_isolation.py
  11. `async with` mock fix for mock_neo4j_driver in test_tenant_isolation.py
  12. `opentelemetry` / `psycopg2` / `asyncpg` / `jinja2` / `botocore` / `langgraph.checkpoint.postgres` missing across layer1/2/4 conftests
  13. Import file mismatch across services fixed with `--import-mode=importlib`
  14. Idempotent opentelemetry stub strategy across conftests to prevent partial-stub conflicts

## Production Invariants (Phase 2 Extraction)

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes
- **Enforcement**: RLS policies with `SET LOCAL app.tenant_id`, middleware validation
- **Code Path**: `tests/security/test_cross_layer_tenant_isolation_matrix.py`, `tests/security/test_cross_tenant_write.py`
- **Test Coverage**: 96 security test files in tests/security/, cross-layer matrix tests

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: GovernanceMiddleware, JWT/API-key/X-Service-Auth resolution
- **Code Path**: `services/layer4-agents/src/api/governance.py`, `services/layer6-benchmarks/src/api/deps.py`
- **Secret Requirements**: JWT_SECRET, API_KEY_HMAC_SECRET, SERVICE_AUTH_SECRET min 32 chars
- **Dev Bypass Control**: ALLOW_INSECURE_DEV_AUTH_BYPASS must be false in production

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: Role checks, permission validators, RequestContext immutability
- **Code Path**: `tests/security/test_auth_boundaries.py`, `tests/security/test_permission_bypass.py`

### Input Validation
- **Rule**: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic schema validation with Field validators
- **Code Path**: All services use Pydantic BaseModel with Field() constraints
- **Test Coverage**: `tests/security/test_input_validation.py`

### Rate Limiting
- **Rule**: Rate limiting keyed by tenant_id + endpoint_pattern + identity_hash
- **Enforcement**: RedisRateLimiter with fallback local limiter
- **Code Path**: `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py`, `tests/security/test_rate_limit_*.py`
- **Production Requirement**: REDIS_RATE_LIMITING_REQUIRED=true in production

### Tool Output Structure
- **Rule**: Tools must return canonical ToolResult shape with status/data/error/metadata
- **Enforcement**: BaseTool.execute() contract, registry validation
- **Code Path**: `services/layer4-agents/src/tools/registry.py`
- **Contract**: status: "success"|"error"|"partial", error.code/message/recoverable, metadata.execution_time_ms/tenant_id/trace_id

### CORS Security
- **Rule**: CORS origins must be explicitly configured, no wildcard in production
- **Enforcement**: CORS_ORIGINS env var validation, reject "*" in production
- **Code Path**: `services/layer4-agents/tests/test_security_fixes.py`, `services/layer5-ground-truth/tests/test_production_fail_closed_i02.py`

### Database Session Isolation
- **Rule**: All tenant-scoped DB access must use get_db_from_context(), not get_db()
- **Enforcement**: CI lint flags Depends(get_db) in production routes
- **Code Path**: `services/layer5-ground-truth/tests/test_router_db_dependencies.py`
- **RLS Pattern**: `SET LOCAL app.tenant_id = :tenant_id` at transaction start

### Error Response Shape
- **Rule**: All errors follow canonical shape with code/message/recoverable
- **Enforcement**: HTTPException normalization, error boundary middleware
- **Code Path**: Middleware stack in docs/contract.md §2.3

### Agent Output Traceability
- **Rule**: All agent outputs include trace_id, session_id, model_version, token_usage
- **Enforcement**: Pydantic schema validation, OpenTelemetry spans
- **Code Path**: docs/contract.md §2.5

## Gap Analysis (Phase 3)

### Critical Gaps (P0 - Immediate Action Required)

#### 1. Tool Output Structure Validation
- **Invariant**: Tools must return canonical ToolResult shape
- **Current Coverage**: Limited - found only 5 tool-related tests in layer4-agents
- **Gap**: No comprehensive tests for:
  - ToolResult.status field validation (success/error/partial)
  - ToolResult.error.code/message/recoverable structure
  - ToolResult.metadata.execution_time_ms/tenant_id/trace_id presence
  - Negative tests: tools throwing exceptions instead of structured errors
- **Priority**: HIGH - Contract violation risk
- **Estimated Effort**: 2-3 test files

#### 2. Agent Output Traceability
- **Invariant**: All agent outputs include trace_id, session_id, model_version, token_usage
- **Current Coverage**: NONE - no tests found for agent traceability
- **Gap**: No tests for:
  - Agent output Pydantic schema validation
  - Trace_id/session_id propagation through workflows
  - Model version pinning validation
  - Token usage metadata presence
  - OpenTelemetry span emission for agent operations
- **Priority**: HIGH - Observability gap
- **Estimated Effort**: 3-4 test files

#### 3. Negative/Adversarial Test Pairs
- **Invariant**: Every important invariant needs positive + negative test
- **Current Coverage**: Partial - some invariants have only positive tests
- **Gap**: Missing negative tests for:
  - Tool output malformed structure rejection
  - Agent output missing required fields
  - RequestContext immutability violations
  - Middleware phase bypass attempts
- **Priority**: MEDIUM - Completeness gap
- **Estimated Effort**: 5-6 test files

### Moderate Gaps (P1 - Next Sprint)

#### 4. Rate Limiting Edge Cases
- **Invariant**: Rate limiting keyed by tenant_id + endpoint_pattern + identity_hash
- **Current Coverage**: Found rate_limit test files but need edge case coverage
- **Gap**: Missing tests for:
  - Rate limit key collision scenarios
  - Burst vs sustained rate limit behavior
  - Redis unavailability fallback behavior
  - Cross-tenant rate limit isolation
- **Priority**: MEDIUM
- **Estimated Effort**: 2-3 test files

#### 5. Database Session Isolation Enforcement
- **Invariant**: All tenant-scoped DB access must use get_db_from_context()
- **Current Coverage**: Found test_router_db_dependencies.py
- **Gap**: Missing tests for:
  - Direct get_db() usage detection in new routes
  - SET LOCAL app.tenant_id execution verification
  - Transaction rollback clears tenant context
  - Background task tenant context propagation
- **Priority**: MEDIUM
- **Estimated Effort**: 2-3 test files

### Low Priority Gaps (P2 - Backlog)

#### 6. Error Response Shape Consistency
- **Invariant**: All errors follow canonical shape with code/message/recoverable
- **Current Coverage**: Partial - some error tests exist
- **Gap**: Missing comprehensive tests for:
  - All HTTPException paths across layers
  - Error boundary middleware behavior
  - Error shape validation for all error codes
- **Priority**: LOW
- **Estimated Effort**: 3-4 test files

### Coverage Summary

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Status |
|-----------|----------------|----------------|-------------------|--------|
| Tenant Isolation | ✅ Extensive | ✅ Extensive | ✅ Extensive | **COVERED** |
| Authentication | ✅ Extensive | ✅ Extensive | ✅ Extensive | **COVERED** |
| Authorization | ✅ Good | ✅ Good | ⚠️ Partial | **NEEDS WORK** |
| Input Validation | ✅ Good | ✅ Good | ⚠️ Partial | **NEEDS WORK** |
| Rate Limiting | ✅ Good | ⚠️ Limited | ❌ Missing | **NEEDS WORK** |
| Tool Output Structure | ⚠️ Limited | ❌ Missing | ❌ Missing | **CRITICAL GAP** |
| CORS Security | ✅ Good | ✅ Good | ✅ Good | **COVERED** |
| Database Session Isolation | ⚠️ Limited | ❌ Missing | ❌ Missing | **NEEDS WORK** |
| Error Response Shape | ⚠️ Partial | ❌ Missing | ❌ Missing | **NEEDS WORK** |
| Agent Output Traceability | ❌ Missing | ❌ Missing | ❌ Missing | **CRITICAL GAP** |

### Remediation Priority Order

1. **P0-CRITICAL**: Tool Output Structure Validation (2-3 test files)
2. **P0-CRITICAL**: Agent Output Traceability (3-4 test files)
3. **P1-MEDIUM**: Negative/Adversarial Test Pairs (5-6 test files)
4. **P1-MEDIUM**: Rate Limiting Edge Cases (2-3 test files)
5. **P1-MEDIUM**: Database Session Isolation Enforcement (2-3 test files)
6. **P2-LOW**: Error Response Shape Consistency (3-4 test files)

**Total Estimated Effort**: 17-23 test files
