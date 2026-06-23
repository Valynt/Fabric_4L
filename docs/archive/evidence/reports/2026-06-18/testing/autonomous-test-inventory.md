# Test Inventory

Generated: 2026-05-06

## Backend Tests

| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| layer1-ingestion | 0 | 0 | 0 | 0 |
| layer2-extraction | 0 | 0 | 0 | 0 |
| layer3-knowledge | 0 | 0 | 0 | 0 |
| layer4-agents | 0 | 0 | 0 | 0 |
| layer5-ground-truth | 3 | 0 | 1 | 0 |
| layer6-benchmarks | 2 | 0 | 0 | 0 |
| tests/ (root) | 60+ | 15+ | 10+ | 5+ |

**Backend Test Categories:**
- agents/ (2 tests)
- arch/ (3 tests)
- backend_integrated/ (13 tests)
- cache/ (1 test)
- chaos/ (4 tests)
- ci/ (4 tests)
- config/ (4 tests)
- contract/ (25 tests)
- contracts/ (8 tests)
- security/ (52 tests)
- integration/ (10 tests)
- k8s/ (12 tests)
- performance/ (10 tests)
- release/ (7 tests)

## Frontend Tests

| Category | Count | Framework |
|----------|-------|-----------|
| Unit/Component | 58 | Vitest |
| Integration | 58 | Playwright |
| E2E | 58 | Playwright |

**Frontend Test Files:**
- src/**/*.{test,spec}.{ts,tsx}: 58 files (hooks, lib, schemas, navigation, pages)
- e2e/**/*.spec.ts: 58 files (journeys, contracts, accessibility, admin)

## CI Gates

| Gate | Status | Command |
|------|--------|---------|
| test-mandatory.yml | Active | pytest -m mandatory |
| security-gates.yml | Active | pytest -m security |
| integration-tests.yml | Active | pytest -m integration |
| contract-compliance.yml | Active | pytest -m contract |
| pr-checks.yml | Active | Full test suite |
| test.yml | Active | Backend tests |
| security-gates-merged.yml | Active | Security regression |
| smoke-gate.yml | Active | Release smoke tests |

## Test Markers (pytest.ini)

- mandatory: Tests that must run and pass in CI (unit + contract + security)
- unit: Fast unit tests (no I/O, <100ms)
- integration: Integration tests with real dependencies
- e2e: End-to-end tests
- contract: API contract tests (OpenAPI schema validation)
- runtime_contract: Runtime cross-layer contract tests
- backend_integrated: Backend-integrated validation tests
- release_smoke: Minimal production-gate smoke checks
- performance: Performance benchmarks and SLO validation
- security: Security tests (OWASP Top 10)
- tenant_boundary: High-risk tenant boundary tests
- auth_boundaries: Authentication and authorization boundary regression tests
- auth_source: Authentication source validation regression tests
- cross_tenant_write: Cross-tenant write isolation regression tests
- jwt_config: JWT configuration safety regression tests
- rate_limit: Rate-limiting safety regression tests
- tenant_lifecycle: Tenant lifecycle security regression tests
- tenant_mismatch: Tenant mismatch and confused-deputy regression tests
- websocket: WebSocket authentication and authorization regression tests
- slow: Tests that take >1 second or require optional heavy deps
- flaky: Known flaky tests being fixed
- quarantine: Tests temporarily isolated due to external dependencies
- requires_postgres: Tests requiring a live PostgreSQL instance
- requires_redis: Tests requiring a live Redis instance
- requires_neo4j: Tests requiring a live Neo4j instance
- requires_docker: Tests requiring a running Docker daemon
- requires_openai: Tests requiring OpenAI API

## Discovery Notes

### Backend Architecture
- 7 service layers: layer1-ingestion, layer2-extraction, layer3-knowledge, layer4-agents, layer5-ground-truth, layer6-benchmarks, api
- Layer4-agents is the largest (348 items) - handles agent workflows, tools, tenant management
- Layer3-knowledge has extensive auth, security, rate limiting, and query validation
- Layer5-ground-truth has tenant_id consistency tests and RLS policy validation
- Layer6-benchmarks has public API routes (/datasets, /compare, /validate, /industries)

### Auth Patterns Discovered
- Registration endpoints in layer4-agents/src/tenants/api/routes/registration.py
- Email verification service with token-based verification
- Tenant provisioning workflow with status tracking
- Security middleware in layer6-benchmarks/src/shared_bootstrap.py
- Query validator in layer3-knowledge/src/security/query_validator.py with tenant scoping checks
- Rate limiting manager in layer3-knowledge/src/rate_limiting/manager.py

### Tenant Isolation
- tenant_id column usage in layer5-ground-truth models
- RLS policy validation in test_tenant_id_consistency.py
- Tenant context filtering in layer4-agents tools (knowledge_tools.py overrides tenant_id parameters)
- Organization ID to tenant ID migration tracked (migration 004, 006 for RLS fixes)

### API Routes
- Layer6-benchmarks: /health, /datasets, /datasets/{id}, /compare, /validate, /industries
- Layer4-agents: /tenants/register, /tenants/verify-email, /tenants/validate-slug, /tenants/tiers

### Frontend Test Structure
- 58 unit/integration tests using Vitest (jsdom environment)
- 58 E2E tests using Playwright with multiple projects:
  - contracts: Fast mocked tests
  - journeys: Chained workflow tests
  - backend-integrated: Tests requiring PLAYWRIGHT_BACKEND_URL
  - Cross-browser: Firefox, WebKit, Mobile Chrome, Mobile Safari
- Journey tests numbered j0-j22 covering full user workflows
- Deep validation tests for golden path, layer UI, tenant isolation, agent grounding, calculation evidence, approval review, export workflows

### Critical Gaps Identified
1. **Layer1-3**: No service-level test files discovered in services/layer1-3/tests/ directories
2. **Layer4**: No service-level test files discovered in services/layer4-agents/tests/
3. **Tenant isolation**: Limited adversarial tests for cross-tenant data access
4. **Auth boundaries**: Missing comprehensive negative tests for authentication bypass
5. **Input validation**: Limited tests for malformed input reaching persistence/LLM/tools
6. **Secrets protection**: No explicit tests for secrets exposure in logs/errors/responses
