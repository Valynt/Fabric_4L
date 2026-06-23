# Test Quality Remediation Plan

**Date**: 2026-04-19
**Status**: Audit Complete, Remediation in Progress

---

## Summary

Completed comprehensive test quality audit of 4 critical test files:

| File | Status | Score | Action Required |
|------|--------|-------|-----------------|
| `test_extract_and_ingest_pipeline.py` | ✅ Passing | 32/35 | None - excellent example |
| `useGraphQuery.test.ts` | ✅ Passing | 28/35 | Strengthen error assertions |
| `test_e2e_pipeline.py` | ⚠️ Conditional | 24/35 | Fix Neo4j Community compatibility |
| `test_checkpoint_resume.py` | ❌ Failing | N/A | **Fix import paths** |

---

## Immediate Actions (P0)

### Fix L4 Checkpoint/Resume Test Collection

**Problem**: Tests fail during collection with `ModuleNotFoundError: No module named 'src'`

**Root Cause**: When running pytest from repo root, the path configuration needs adjustment.

**Solution Options**:

#### Option A: Update Root pytest.ini (Recommended)
Add layer4-agents src to pythonpath:

```ini
# pytest.ini
pythonpath =
    services/layer1-ingestion/src
    services/layer2-extraction/src
    services/layer3-knowledge/src
    services/layer4-agents/src  # <-- ADD THIS
    services/layer5-ground-truth/src
    services/layer6-benchmarks/src
    shared/
```

#### Option B: Fix conftest.py Path Insertion
Update `services/layer4-agents/tests/conftest.py`:

```python
# Add before any imports
import sys
from pathlib import Path

# Add layer4 src to path
_layer4_src = Path(__file__).parent.parent / "src"
if str(_layer4_src) not in sys.path:
    sys.path.insert(0, str(_layer4_src))
```

#### Option C: Run from Layer4 Directory
```bash
cd services/layer4-agents
pytest tests/test_checkpoint_resume.py
```

**Recommended**: Option A (root-level fix) ensures tests work from any directory.

---

## High Priority Actions (P1)

### 1. Fix L3 E2E Pipeline Tests

**Issues**:
- Enterprise-only Neo4j constraints fail on Community edition
- Logger misuse with structured kwargs

**Fixes**:

```python
# test_e2e_pipeline.py - Add edition detection
@pytest.fixture(scope="module")
async def neo4j_driver(neo4j_container):
    driver = AsyncGraphDatabase.driver(...)

    # Detect edition
    async with driver.session() as session:
        result = await session.run("CALL dbms.components() YIELD edition")
        record = await result.single()
        edition = record["edition"]

    yield driver

    # Skip enterprise-only tests on Community
    if edition == "community":
        pytest.skip("Enterprise-only test")
```

```python
# Fix logger calls
# Before:
logger.error("Failed", exception_type="Timeout", path="/api/v1/graph")

# After:
logger.error("Failed", extra={"exception_type": "Timeout", "path": "/api/v1/graph"})
```

### 2. Strengthen Frontend Error Assertions

**File**: `useGraphQuery.test.ts`

```typescript
// Before:
await waitFor(() => expect(result.current.isError).toBe(true));

// After:
await waitFor(() => {
  expect(result.current.isError).toBe(true);
  expect(result.current.error?.message).toMatch(/timeout|error/i);
});
```

---

## Medium Priority (P2)

### 1. Extract Shared Test Factories

Create `tests/factories.py`:

```python
"""Shared test data factories for Value Fabric tests."""

from layer2_extraction.models import Capability, UseCase, Relationship, ExtractionResult

def make_capability(name: str = "Test Capability", **overrides) -> Capability:
    return Capability(name=name, **overrides)

def make_use_case(name: str = "Test Use Case", **overrides) -> UseCase:
    return UseCase(name=name, **overrides)

def make_extraction_result(
    job_id: str = "test-job",
    source_url: str = "https://example.com",
    **overrides
) -> ExtractionResult:
    return ExtractionResult(
        job_id=job_id,
        source_url=source_url,
        capabilities=[make_capability()],
        use_cases=[make_use_case()],
        **overrides
    )
```

### 2. Split Frontend Hook Tests

Separate `useGraphQuery.test.ts` into:
- `useGraphQuery.test.ts` (GraphRAG mutation)
- `useEntityContext.test.ts` (neighborhood queries)
- `useEntityTraversal.test.ts` (value tree traversal)
- `useFullGraph.test.ts` (subgraph queries)

---

## Validation Commands

### Verify P0 Fix
```bash
# From repo root
pytest services/layer4-agents/tests/test_checkpoint_resume.py --collect-only

# Should output: collected 12 items
```

### Verify P1 Fixes
```bash
# L3 e2e with Neo4j Community
cd services/layer3-knowledge
pytest tests/test_e2e_pipeline.py -v --tb=short

# Frontend hooks
cd frontend
pnpm test useGraphQuery
```

### Full Regression
```bash
# Backend
pytest -m unit -n auto --timeout=60
pytest -m integration --timeout=120

# Frontend
cd frontend
pnpm test
pnpm test:e2e
```

---

## Success Criteria

- [ ] `test_checkpoint_resume.py` collects and passes
- [ ] `test_e2e_pipeline.py` skips enterprise tests on Community
- [ ] `useGraphQuery.test.ts` has strong error assertions
- [ ] All P0/P1 tests pass in CI
- [ ] No import errors during collection
- [ ] Test coverage maintained at ≥80%

---

## Appendix: Quality Principles Checklist

For future test reviews:

- [ ] **Behavior-Focused**: Tests contracts, not internals
- [ ] **Clear/Readable**: AAA structure, descriptive names
- [ ] **Focused**: One behavior per test
- [ ] **Deterministic**: No flaky timing or randomness
- [ ] **Isolated**: Fresh state per test, proper cleanup
- [ ] **Meaningful**: Catches regressions that matter
- [ ] **Maintainable**: Resilient to harmless refactors
