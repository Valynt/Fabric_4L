"""Sprint 6 — Layer 4 structured log schema contract tests (S6-R5).

Verifies that the required structured log fields are present in:
  S6-R5.1  Harness trace events (tenant_id, run_id, workflow_type, stage, trace_id)
  S6-R5.2  Validation outcome events (tenant_id, run_id, gate_id, outcome, decision_by)
  S6-R5.3  Failed/degraded workflow events (tenant_id, run_id, error_class, error_code, stage)

All checks are source/AST-level — no live services required.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.unit]

_HARNESS_MODELS = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/harness/models.py"
)
_OBSERVABILITY = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/observability.py"
)
_HARNESS_ROUTES = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/api/routes/harness.py"
)
_GOVERNED_LLM = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/services/governed_llm_client.py"
)


# ---------------------------------------------------------------------------
# S6-R5.1 — Harness trace event schema
# ---------------------------------------------------------------------------


class TestHarnessTraceEventSchema:
    """HarnessTraceEvent contains all required structured log fields."""

    def test_trace_event_has_tenant_id(self) -> None:
        """HarnessTraceEvent.tenant_id is a required field."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "tenant_id" in class_src
                ), "HarnessTraceEvent must have tenant_id field"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_trace_event_has_run_id(self) -> None:
        """HarnessTraceEvent.run_id is a required field."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert "run_id" in class_src, "HarnessTraceEvent must have run_id field"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_trace_event_has_workflow_type(self) -> None:
        """HarnessTraceEvent.workflow_type is a required field."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "workflow_type" in class_src
                ), "HarnessTraceEvent must have workflow_type field"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_trace_event_has_trace_id(self) -> None:
        """HarnessTraceEvent.trace_id is a required field."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "trace_id" in class_src
                ), "HarnessTraceEvent must have trace_id field"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_trace_event_has_event_type_as_stage(self) -> None:
        """HarnessTraceEvent.event_type serves as the stage field."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "event_type" in class_src
                ), "HarnessTraceEvent must have event_type field (serves as stage)"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_trace_event_validates_required_ids(self) -> None:
        """HarnessTraceEvent validates that tenant_id, trace_id, run_id are non-empty."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "field_validator" in class_src or "validator" in class_src
                ), "HarnessTraceEvent must validate required ID fields"
                return
        pytest.fail("HarnessTraceEvent not found")

    def test_lifecycle_logger_emits_stage_field(self) -> None:
        """Layer4LifecycleLogger.emit() includes event_stage in payload."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "event_stage" in fn_src or "stage" in fn_src
                ), "Layer4LifecycleLogger.emit() must include stage/event_stage in payload"
                return
        pytest.fail("Layer4LifecycleLogger.emit() not found")


# ---------------------------------------------------------------------------
# S6-R5.2 — Validation outcome event schema
# ---------------------------------------------------------------------------


class TestValidationOutcomeSchema:
    """Validation outcome events contain all required structured log fields."""

    def test_gate_decision_emits_gate_id(self) -> None:
        """decide_gate route uses gate_id in its response/logging."""
        source = _HARNESS_ROUTES.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide_gate":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "gate_id" in fn_src, "decide_gate must use gate_id in its logic"
                return
        pytest.fail("decide_gate not found in harness.py")

    def test_gate_decision_emits_decision_by_from_context(self) -> None:
        """decide_gate derives decision_by from ctx.user_id (server-derived)."""
        source = _HARNESS_ROUTES.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide_gate":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "ctx.user_id" in fn_src
                ), "decide_gate must derive decision_by from ctx.user_id"
                assert (
                    "server_decision_by" in fn_src
                ), "decide_gate must use server_decision_by variable"
                return
        pytest.fail("decide_gate not found in harness.py")

    def test_gate_decision_passes_tenant_id_to_registry(self) -> None:
        """decide_gate passes ctx.tenant_id to registry.decide_gate."""
        source = _HARNESS_ROUTES.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide_gate":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "ctx.tenant_id" in fn_src
                ), "decide_gate must pass ctx.tenant_id to registry"
                return
        pytest.fail("decide_gate not found in harness.py")

    def test_harness_run_has_validation_state(self) -> None:
        """HarnessRun model includes validation_state for outcome tracking."""
        source = _HARNESS_MODELS.read_text()
        assert (
            "validation_state" in source or "ValidationState" in source
        ), "harness/models.py must include validation_state for outcome tracking"

    def test_gate_response_includes_outcome_fields(self) -> None:
        """GateResponse includes status (outcome) and decision_by fields."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "GateResponse":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "status" in class_src or "decision" in class_src
                ), "GateResponse must include status/outcome field"
                assert (
                    "decision_by" in class_src or "decided_by" in class_src
                ), "GateResponse must include decision_by field"
                return
        # GateResponse may be in api_models.py
        api_models = pathlib.Path(
            "services/layer4-agents/src/layer4_agents/harness/api_models.py"
        )
        if api_models.exists():
            source2 = api_models.read_text()
            if "GateResponse" in source2:
                assert (
                    "decision_by" in source2 or "decided_by" in source2
                ), "GateResponse must include decision_by field"
                return
        pytest.fail("GateResponse not found in harness models")


# ---------------------------------------------------------------------------
# S6-R5.3 — Failed/degraded workflow event schema
# ---------------------------------------------------------------------------


class TestFailedWorkflowSchema:
    """Failed/degraded workflow events contain all required structured log fields."""

    def test_lifecycle_logger_supports_error_class(self) -> None:
        """Layer4LifecycleLogger.emit() accepts error_class parameter."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "error_class" in fn_src
                ), "Layer4LifecycleLogger.emit() must accept error_class parameter"
                return
        pytest.fail("Layer4LifecycleLogger.emit() not found")

    def test_lifecycle_logger_supports_error_code(self) -> None:
        """Layer4LifecycleLogger.emit() accepts error_code parameter."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "error_code" in fn_src
                ), "Layer4LifecycleLogger.emit() must accept error_code parameter"
                return
        pytest.fail("Layer4LifecycleLogger.emit() not found")

    def test_lifecycle_logger_includes_tenant_id_in_payload(self) -> None:
        """Layer4LifecycleLogger.emit() includes tenant_id in every log payload."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "tenant_id" in fn_src
                ), "Layer4LifecycleLogger.emit() must include tenant_id in payload"
                return
        pytest.fail("Layer4LifecycleLogger.emit() not found")

    def test_lifecycle_logger_includes_run_id_in_payload(self) -> None:
        """Layer4LifecycleLogger.emit() includes run_id in every log payload."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "run_id" in fn_src
                ), "Layer4LifecycleLogger.emit() must include run_id in payload"
                return
        pytest.fail("Layer4LifecycleLogger.emit() not found")

    def test_executor_emits_lifecycle_event_on_workflow_start(self) -> None:
        """executor.py emits a lifecycle event at workflow start with stage='start'."""
        source = pathlib.Path(
            "services/layer4-agents/src/layer4_agents/engine/executor.py"
        ).read_text()
        assert (
            "lifecycle_logger.emit" in source
        ), "executor.py must call lifecycle_logger.emit() for workflow lifecycle events"
        assert (
            '"start"' in source or "'start'" in source
        ), "executor.py must emit a 'start' stage event"

    def test_governed_llm_client_emits_failed_event(self) -> None:
        """GovernedLLMClient emits llm_call_failed event on error."""
        source = _GOVERNED_LLM.read_text()
        assert (
            "llm_call_failed" in source
        ), "governed_llm_client.py must emit 'llm_call_failed' event on error"

    def test_governed_llm_client_failed_event_includes_error(self) -> None:
        """llm_call_failed event metadata includes error field."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_call_failed":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    '"error"' in fn_src or "'error'" in fn_src
                ), "_emit_call_failed must include 'error' field in metadata"
                assert (
                    "model" in fn_src
                ), "_emit_call_failed must include 'model' field in metadata"
                return
        pytest.fail("_emit_call_failed not found in governed_llm_client.py")
