# Test Assurance Inventory

## Repository Test Landscape

### Backend Tests (Python/pytest)

| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests | Total Active | Quarantined |
|-------|-----------|-------------------|----------------|-----------|--------------|-------------|
| Layer 1 (Ingestion) | ~20 | ~15 | ~10 | - | ~45 | - |
| Layer 2 (Extraction) | ~25 | ~20 | ~15 | - | ~60 | - |
| Layer 3 (Knowledge) | ~30 | ~25 | ~20 | - | ~75 | ~200 |
| Layer 4 (Agents) | ~35 | ~30 | ~25 | - | ~90 | - |
| Layer 5 (Ground Truth) | ~20 | ~15 | ~10 | - | ~45 | - |
| Shared | ~15 | ~10 | ~15 | - | ~40 | - |
| Tests/ (Cross-layer) | ~50 | ~40 | ~476 | ~20 | ~586 | ~170 |

**Total Active Python Tests:** ~851
**Quarantined Tests:** ~170 (8 files, cannot collect)

### Frontend Tests (TypeScript/Vitest/Playwright)

| Category | Count | Framework | Status |
|----------|-------|-----------|--------|
| Unit/Component | ~150 | Vitest | Active |
| Integration | ~100 | Vitest + MSW | Active |
| E2E | ~45 | Playwright | Active |

**Total Frontend Tests:** ~295

## Security Test Inventory (tests/security/)

### Active Tests (476 tests across 25 files)

| File | Tests | Coverage Area |
|------|-------|---------------|
| `test_owasp_top10_complete.py` | 45 | OWASP Top 10 comprehensive |
| `test_oidc.py` | 27 | OIDC authentication flows |
| `test_shared_security_middleware.py` | 24 | Middleware security checks |
| `test_owasp_top10.py` | 19 | Core OWASP tests |
| `test_rbac.py` | 18 | Role-based access control |
| `test_privileged_audit.py` | 17 | Privileged operation auditing |
| `test_security_misconfiguration.py` | 16 | Security misconfiguration detection |
| `test_cross_layer_tenant.py` | 16 | Cross-layer tenant isolation |
| `test_cross_tenant_api.py` | 14 | Cross-tenant API access |
| `test_security_smoke.py` | 14 | Security smoke tests |
| `test_tenant_isolation.py` | 13 | Tenant data isolation |
| `test_rls_enforcement.py` | 12 | Row-level security enforcement |
| `test_export_tenant_access.py` | 11 | Export access controls |
| `test_tenant_context_contract.py` | 10 | Tenant context validation |
| `test_tenant_audit.py` | 9 | Tenant audit logging |
| `test_injection.py` | 8 | Injection attack prevention |
| `test_security_headers.py` | 6 | Security headers |
| `test_neo4j_tenant_query_enforcement.py` | 5 | Neo4j tenant query validation |

### Quarantined Tests (170+ tests across 8 files)

| File | Tests | Issue |
|------|-------|-------|
| `test_jwt_security.py` | 40+ | Imports non-existent `_DEFAULT_JWT_SECRET` |
| `test_oidc_pkce.py` | 30+ | Relative import chain breaks |
| `test_api_key_security.py` | 35+ | Imports non-existent `value_fabric` package |
| `test_middleware_security.py` | 30+ | Imports non-existent `_build_context_from_role` |
| `test_rbac_permissions.py` | 35+ | Imports non-existent `get_current_context` |
| `test_auth_integration.py` | 20+ | Imports non-existent `value_fabric` package |

**Impact:** These tests appear to provide coverage but **cannot collect/run**, creating false confidence.

## CI Gates

| Gate | Status | Command | Coverage |
|------|--------|---------|----------|
| Unit | ✅ Active | `pytest tests/unit` | ~200 tests |
| Integration | ✅ Active | `pytest tests/integration` | ~100 tests |
| Security | ✅ Active | `pytest tests/security` | 476 tests |
| Contract | ✅ Active | `pytest tests/contract` | ~40 tests |
| E2E Smoke | ✅ Active | `playwright test` | ~45 tests |
| Quarantine Check | ❌ MISSING | - | Would catch broken imports |

## Critical Findings

### P0: Broken Test Coverage (False Confidence)
**Issue:** 8 test files (~170 tests) in `_quarantine/` cannot collect due to import errors
**Risk:** Team believes these areas are tested, but zero actual coverage
**Evidence:** `tests/security/_quarantine/README.md`

### P1: Missing Negative Test Patterns
**Issue:** Security tests exist but may lack adversarial coverage
**Risk:** Only happy paths verified, attack vectors not blocked
**Evidence:** Review needed of existing test assertions

### P1: Quarantine Reconciliation Missing
**Issue:** No process to fix or delete quarantined tests
**Risk:** Technical debt grows, coverage remains fake
**Evidence:** Tests have been quarantined without resolution plan

## Test Infrastructure Quality

### Strengths
- ✅ Comprehensive `conftest.py` with deterministic fixtures
- ✅ JWT token fixtures (valid, expired, malformed)
- ✅ Tenant A/B fixtures for isolation testing
- ✅ Infrastructure check fixtures (postgres, redis, neo4j)

### Gaps
- ❌ No quarantine monitoring gate
- ❌ No test collection verification in CI
- ❌ Quarantined tests not tracked with expiration dates

## Next Actions

1. **Fix quarantined tests** - Rewrite against actual API or delete
2. **Add collection verification gate** - CI step to ensure all tests collect
3. **Review active security tests** - Verify negative/adversarial coverage
4. **Document test debt** - Track quarantine items with expiration
