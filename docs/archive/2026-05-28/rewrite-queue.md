# Test Rewrite Priority Queue

**Generated:** 2026-04-19
**Source:** `docs/testing/test-quality-audit.md`

---

## P0 - Critical (Fix Immediately)

### 1. L4 Checkpoint/Resume Import Fix
**File:** `services/layer4-agents/tests/conftest.py`
**Effort:** 30 min
**Impact:** Unblocks 12 failing tests

**Problem:** `sys.path.insert()` pattern causes import failures

**Solution:**
```python
# BEFORE (conftest.py lines 16-17)
if str(layer4_dir) not in sys.path:
    sys.path.insert(0, str(layer4_dir))

# AFTER - Use editable install approach
# In CI/pip install: pip install -e services/layer4-agents
# Remove manual path manipulation from conftest.py
```

---

### 2. L3 E2E Neo4j Edition Detection
**File:** `services/layer3-knowledge/tests/test_e2e_pipeline.py`
**Effort:** 1 hour
**Impact:** Fixes 6 failing tests

**Problem:** Tests require Neo4j Enterprise but testcontainers uses Community

**Solution:**
```python
# Add edition detection fixture
@pytest.fixture
async def neo4j_edition(neo4j_driver):
    async with neo4j_driver.session() as session:
        result = await session.run("CALL dbms.components() YIELD name, editions")
        record = await result.single()
        return "enterprise" if "enterprise" in record["editions"] else "community"

# Add skip decorator to enterprise-only tests
@pytest.mark.skipif(
    os.getenv("NEO4J_EDITION") != "enterprise",
    reason="Requires Neo4j Enterprise for property existence constraints"
)
```

---

### 3. L4 Test Isolation Fix
**File:** `services/layer4-agents/tests/conftest.py`
**Effort:** 30 min
**Impact:** Prevents cross-test contamination

**Problem:** Global sys.path modification affects all tests

**Solution:**
```python
# Remove lines 7-17 from conftest.py
# Instead, rely on:
# 1. Editable install (pip install -e .)
# 2. Or pytest's pythonpath in pyproject.toml

# Add to pyproject.toml:
[tool.pytest.ini_options]
pythonpath = ["src"]
```

---

## P1 - Material (Next 2 Sprints)

### 4. Weak Test Naming (L1)
**File:** `services/layer1-ingestion/tests/test_todo_placeholder_regressions.py`
**Effort:** 30 min

**Before:**
```python
def test_case_1(self): ...
def test_case_2(self): ...
```

**After:**
```python
def test_rejects_todo_placeholder_in_scraping_target_title(self): ...
def test_rejects_todo_placeholder_in_raw_content_body(self): ...
```

---

### 5. LLM Mock Migration (L2)
**File:** `services/layer2-extraction/tests/test_extraction.py`
**Effort:** 2 hours

**Problem:** 1 test skipped due to missing OPENAI_API_KEY

**Solution:** Use L4's `mock_openai_client` fixture pattern

---

### 6. Slow Test Markers (L1)
**File:** `services/layer1-ingestion/tests/test_playwright_crawler.py`
**Effort:** 30 min

**Solution:**
```python
@pytest.mark.slow  # For selective running
@pytest.mark.integration  # For CI filtering
async def test_real_browser_crawling(): ...
```

---

### 7. Deprecation Cleanup (L1)
**Files:** Multiple L1 test files
**Effort:** 1 hour

**Solution:**
```python
# BEFORE
from datetime import datetime
datetime.utcnow()

# AFTER
from datetime import datetime, UTC
datetime.now(UTC)
```

---

### 8. E2E CI Integration (Frontend)
**File:** `.github/workflows/pr-checks.yml`
**Effort:** 4 hours

**Solution:** Add E2E job step with Playwright

---

### 9. Implementation Coupling (L2)
**File:** `services/layer2-extraction/tests/test_llm_extractor.py`
**Effort:** 4 hours

**Problem:** Tests internal method calls

**Solution:** Test extracted entity output instead

---

### 10. Test Split (L4)
**File:** `services/layer4-agents/tests/test_langgraph_execution.py` (33,688 bytes)
**Effort:** 8 hours

**Solution:** Split into:
- `test_langgraph_basic_execution.py`
- `test_langgraph_checkpointing.py`
- `test_langgraph_error_handling.py`
- `test_langgraph_tool_integration.py`

---

## P2 - Improvements (Opportunistic)

11. **Mock Response Factories** - Extract `createMockResponse` pattern (frontend)
12. **Coverage Gates** - Add 80% minimum to CI
13. **Test Parallelization** - Add `pytest-xdist` to layers
14. **Property-Based Testing** - Add `hypothesis` for validation
15. **Contract Test Expansion** - Add more endpoint coverage

---

## Progress Tracking

| # | Task | Status | Assignee | Notes |
|---|------|--------|----------|-------|
| 1 | L4 Import Fix | ✅ COMPLETE | 2026-04-19 | Removed sys.path manipulation |
| 2 | L3 Neo4j Fix | ✅ VERIFIED | 2026-04-19 | Already implemented correctly |
| 3 | L4 Isolation | ✅ COMPLETE | 2026-04-19 | Fixed pythonpath in pyproject.toml |
| 4 | L1 Naming | 🔴 NOT STARTED | | |
| 5 | L2 LLM Mock | 🔴 NOT STARTED | | |
| 6 | Slow Markers | 🔴 NOT STARTED | | |
| 7 | Deprecation | 🔴 NOT STARTED | | |
| 8 | E2E CI | 🔴 NOT STARTED | | |
| 9 | L2 Coupling | 🔴 NOT STARTED | | |
| 10 | L4 Split | 🔴 NOT STARTED | | |

---

*Next: Execute P0 fixes for immediate CI stability*
