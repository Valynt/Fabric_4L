# Test Quality Discovery Report 2025-04-19

## Repository Testing Landscape

### Frameworks by Location

| Location | Framework | Test Command | Coverage Tool |
|----------|-----------|--------------|---------------|
| Root (`/tests/`) | pytest | `pytest tests/` | pytest-cov (80% min) |
| `services/layer1-ingestion/` | pytest | `pytest` | pytest-cov |
| `services/layer2-extraction/` | pytest | `pytest` | pytest-cov |
| `services/layer3-knowledge/` | pytest | `pytest` | pytest-cov |
| `services/layer4-agents/` | pytest | `pytest` | pytest-cov |
| `services/layer5-ground-truth/` | pytest | `pytest` | pytest-cov |
| `services/layer6-benchmarks/` | pytest | `pytest` | pytest-cov |
| `frontend/` | Vitest + Playwright | `pnpm test` / `pnpm test:e2e` | @vitest/coverage-v8 |
| `sdk/python/` | pytest | `pytest` | pytest-cov |
| `packs/*/` | pytest | `pytest` | Not configured |

### Test File Counts

| Category | Count | Location Pattern |
|----------|-------|------------------|
| Python test files | 61 | `test_*.py` |
| TypeScript unit tests | 33 | `*.test.ts` / `*.test.tsx` |
| E2E spec files | 16 | `e2e/*.spec.ts` |
| **Total** | **110** | |

### Coverage Configuration

**Backend (pytest.ini)**:
- Minimum coverage: 80%
- Reports: terminal, HTML, XML
- Parallel execution: `-n auto`
- Timeout: 60 seconds per test

**Frontend (vitest.config.ts)**:
- Coverage via @vitest/coverage-v8
- E2E via Playwright with accessibility audits

### CI Integration

GitHub Actions workflows in `.github/workflows/`:
- `ai-evals-pipeline.yml` - AI evaluation tests
- `contract-tests.yml` - OpenAPI contract validation
- `drift-detection.yml` - API drift detection
- `integration-tests.yml` - Integration test suite
- `unit-tests.yml` - Unit test execution

### Test Categories (pytest markers)

- `unit` - Fast tests (<100ms, no I/O)
- `integration` - Tests with real dependencies
- `contract` - OpenAPI schema validation
- `e2e` - End-to-end tests
- `performance` - Benchmarks
- `security` - Security tests
- `accessibility` - WCAG compliance
- `slow` - Tests > 1 second
- `flaky` - Known flaky tests
- `requires_postgres/redis/neo4j/openai` - Dependency-specific

### Known Gaps

1. **Pack Tests**: 6 packs × 3 tests each = 18 tests, but minimal coverage configuration
2. **SDK Tests**: Python SDK has tests but may need more coverage
3. **Contract Tests**: Recently added path alignment tests - need audit
4. **Frontend Hook Tests**: 20+ hook tests - quality varies

### Immediate Focus Areas

Based on recent drift assessment work:
1. `tests/contract/test_l4_frontend_contract.py` - Path alignment tests (newly added)
2. `tests/contract/test_l3_graph_contract.py` - Graph API contracts
3. Frontend hook tests for graph/formula features

---

## Audit Plan

### Phase 2 Target Files

| Priority | File | Reason |
|----------|------|--------|
| P1 | `tests/contract/test_l4_frontend_contract.py` | Newly added, needs quality validation |
| P1 | `tests/contract/test_l3_graph_contract.py` | Critical path for Graph Explorer |
| P1 | `tests/contract/test_l3_formulas_contract.py` | Formula governance feature |
| P2 | `frontend/client/src/hooks/useGraphQuery.test.ts` | Frontend graph functionality |
| P2 | `frontend/client/src/hooks/useFormulas.test.ts` | Formula management |
