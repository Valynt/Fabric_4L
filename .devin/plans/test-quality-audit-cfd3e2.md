# Test Quality Audit Report

## Discovery Summary

### Repository Testing Landscape

| Category | Framework | Test Files | Estimated Test Count |
|----------|-----------|------------|---------------------|
| **Backend Python** | pytest | 60+ files | 1,140+ test functions |
| **Frontend TypeScript** | Vitest | 41 files | ~300 tests |
| **E2E Tests** | Playwright | 15+ spec files | ~100 scenarios |
| **Contract Tests** | pytest + httpx | 15 files | ~150 tests |
| **Security Tests** | pytest | 20+ files | ~200 tests |
| **Value Packs** | pytest | 21 files | ~60 tests |

### Test Configuration

**Python (pytest)**:
- Root config: `pytest.ini` with markers for unit, integration, e2e, contract, performance, security
- Parallel execution: `-n auto` (pytest-xdist)
- Test timeout: 60 seconds
- Quarantine directory for flaky/external-dep tests
- Environment variables for test DB/Redis/Neo4j

**Frontend (Vitest)**:
- Config in `frontend/package.json`
- MSW for API mocking
- React Testing Library for component tests
- Coverage via `--coverage` flag

---

## Phase 2: Audit Findings

### Files Evaluated

#### 1. `tests/config/test_startup_validation.py` (Lines 1-465)

**Overview**:
- Test count: 22
- Well-structured with clear AAA pattern
- Good docstrings explaining rationale
- Proper isolation using `patch.dict(os.environ, ...)`

**Principle Scores**:
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests production security controls, not implementation |
| Clear/Readable | 5 | Excellent naming, clear docstrings |
| Focused | 5 | Each test validates one specific control |
| Deterministic | 5 | Uses mocks, no timing dependencies |
| Isolated | 4 | Good use of `patch.dict` but imports inside test functions |
| Meaningful | 5 | Critical security controls validated |
| Maintainable | 4 | Minor coupling to specific error messages |
| **Total** | **33/35** | Excellent quality |

**Issues**: None - This is a model test file

---

#### 2. `tests/contract/test_layer3_contract.py` (Lines 1-292)

**Overview**:
- Test count: 15
- Contract tests for Layer 3 Knowledge API
- Uses JSON schema validation

**Principle Scores**:
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests API contracts (good) |
| Clear/Readable | 3 | Names like `test_entity_traverse_endpoint_exists` could be clearer |
| Focused | 4 | Mostly focused but some tests check multiple status codes |
| Deterministic | 3 | Depends on external API availability |
| Isolated | 3 | Uses real HTTP client, no clear mocking strategy |
| Meaningful | 4 | Contract validation is important |
| Maintainable | 3 | Hardcoded status code lists may need updates |
| **Total** | **24/35** | Good, could improve isolation |

**Issues Found**:
- **P1**: Tests require running Layer 3 API (no mocking)
- **P1**: Import failure: `ModuleNotFoundError: No module named 'httpx'`
- **P2**: Weak test names don't describe expected behavior clearly

---

#### 3. `tests/security/test_owasp_top10.py` (Lines 1-489)

**Overview**:
- Security tests for OWASP Top 10
- Tests IDOR, path traversal, JWT validation

**Principle Scores**:
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests security behaviors |
| Clear/Readable | 4 | Good class names, clear test names |
| Focused | 4 | Generally focused |
| Deterministic | 4 | Uses `if create_response.status_code == 201` - conditional assertion |
| Isolated | 3 | Uses real TestClient, state may leak |
| Meaningful | 5 | Security tests are critical |
| Maintainable | 4 | UUID pattern is documented |
| **Total** | **29/35** | Good quality |

**Issues Found**:
- **P1**: Conditional assertions (`if response.status_code == 201`) - tests may pass silently
- **P2**: Uses real client, could use mocks for better isolation

---

#### 4. `frontend/client/src/hooks/useFormulas.test.ts` (Lines 1-267)

**Overview**:
- React hook tests using Vitest
- Tests formula CRUD operations

**Principle Scores**:
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests hook behavior |
| Clear/Readable | 4 | Good test names like `fetches all formulas` |
| Focused | 3 | `applies status filter` checks multiple formulas |
| Deterministic | 5 | MSW provides consistent mocks |
| Isolated | 5 | `beforeEach(() => server.resetHandlers())` |
| Meaningful | 4 | Covers main use cases |
| Maintainable | 4 | Well-structured |
| **Total** | **29/35** | Good quality |

**Issues Found**:
- **P2**: Test `applies status filter` could be more focused
- **P2**: Uses `result.current.data?.forEach` - could fail silently if data undefined

---

#### 5. `frontend/client/src/hooks/useGraphQuery.test.ts` (Lines 1-223)

**Overview**:
- Graph query hook tests
- Uses MSW for API mocking

**Principle Scores**:
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests hook behavior |
| Clear/Readable | 4 | Good structure |
| Focused | 4 | Generally focused |
| Deterministic | 5 | MSW mocks |
| Isolated | 5 | `beforeEach(() => server.resetHandlers())` |
| Meaningful | 4 | Covers main use cases |
| Maintainable | 5 | Uses factory function `createMockNode` |
| **Total** | **31/35** | Very good |

**Issues Found**: None significant

---

### Summary by Severity

| Severity | Count | Issue Types |
|----------|-------|-------------|
| **P0** | 0 | No critical issues found in sampled tests |
| **P1** | 4 | Missing dependencies, external service coupling, conditional assertions |
| **P2** | 4 | Weak naming, test focus, minor readability |

---

## Phase 3: Prioritized Rewrite Queue

### P0 - Critical (None found in sample)

### P1 - Material (Priority Order)

1. **[CONTRACT-1]** Fix `tests/contract/conftest.py` - Add `httpx` dependency
   - **Effort**: Small (< 5 min)
   - **Impact**: Unblocks all contract tests

2. **[CONTRACT-2]** Improve contract test isolation - Add mocking strategy
   - **Files**: `tests/contract/test_layer3_contract.py`, `tests/contract/test_layer4_contract.py`
   - **Effort**: Medium (30-60 min)
   - **Impact**: Tests can run without running services

3. **[SECURITY-1]** Fix conditional assertions in OWASP tests
   - **File**: `tests/security/test_owasp_top10.py`
   - **Effort**: Small (15 min)
   - **Impact**: Tests fail explicitly instead of passing silently

4. **[HOOK-1]** Improve filter test in useFormulas
   - **File**: `frontend/client/src/hooks/useFormulas.test.ts`
   - **Effort**: Small (10 min)
   - **Impact**: Clearer test intent

### P2 - Improvement (Opportunistic)

5. **[NAMING]** Improve test names across contract tests
6. **[FACTORY]** Extract more factory functions in frontend tests
7. **[COVERAGE]** Add edge case tests for empty/null inputs

---

## Phase 4: Rewrite Execution Plan

### Immediate Actions (Next 30 min)

#### 1. Add Missing Dependency
```bash
# Add httpx to test dependencies
echo "httpx>=0.27.0" >> tests/requirements.txt
```

#### 2. Fix Conditional Assertions (SECURITY-1)

**Current** (test_owasp_top10.py:40-53):
```python
if create_response.status_code == 201:
    entity = create_response.json()
    entity_id = entity.get("id")
    # ... test continues conditionally
```

**Rewrite**:
```python
assert create_response.status_code == 201, "Entity creation failed - cannot test IDOR"
entity = create_response.json()
entity_id = entity.get("id")
assert entity_id, "Entity ID not returned"
# ... test continues unconditionally
```

#### 3. Improve Contract Test Isolation (CONTRACT-2)

Add `tests/contract/conftest.py` improvements:
```python
@pytest.fixture
def mock_client() -> AsyncClient:
    """Mock HTTP client for contract tests."""
    # Use respx or aioresponses to mock httpx
    pass
```

---

## Phase 5: Validation Plan

### Run Tests After Rewrites

```bash
# Contract tests
cd tests/contract
python -m pytest test_layer3_contract.py -v

# Security tests
cd tests/security
python -m pytest test_owasp_top10.py -v

# Frontend tests
cd frontend
pnpm test --run

# Full suite
pytest tests/ -v --tb=short
```

### Verify Improvements

- [ ] Contract tests pass without running services
- [ ] Security tests fail explicitly on errors
- [ ] Frontend tests maintain 100% pass rate
- [ ] No new warnings or deprecations

---

## Appendix: Testing Map

### Python Test Locations

```
tests/
├── arch/                    # Architecture tests
├── cache/                   # Redis/cache tests
├── config/                  # Startup validation (EXCELLENT)
├── context/                 # Tenant context
├── contract/                # API contracts (NEEDS HTTPX)
├── contracts/               # Duplicate dir - merge?
├── e2e/                     # End-to-end
├── evals/                   # Evaluations
├── gitops/                  # GitOps tests
├── integration/             # Integration tests
├── k8s/                     # Kubernetes tests
├── performance/             # Performance tests
├── security/                # Security tests (GOOD)
└── tools/                   # Tool tests

services/
├── layer1-ingestion/tests/
├── layer2-extraction/tests/
├── layer3-knowledge/tests/
├── layer4-agents/tests/
├── layer5-ground-truth/tests/
└── layer6-benchmarks/tests/

packs/
├── */tests/test_formula_execution.py
├── */tests/test_ontology_relationships.py
└── */tests/test_pack_integrity.py
```

### Frontend Test Locations

```
frontend/client/src/
├── api/*.test.ts
├── components/*.test.tsx
├── hooks/*.test.ts
├── pages/*.test.tsx
├── stores/*.test.ts
└── services/*.test.ts

frontend/e2e/
├── *.spec.ts
└── fixtures/
```

### CI Integration

- `.github/workflows/test.yml` - Main test runner
- `.github/workflows/integration-tests.yml` - Integration tests
- `.github/workflows/contract-compliance.yml` - Contract validation
- `.github/workflows/security-gates.yml` - Security tests

---

## Recommendations

### High Priority
1. Fix missing `httpx` dependency for contract tests
2. Standardize on single `contracts/` directory (remove duplicate)
3. Add contract test mocking to enable CI execution

### Medium Priority
4. Add factory functions for consistent test data
5. Improve test naming across contract tests
6. Extract common setup patterns

### Low Priority
7. Add mutation testing to validate test effectiveness
8. Consider property-based testing for complex validation logic
