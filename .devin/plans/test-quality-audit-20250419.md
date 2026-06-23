# Test Quality Audit - Discovery Output

**Date**: 2026-04-19
**Repository**: Fabric_4L (Value Fabric)

---

## 1. Repository Testing Map

### 1.1 Backend Layers (Python/pytest)

| Layer | Test Files | Framework | Coverage Tool | Notes |
|-------|-----------|-----------|---------------|-------|
| layer1-ingestion | 4+ | pytest | pytest-cov | Redis/PostgreSQL tests |
| layer2-extraction | 7+ | pytest | pytest-cov | Extraction pipeline tests |
| layer3-knowledge | 4+ | pytest | pytest-cov | Neo4j graph tests |
| layer4-agents | 7+ | pytest | pytest-cov | Agent orchestration tests |
| layer5-ground-truth | 7+ | pytest | pytest-cov | State machine tests |
| layer6-benchmarks | 7+ | pytest | pytest-cov | Performance benchmarks |
| shared/ | 0 | - | - | Cross-cutting utilities |
| packs/*/ | 21 | pytest | - | Domain pack tests |
| sdk/python | 5 | pytest | - | SDK client tests |
| tests/ (cross-layer) | 20+ | pytest | - | Contract, integration, security |

**Total Python Test Files**: ~85

### 1.2 Frontend (TypeScript/Vitest/Playwright)

| Category | Test Files | Framework | Notes |
|----------|-----------|-----------|-------|
| Unit Tests (client) | 33 | Vitest | React hooks, components, utils |
| E2E Tests | 16 | Playwright | Full user flows |

**Total TypeScript Test Files**: ~49

### 1.3 Test Markers (pytest)

- `@pytest.mark.unit` - Fast unit tests (<100ms)
- `@pytest.mark.integration` - Integration tests with real deps
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.contract` - OpenAPI schema validation
- `@pytest.mark.performance` - Benchmarks
- `@pytest.mark.security` - OWASP tests
- `@pytest.mark.slow` - >1 second tests
- `@pytest.mark.flaky` - Known flaky (skip in CI)

### 1.4 CI Integration

| Workflow | Purpose |
|----------|---------|
| `test.yml` | Main test suite (unit, integration, contract, security) |
| `integration-tests.yml` | Additional integration coverage |
| `performance-load-tests.yml` | Performance gates |
| `pr-checks.yml` | Pre-merge validation |

### 1.5 Coverage Requirements

- **Minimum**: 80% (enforced via `--cov-fail-under=80`)
- **Reporting**: term-missing, HTML, XML (for Codecov)

---

## 2. Known Gaps

### 2.1 Critical Path Coverage
- [ ] Layer 4 checkpoint/resume tests (failing - ModuleNotFoundError)
- [ ] L3 Neo4j Community compatibility (enterprise-only constraints failing)
- [ ] Frontend API contract alignment (graph/entity routes drift)

### 2.2 Missing Test Types
- [ ] Chaos/tenant isolation tests (exist but not integrated)
- [ ] Accessibility automated tests (Axe, needs expansion)

### 2.3 Infrastructure
- [ ] No shared test utilities module (per user preference - local helpers only)
- [ ] Deterministic clock fixtures needed in multiple layers

---

## 3. Priority Areas for Audit

Based on roadmap critical path and runtime evidence:

### P0 - Critical
1. **L2 extract-and-ingest pipeline tests** (`tests/test_extract_and_ingest_pipeline.py`)
   - Status: Need validation
2. **L4 checkpoint/resume tests**
   - Status: Failing during collection (import errors)
3. **L3 e2e pipeline tests**
   - Status: Failing on Neo4j Community edition

### P1 - Material
4. Contract tests (L2-L3, L3-L4 interfaces)
5. Frontend API hook tests (useGraphQuery, useFormulas, etc.)
6. Security tests (OWASP Top 10)

### P2 - Improvement
7. Pack integrity tests (duplication across 7 packs)
8. SDK client tests
9. Architecture tests (tenant isolation, testability)

---

## Next Steps

Proceed to **Phase 2: Audit** - evaluate specific test files against quality principles.

Target files for immediate audit:
1. `tests/test_extract_and_ingest_pipeline.py` (L2-L3 orchestration)
2. `services/layer4-agents/tests/test_checkpoints.py` (failing)
3. `services/layer3-knowledge/tests/test_e2e_pipeline.py` (failing)
4. `frontend/client/src/hooks/useGraphQuery.test.ts` (API contract)
