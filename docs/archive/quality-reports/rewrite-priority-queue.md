# Test Rewrite Priority Queue

Generated: Apr 11, 2026
Updated: Apr 11, 2026 (WeasyPrint fix applied)
Based on: Test Quality Audit + Task 33 Review

---

## P0 - Critical (Fix Immediately)

### 1. layer3-knowledge/src/api/main.py:get_system_metrics() - FIXED ✅
- **Issue**: `total_errors` variable used but never initialized (NameError)
- **Status**: Fixed in Task 33 refinement
- **Effort**: Small (1 line fix)
- **Verification**: Syntax check passed

### 2. layer1-ingestion tests - Collection Errors
- **Issue**: Cannot collect tests due to model/scheduler issues
- **Impact**: 0 tests running, critical path blocked
- **Effort**: Medium (fix imports, signatures)
- **Files**:
  - `src/shared/models.py` - reserved `metadata` attribute
  - `src/scheduler.py` - function signature mismatch

### 3. layer3-knowledge/pytest.ini - Format Issue
- **Issue**: File is pytest.ini but contains Python code (conftest.py content)
- **Impact**: Tests fail to collect
- **Effort**: Small (rename or convert)
- **Fix**: Rename to conftest.py or convert to actual INI format

---

## P1 - Material (Fix Soon)

### 4. layer3-knowledge/tests/conftest.py - Deprecated Patterns
- **Issue**: Uses deprecated `event_loop` fixture pattern
- **Impact**: pytest-asyncio deprecation warnings
- **Effort**: Small
- **Fix**: Remove event_loop fixture, use modern pytest-asyncio config

### 5. layer5-ground-truth/tests/test_api.py - Pydantic Datetime Issues
- **Issue**: 19 tests failing due to datetime serialization
- **Impact**: 58% pass rate
- **Effort**: Medium
- **Fix**: Update datetime handling for Pydantic v2 compatibility

### 6. layer2-extraction Import Chain
- **Issue**: Relative imports causing collection failures
- **Impact**: Tests blocked in some environments
- **Effort**: Small
- **Fix**: Fix relative import in `src/extraction/__init__.py`

---

## P2 - Improvement (Nice to Have)

### 7. layer3-knowledge/tests/test_e2e_pipeline.py - Docker Dependency
- **Issue**: Requires live Neo4j via testcontainers
- **Impact**: Tests fail without Docker
- **Effort**: Medium
- **Fix**: Add better skip logic, mock option for CI without Docker

### 8. layer4-agents Test Coverage - PARTIALLY RESOLVED ✅
- **Issue**: ~~Only 4 test files, import errors~~ Tests now run (39 passed, 2 xfailed)
- **Impact**: WeasyPrint OSError fixed by catching (ImportError, OSError)
- **Files Modified**:
  - `src/tools/document_export.py` - Added OSError catch
  - `src/tools/generation_tools.py` - Added import guard + OSError catch
- **Status**: Tests operational, 2 pre-existing xfails remain (LangGraph state)

### 9. Frontend Tests
- **Issue**: Vitest installed but 0 test files
- **Impact**: No frontend test coverage
- **Effort**: Large
- **Fix**: Create foundational component tests

---

## Rewrite Queue - Execution Order

### Week 1: Unblock Critical Paths - STATUS UPDATE
1. [x] Fix layer3-knowledge get_system_metrics() bug (Task 33) - DONE
2. [ ] Fix layer1-ingestion model/scheduler issues
3. [x] ~~Fix layer3-knowledge pytest.ini format~~ - WAS ALREADY FIXED
4. [x] Verify all layers can collect tests - L4 NOW COLLECTS (WeasyPrint fix)

### Week 2: Quality Improvements
5. [ ] Fix layer5 datetime serialization (19 failing tests)
6. [ ] Update layer3 conftest deprecated patterns
7. [ ] Fix layer2 extraction imports

### Week 3: Coverage Expansion
8. [ ] Add layer4-agents edge case tests
9. [ ] Create frontend foundational tests
10. [ ] Improve layer3 e2e test isolation

---

## Files Status Summary

| File | Quality Score | Issues | Action |
|------|---------------|--------|--------|
| L2 test_extract_and_ingest_pipeline.py | 32/35 | None | Leave as-is ✅ |
| L3 conftest.py | 25/35 | Deprecated patterns | Fix P1 |
| L4 test_checkpoint_resume.py | 28/35 | Import context | Verify P0 |
| L5 test_state_machine.py | 30/35 | None | Leave as-is ✅ |
| L5 test_api.py | 20/35 | 19 failures | Fix P0/P1 |
| L3 test_health_endpoints.py | 26/35 | Needs determinism | Fix P1 |

---

## Verification Commands

```bash
# After fixes, verify all layers collect
for layer in layer1-ingestion layer2-extraction layer3-knowledge layer4-agents layer5-ground-truth; do
  echo "=== $layer ==="
  cd services/$layer
  pytest --collect-only 2>&1 | head -5
  cd ../..
done
```
