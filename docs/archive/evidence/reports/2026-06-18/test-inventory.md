# Test Inventory

Generated: 2026-05-27

## Backend Tests

| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| api | 25 | 5 | 15 | 0 |
| layer1-ingestion | 40+ | 5 | 10+ | 0 |
| layer2-extraction | 35+ | 8 | 5+ | 0 |
| layer2-5-signal-refinery | 5 | 2 | 2 | 0 |
| layer3-knowledge | 20+ | 5 | 5+ | 0 |
| layer4-agents | 30+ | 5 | 10+ | 0 |
| layer5-ground-truth | 15+ | 5 | 8+ | 0 |
| layer6-benchmarks | 10+ | 3 | 2 | 0 |
| layer7-billing | 5+ | 2 | 1 | 0 |

## Frontend Tests

| Category | Count | Framework |
|----------|-------|-----------|
| Unit/Component | 57 | Vitest |
| Integration | 58 | Vitest |
| E2E | 30+ | Playwright |
| Contract Tests | 19 | Vitest |

## CI Gates

| Gate | Status | Command |
|------|--------|---------|
| pr-checks | Active | .github/workflows/pr-checks.yml |
| contract-compliance | Active | .github/workflows/contract-compliance.yml |
| security-gates | Active | .github/workflows/security-gates.yml |
| test-mandatory | Active | .github/workflows/test-mandatory.yml |
| backend-integrated-reproducibility | Active | .github/workflows/backend-integrated-reproducibility.yml |

## Discovery Notes

### Auth & Boundary Patterns
- **Authentication**: `require_authenticated` dependency found in layer4-agents
- **Tenant Context**: Tenant ID propagation via AsyncSession with `set_config('app.tenant_id')` in layer7-billing
- **RLS Policies**: Row-level security policies referenced in layer5-ground-truth migrations
- **Session Management**: AsyncSession patterns with tenant context throughout layers

### Database Patterns
- **Session Factory**: `create_session_maker` pattern in layer7-billing
- **Tenant Context**: `db_session_for_context(tenant_id)` sets PostgreSQL config
- **RLS Enforcement**: Migration 006 fixes RLS policies after org_id → tenant_id rename

### Test Frameworks
- **Backend**: pytest with markers (@pytest.mark.asyncio, @pytest.mark.release)
- **Frontend**: Vitest for unit/integration, Playwright for E2E
- **Coverage**: pytest-cov configured for all backend layers

### Security Test Coverage
- **Tenant Isolation**: Tests in layer1-ingestion, layer2-extraction, layer4-agents
- **Auth Enforcement**: Tests in api layer (test_auth_enforcement, test_jwks_and_token_validation)
- **Rate Limiting**: test_tenant_rate_limiting.py at root
- **Production Safety**: test_production_safety.py in api layer

### Critical Gaps Identified
1. **layer7-billing**: Minimal test coverage (5+ tests) for billing/metering critical path
2. **Cross-layer integration**: Limited tests for L1→L2 Celery dispatch (recently added)
3. **Adversarial testing**: Some hostile case tests exist but coverage uneven across layers
4. **E2E backend**: No backend-integrated E2E tests (only frontend Playwright)
