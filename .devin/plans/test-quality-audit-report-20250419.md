# Test Quality Audit Report

**Date**: 2026-04-19
**Auditor**: Test Quality Remediation Workflow
**Scope**: Critical path tests (L2-L3 orchestration, L4 checkpoint/resume, L3 e2e, Frontend API hooks)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Test Files Audited | 4 |
| P0 Issues Found | 1 |
| P1 Issues Found | 4 |
| P2 Issues Found | 3 |
| Tests Needing Rewrite | 2 |
| Tests Passing | 1 |
| Tests Failing | 2 |

**Critical Finding**: L4 checkpoint/resume tests fail during collection due to `ModuleNotFoundError` importing 'src'. This blocks reliable releases.

---

## File-by-File Assessment

### 1. `test_extract_and_ingest_pipeline.py` (L2-L3 Orchestration)

**Status**: ✅ Well-structured, passing
**Lines**: 548 | **Tests**: 6 | **Score**: 32/35

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 5 | Tests API contract and cross-layer integration |
| Clear/Readable | 5 | Excellent naming: `test_l3_unavailable_queues_retry_and_persists` |
| Focused | 5 | Each test verifies one behavior (kickoff, retry, success) |
| Deterministic | 5 | FrozenClock ensures deterministic timing |
| Isolated | 5 | FakePendingIngestionStore, Layer3 doubles, autouse fixture |
| Meaningful | 4 | Covers happy path, retry, failure, cross-layer contract |
| Maintainable | 3 | Some duplication in artifact building (extractable to factory) |

**Strengths**:
- Excellent use of test doubles (FakePendingIngestionStore, FrozenClock, Layer3ClientDouble)
- Clear AAA structure in all tests
- Comprehensive docstrings explaining cross-layer contract
- Proper use of `monkeypatch` for dependency injection

**Minor Issues (P2)**:
- `build_artifacts()` helper could be extracted to shared factory
- Some duplication in fake extraction setup between tests

**Action**: Leave as-is. Excellent example for other test files.

---

### 2. `test_checkpoint_resume.py` (L4 Agents)

**Status**: ❌ Failing during collection
**Lines**: 339 | **Tests**: 12 | **Score**: N/A (cannot run)

**Critical Issue (P0)**:
```python
from src.config.checkpoint import CheckpointConfig  # ModuleNotFoundError
```

**Root Cause**: Import path issue. Tests use `src.` prefix but pytest `pythonpath` may not include the correct source directory structure.

**Impact**:
- Blocks CI reliability
- Prevents validation of checkpoint/resume functionality
- Risk of regressions in human-in-the-loop workflows

**Recommended Actions**:
1. Fix import paths to use layer-specific package structure
2. Add `conftest.py` with proper path configuration
3. Verify pytest `pythonpath` in `pyproject.toml`

**Pattern Fix**:
```python
# Before (broken)
from src.config.checkpoint import CheckpointConfig

# After (correct)
from layer4_agents.config.checkpoint import CheckpointConfig
```

---

### 3. `test_e2e_pipeline.py` (L3 Knowledge)

**Status**: ⚠️ Conditional skip, enterprise constraints failing
**Lines**: 828 | **Tests**: 8+ | **Score**: 24/35

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests full pipeline flow |
| Clear/Readable | 3 | Large file, complex setup |
| Focused | 3 | Multiple concerns (schema, ingest, query) |
| Deterministic | 3 | Testcontainers provides determinism |
| Isolated | 3 | Uses real Neo4j container |
| Meaningful | 4 | Covers critical e2e path |
| Maintainable | 3 | Tight coupling to Neo4j enterprise features |

**P1 Issues**:
1. **Enterprise-only constraints**: Tests fail on Neo4j Community edition
   - Property existence constraints are enterprise-only
   - Need conditional constraint creation

2. **Large test file**: 828 lines suggests mixed concerns
   - Schema initialization
   - Data ingestion
   - GraphRAG queries
   - Hybrid search

**P2 Issues**:
3. **Logger misuse**: `logger.error()` with structured kwargs causes TypeError
   ```python
   # Wrong
   logger.error("msg", exception_type="X", path="Y")

   # Correct
   logger.error("msg", extra={"exception_type": "X", "path": "Y"})
   ```

**Recommended Actions**:
1. Add Neo4j edition detection and skip enterprise-only tests on Community
2. Split into focused test modules
3. Fix logger calls

---

### 4. `useGraphQuery.test.ts` (Frontend Hooks)

**Status**: ✅ Well-structured, likely passing
**Lines**: 214 | **Tests**: 13 | **Score**: 28/35

| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | 4 | Tests hook behavior (fetch, cache, error) |
| Clear/Readable | 4 | Good naming: `executes graph query successfully` |
| Focused | 4 | Each describe block covers one hook |
| Deterministic | 4 | MSW mocks ensure determinism |
| Isolated | 4 | Server reset between tests |
| Meaningful | 4 | Covers success, error, caching, null handling |
| Maintainable | 4 | Uses `createWrapper()` helper, factories |

**Strengths**:
- Proper use of React Testing Library patterns
- MSW for API mocking
- `createMockNode()` factory function
- Tests error handling and edge cases (null entityId)

**P1 Issue**:
1. **Weak assertion in error test**: Only checks `isError`, not error message
   ```typescript
   // Current
   await waitFor(() => expect(result.current.isError).toBe(true));

   // Improved
   await waitFor(() => {
     expect(result.current.isError).toBe(true);
     expect(result.current.error?.message).toContain('timeout');
   });
   ```

**P2 Issues**:
2. **Test description typos**: `executes` vs `should execute`
3. **Mixed hook testing**: File tests 4 different hooks (could split)

**Recommended Actions**:
1. Strengthen error assertions
2. Consider splitting into `useGraphQuery.test.ts`, `useEntityContext.test.ts`, etc.

---

## Categorized Issues Summary

### P0 - Critical (Fix Immediately)
| Issue | File | Action |
|-------|------|--------|
| Import error blocking collection | `test_checkpoint_resume.py` | Fix import paths to use `layer4_agents.` prefix |

### P1 - Material (Fix This Sprint)
| Issue | File | Action |
|-------|------|--------|
| Enterprise-only Neo4j constraints | `test_e2e_pipeline.py` | Add edition detection, skip on Community |
| Logger.error misuse | `test_e2e_pipeline.py` | Use `extra=` dict for structured logging |
| Weak error assertions | `useGraphQuery.test.ts` | Assert on error message/content |
| File too large (mixed concerns) | `test_e2e_pipeline.py` | Split into focused modules |

### P2 - Improvement (Nice to Have)
| Issue | File | Action |
|-------|------|--------|
| Artifact building duplication | `test_extract_and_ingest_pipeline.py` | Extract to shared factory |
| Test naming convention | `useGraphQuery.test.ts` | Use `should_` prefix consistently |
| Multiple hooks in one file | `useGraphQuery.test.ts` | Split into separate files |

---

## Rewrite Priority Queue

### Immediate (P0)
1. **Rewrite**: `test_checkpoint_resume.py` - Fix imports, verify collection

### This Sprint (P1)
2. **Rewrite**: `test_e2e_pipeline.py` - Split and fix Neo4j Community compatibility
3. **Strengthen**: `useGraphQuery.test.ts` - Add error message assertions
4. **Audit**: Other L4 agent tests for similar import issues

### Next Sprint (P2)
5. **Refactor**: Extract common factories from `test_extract_and_ingest_pipeline.py`
6. **Split**: Frontend hook tests into focused files
7. **Add**: Missing edge case coverage for retry scenarios

---

## Recommendations

### Immediate Actions
1. **Fix L4 imports**: Update `test_checkpoint_resume.py` to use `layer4_agents.` prefix
2. **Verify CI**: Run `pytest services/layer4-agents/tests/test_checkpoint_resume.py --collect-only`

### Architectural Improvements
1. **Test Helpers**: Create `tests/factories.py` for shared test data builders
2. **Neo4j Compatibility**: Add edition detection fixture for L3 tests
3. **Import Standards**: Document layer-specific import conventions

### Process Improvements
1. **Pre-commit**: Add import path validation hook
2. **CI**: Run collection-only check before full test suite
3. **Documentation**: Add test quality guidelines to `CONTRIBUTING.md`

---

## Appendix: Test Quality Scores

| File | Score | Grade | Status |
|------|-------|-------|--------|
| `test_extract_and_ingest_pipeline.py` | 32/35 | A | ✅ Passing |
| `useGraphQuery.test.ts` | 28/35 | B+ | ✅ Likely passing |
| `test_e2e_pipeline.py` | 24/35 | C+ | ⚠️ Conditional skip |
| `test_checkpoint_resume.py` | N/A | F | ❌ Failing collection |

**Grade Scale**: A (30-35), B (25-29), C (20-24), D (15-19), F (<15)
