# Audit: Remaining Known Issues

## Summary
Audit of three remaining issues from Slice A implementation: L4 LangGraph test failures, Task 76 (LLM Cost Metrics), and Task 79 (OpenAPI Contracts).

---

## Issue 1: L4 LangGraph Test Failures

### Current Status: PARTIALLY RESOLVED

**Previous State:** 3 failing tests
- `test_execute_workflow_creates_metadata` - TypeError: cancel_workflow() got unexpected `reason` kwarg
- `test_business_case_rejects_empty_sections` - DID NOT RAISE expected exception
- `test_get_workflow_status_after_execute` - Assert None is not None

**Current State:**
- `cancel_workflow()` signature already includes `reason: str | None = None` parameter at line 469
- Test may be using outdated mock or the controller class under test is different

**Files to Examine:**
- `services/layer4-agents/src/engine/executor.py:469` - cancel_workflow method
- `services/layer4-agents/tests/test_langgraph_execution.py` - failing tests

**Root Cause:** Test likely mocks `cancel_workflow` without `reason` parameter or uses different controller class.

---

## Issue 2: Task 76 - LLM Cost Prometheus Metrics

### Current Status: PARTIALLY IMPLEMENTED

**What's Already Done:**
- ✅ `PrometheusMetrics` class exists in `layer2-extraction/src/metrics/prometheus_metrics.py`
- ✅ `vf_llm_cost_usd_total` Gauge metric defined at line 153
- ✅ `vf_llm_tokens_total` Counter metric defined
- ✅ `record_llm_cost()` method implemented at line 234
- ✅ `record_llm_tokens()` method implemented
- ✅ LLM client imports and calls `get_prometheus_metrics()` at line 458

**What's Missing:**
- ❌ `vf_llm_tokens_total` Counter not being incremented in LLM client
- ❌ Grafana panel "LLM Cost by Tenant" not created
- ❌ Alert rule for budget threshold not added

**Files Affected:**
- `services/layer2-extraction/src/extraction/llm_extractor.py` - needs to call token metrics
- `monitoring/grafana/dashboards/value-fabric-overview.json` - needs panel
- `monitoring/alerting/rules.yml` - needs cost alert rule

---

## Issue 3: Task 79 - OpenAPI Contract Regeneration

### Current Status: SCRIPT EXISTS, NEEDS FIXING

**Current State:**
- `scripts/export_openapi.py` exists (276 lines)
- Uses `importlib.util` for explicit module loading
- Sets up package hierarchy for relative imports
- Export directory: `contracts/openapi/`

**Problems Identified:**
- Script may fail on module imports due to complex package structure
- Layer 3 OpenAPI contains Layer 1 specs (mentioned in roadmap)
- Missing schemas: `IngestRequest`, `Formula`, `GraphRAGResponse`

**Files Affected:**
- `scripts/export_openapi.py` - needs PYTHONPATH setup fix
- `contracts/openapi/layer3-knowledge.json` - needs regeneration

---

## Recommended Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 1 | L4 LangGraph Tests | 2 hours | Unblocks L4 testing confidence |
| 2 | Task 76 LLM Metrics | 4 hours | Cost observability for production |
| 3 | Task 79 OpenAPI | 4 hours | SDK generation, contract validation |

---

## Verification Commands

```bash
# Check L4 LangGraph tests
cd services/layer4-agents && python -m pytest tests/test_langgraph_execution.py -v

# Check LLM cost tracking tests
cd services/layer4-agents && python -m pytest tests/test_llm_cost_tracking.py -v

# Run OpenAPI export
python scripts/export_openapi.py
```
