# Autonomous Test Hardening Loop Log

Repository: Fabric_4L
Start: 2026-05-13

---

## Loop 1
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py`
- **Defect or missing behavior:** `_execute_generate_sections` returns `BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult` missing required fields `blocked`, `error`, `remediation_items`, `truth_references`
- **Why this matters:** Pydantic v2 raises `ValidationError` when required fields are missing, causing the workflow step to crash at runtime
- **Test added:** `test_generate_sections_returns_complete_result_with_all_required_fields` in `tests/test_langgraph_execution.py`
- **Initial failure observed:** `pydantic_core._pydantic_core.ValidationError: 4 validation errors for BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult` (blocked, error, remediation_items, truth_references Field required)
- **Code fix:** Added the 4 missing required fields with sensible defaults (`blocked=False`, `error=""`, `remediation_items=[]`, `truth_references=[]`) to both return paths in `_execute_generate_sections`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 5 passed, 0 failed
- **Remaining risk:** Other workflow result models in `business_case.py` may have similar missing-field issues; should audit all `model_validate` calls

---

## Loop 2
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py`
- **Defect or missing behavior:** `_execute_roi_subworkflow` returns `BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult` missing required fields `status` and `roi_results` when `case_input` is None
- **Why this matters:** Pydantic v2 raises `ValidationError`, causing the workflow step to crash
- **Test added:** `test_roi_subworkflow_returns_complete_result_when_input_missing` in `tests/test_langgraph_execution.py`
- **Initial failure observed:** `pydantic_core._pydantic_core.ValidationError: 2 validation errors for BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult` (roi_results, status Field required)
- **Code fix:** Added `status="failed"` and `roi_results={}` to the early return in `_execute_roi_subworkflow`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 6 passed, 0 failed
- **Remaining risk:** Other `model_validate` calls in the file may still be incomplete

---

## Loop 3
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py`
- **Defect or missing behavior:** `_execute_verify_truth_requirements` returns `BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult` missing required fields `organization_id`, `requirements`, `truth_references`, `remediation_items` when `case_input` is None
- **Why this matters:** Pydantic v2 raises `ValidationError`, causing the workflow step to crash
- **Test added:** `test_verify_truth_requirements_returns_complete_result_when_input_missing` in `tests/test_langgraph_execution.py`
- **Initial failure observed:** `pydantic_core._pydantic_core.ValidationError: 4 validation errors for BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult` (organization_id, remediation_items, requirements, truth_references Field required)
- **Code fix:** Added `organization_id=None`, `requirements=[]`, `truth_references=[]`, `remediation_items=[]` to the early return in `_execute_verify_truth_requirements`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 7 passed, 0 failed
- **Remaining risk:** Need to audit remaining `model_validate` calls in business_case.py and other workflow files


---

## Loop 4
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/whitespace.py`
- **Defect or missing behavior:** `_execute_analyze_prospect` success path missing required `error`; `_execute_identify_gaps` success path missing required `error`; `_execute_score_opportunity` success path missing required `score`. Additionally, f-string JSON example on line 158 used single braces causing `ValueError: Invalid format specifier` at runtime.
- **Why this matters:** Pydantic v2 raises `ValidationError` when required fields are missing, crashing the workflow step. The f-string bug would also crash the workflow whenever the code path is reached.
- **Tests added:** `test_analyze_prospect_returns_complete_result`, `test_identify_gaps_returns_complete_result`, `test_score_opportunity_returns_complete_result` in `tests/test_langgraph_execution.py` (under `TestWhitespaceAnalysisWorkflow`)
- **Initial failure observed:** 
  - `ValidationError: error Field required` for analyze_prospect and identify_gaps
  - `ValidationError: score Field required` for score_opportunity
  - `ValueError: Invalid format specifier` for the f-string bug
- **Code fix:** 
  - Added `"error": ""` to `_execute_analyze_prospect` return dict
  - Added `"error": ""` to `_execute_identify_gaps` success return dict
  - Added `"score": int(total_score)` to `_execute_score_opportunity` success return dict
  - Escaped JSON braces in f-string on line 158 (`{{` and `}}`)
  - Also fixed `get_openai_provider` in `services/layer4-agents/src/layer4_agents/services/llm_provider.py` to handle Pydantic model configs (not just dicts) — it was failing with `AttributeError: 'WorkflowConfig' object has no attribute 'get'`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestWhitespaceAnalysisWorkflow -v`
- **Result:** 3 passed, 0 failed
- **Remaining risk:** `_execute_query_capabilities` may have ToolResult contract drift (`.get("results")` on a ToolResult object). Other workflow files (`prospecting.py`, `competitive_analysis.py`, etc.) should be audited for the same required-field omission pattern.


---

## Loop 5
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py` (continued audit)
- **Defect or missing behavior:** 
  - `_execute_gather_inputs` success path (line ~199) missing required `error` field
  - `_execute_verify_truth_requirements` no-requirements path (line ~441) missing required `organization_id` field
- **Why this matters:** Pydantic v2 raises `ValidationError` when required fields are missing, crashing the workflow step at runtime
- **Tests added:**
  - `test_gather_inputs_returns_complete_result` in `tests/test_langgraph_execution.py`
  - `test_verify_truth_requirements_returns_complete_result_when_no_requirements` in `tests/test_langgraph_execution.py`
- **Initial failure observed:** 
  - `ValidationError: error Field required` for gather_inputs
  - `ValidationError: organization_id Field required` for verify_truth_requirements
- **Code fix:** 
  - Added `"error": ""` to `_execute_gather_inputs` success return dict
  - Added `"organization_id": None` to `_execute_verify_truth_requirements` no-requirements return dict
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 9 passed, 0 failed
- **Remaining risk:** `_execute_query_capabilities` in `whitespace.py` uses `.get("results")` on `tool_registry.execute()` return, which will fail with ToolResult contract drift. `_sync_ground_truths_to_kg` success path returns raw `sync_result` from Layer5 client without validating against `BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult`. Other workflow files outside `services/layer4-agents/src/layer4_agents/workflows/` may have similar patterns.


---

## Loop 6
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/whitespace.py` (ToolResult contract drift)
- **Defect or missing behavior:** `_execute_query_capabilities` and `_execute_identify_gaps` called `.get("results", [])` directly on `tool_registry.execute()` return. In production the registry returns `ToolResult` (not a raw dict), so `.get()` raises `AttributeError`.
- **Why this matters:** Workflow steps crash at runtime when real ToolRegistry is wired in, because `ToolResult` has no `.get()` method — data lives in `.data`
- **Test added:** `test_query_capabilities_handles_tool_result_contract` in `tests/test_langgraph_execution.py` (feeds `ToolResult.success(data={...})` to the mock registry)
- **Initial failure observed:** `AttributeError: 'ToolResult' object has no attribute 'get'` (confirmed by inspection; test validates fix)
- **Code fix:** 
  - Added `_unwrap_tool_data()` helper to `whitespace.py` (same pattern as `roi_calculator.py`)
  - Replaced `query_result.get("results", [])` with `_unwrap_tool_data(query_result).get("results", [])`
  - Replaced `search_result.get("results", [])` with `_unwrap_tool_data(search_result).get("results", [])`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestWhitespaceAnalysisWorkflow -v`
- **Result:** 4 passed, 0 failed
- **Remaining risk:** `_sync_ground_truths_to_kg` in `business_case.py` returns raw `sync_result` without validating against its result model. Other layers (Layer 1 Celery tasks, CRM webhooks) have broad `except Exception` swallowing. Remaining 69 loops should target those.


---

## Loop 7
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py` — `_sync_ground_truths_to_kg`
- **Defect or missing behavior:** Success path returned raw `sync_result` from Layer 5 client without validating against `BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult`. If the upstream API omitted `error` (common on success), downstream consumers expecting the contract shape would receive an unvalidated dict.
- **Why this matters:** Contract drift between Layer 4 workflow output and its declared result model; future consumers or serialization could break
- **Test added:** `test_sync_ground_truths_normalizes_success_result` in `tests/test_langgraph_execution.py`
- **Initial failure observed:** N/A (defect discovered by code audit), but test validates that a Layer 5 response missing `error` is normalized to include `error: ""`
- **Code fix:** Wrapped success return in `BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult.model_validate({...})` with safe defaults (`synced`, `failed`, `error` extracted via `.get()` with fallbacks)
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 10 passed, 0 failed
- **Remaining risk:** Broad `except Exception` swallowing identified across Layer 1 Celery tasks and CRM webhooks. Should audit `services/layer1-ingestion/` next. Also, `is_enabled` coroutine never awaited warnings in business_case tests suggest a feature-flag async/await mismatch.


---

## Loop 8
- **Area inspected:** `services/layer4-agents/src/layer4_agents/workflows/business_case.py` — async/await mismatch and ToolResult contract drift
- **Defect or missing behavior:** 
  1. `is_enabled` (async feature-flag check) was called synchronously, causing it to return a coroutine object instead of a bool. This meant `enhanced_mode` was always truthy and the coroutine was never awaited.
  2. Multiple `.get()` calls on raw `tool_registry.execute()` results: `query_result.get("results")`, `chart_result.get("chart_data")`, `section_result.get("content")`, `result.get("document_bytes")`. Production `ToolRegistry.execute` returns `ToolResult` (data nested in `.data`), so these `.get()` calls would return `None` instead of the actual payload.
- **Why this matters:** 
  1. Feature flag logic was broken — enhanced narrative generation would always run.
  2. Tool result unwrapping failure would cause empty charts, empty sections, empty documents in production.
- **Tests added:** N/A for this loop (existing tests already covered the code paths; warnings were the signal)
- **Initial failure observed:** 
  - `RuntimeWarning: coroutine 'is_enabled' was never awaited` in test output
  - `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` in test output (symptom of `.get()` on AsyncMock, which mirrors production ToolResult contract drift)
- **Code fix:** 
  - Added `await` to `is_enabled(...)` call
  - Added `_unwrap_tool_data()` helper to `business_case.py` (same pattern as `roi_calculator.py` and `whitespace.py`)
  - Applied `_unwrap_tool_data()` to all 4 tool result `.get()` call sites in `_resolve_value_driver_ids`, `_execute_generate_sections`, and `_execute_assemble_document`
- **Validation run:** `pytest tests/test_langgraph_execution.py::TestBusinessCaseGeneratorWorkflow -v`
- **Result:** 10 passed, 0 failed (coroutine warnings eliminated)
- **Remaining risk:** 5 pre-existing failures in `test_langgraph_execution.py` unrelated to current changes. Broad `except Exception` swallowing in Layer 1 Celery tasks and CRM webhooks still needs audit.

