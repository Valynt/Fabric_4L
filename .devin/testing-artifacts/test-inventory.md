# Test Inventory - Autonomous Test Assurance Agent

**Last Updated:** 2026-04-28
**Inspector:** Level 3 Test Assurance Agent

## Backend Tests (Actual Counts)

| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests | Notes |
|-------|-----------|-------------------|----------------|-----------|-------|
| Layer 1 (Ingestion) | 16 | 2 | 0 | 0 | `tests/unit/`, `tests/integration/`, `tests/crawler/` |
| Layer 2 (Extraction) | 7 | 0 | 0 | 0 | `tests/test_*.py` |
| Layer 3 (Knowledge) | 18 | 0 | 0 | 0 | `tests/test_*.py` (includes tenant isolation tests) |
| Layer 4 (Agents) | ~35 | ~5 | 0 | 0 | `tests/test_*.py` |
| Layer 5 (Ground Truth) | ~10 | ~3 | 0 | 0 | Limited test coverage observed |
| Layer 6 (Benchmarks) | ~5 | ~2 | 0 | 0 | Minimal test files |
| Shared | ~15 | ~10 | 0 | 0 | `shared/identity/tests/`, `shared/*/tests/` |
| **tests/ (root)** | 63 | 15+ | **27** | 5 | Primary security test suite |

## Frontend Tests
| Category | Count | Framework | Location |
|----------|-------|-----------|----------|
| Unit/Component | ~25 | Vitest | `frontend/client/src/**/*.test.ts` |
| Integration | ~15 | Vitest + MSW | `frontend/client/src/test/` |
| E2E | ~8 | Playwright | `tests/e2e/` |

## CI Gates
| Gate | Status | Command | Workflow File |
|------|--------|---------|---------------|
| Unit Tests | ⚠️ | `pytest` | `test.yml` |
| Integration Tests | ⚠️ | `pytest -m integration` | `integration-tests.yml` |
| Security Smoke | ⚠️ | `pytest tests/security/` | `security-gates.yml` |
| Contract Tests | ⚠️ | `pytest tests/contract/` | `contract-compliance.yml` |
| E2E | ⚠️ | `pnpm e2e` | `pr-checks.yml` |

## Security Test Inventory (tests/security/)

| File | Test Count | Coverage Area |
|------|-----------|---------------|
| `test_adversarial_auth.py` | 20 | Malformed auth headers, JWT attacks |
| `test_tenant_isolation.py` | 13 | Cross-tenant access prevention |
| `test_rls_enforcement.py` | 12 | DB RLS policy enforcement |
| `test_rbac.py` | 18 | Role-based access control |
| `test_owasp_top10.py` | 19 | OWASP top 10 vulnerabilities |
| `test_owasp_top10_complete.py` | 45 | Extended OWASP coverage |
| `test_cross_layer_tenant.py` | 16 | Cross-layer tenant isolation |
| `test_cross_tenant_api.py` | 14 | API-level tenant boundaries |
| `test_secrets_protection.py` | 11 | Secret exposure prevention |
| `test_input_validation.py` | 9 | Input sanitization |
| `test_security_headers.py` | 6 | Security headers enforcement |
| `test_security_misconfiguration.py` | 16 | Config security checks |
| `test_injection.py` | 8 | SQL/injection attacks |
| `test_oidc.py` | 27 | OIDC authentication |
| `test_supply_chain.py` | 15 | Supply chain security |
| `test_tenant_audit.py` | 9 | Tenant audit logging |
| `test_privileged_audit.py` | 17 | Privileged operation auditing |
| Other files | ~35 | Various security areas |

## Test Skip/Skipif Analysis
- 113 skip markers found across test files
- Many integration tests use `@pytest.mark.skipif` for optional dependencies
- Database-dependent tests skip when DB unavailable (local dev)

## Critical Gaps Identified

1. **No RLS SQL migration files found** - RLS policies may be in Python code only
2. **WebSocket auth untested** - `layer4-agents/src/api/websocket/routes.py` lacks negative tests
3. **Skipped tests need audit** - 113 skips need review for CI completeness
4. **Integration test coverage** - Many layers lack true integration tests
