"""Sprint 6 — LLM cost structured log field contract test (S6-R4.3).

Verifies that the required structured log fields are present in the
llm_call_complete event emitted by GovernedLLMClient._emit_call_complete.

Required fields (S6-R4.2):
  tenant_id       — from HarnessTraceEvent / run context
  workflow_id     — from Layer4EventContext / run context
  model           — LLM model name
  prompt_tokens   — input token count
  completion_tokens — output token count
  cost_usd        — calculated cost

Tests are source/AST-level to avoid the services/ namespace collision.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.unit]

_GOVERNED_LLM = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/services/governed_llm_client.py"
)
_OBSERVABILITY = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/observability.py"
)
_HARNESS_MODELS = pathlib.Path(
    "services/layer4-agents/src/layer4_agents/harness/models.py"
)


class TestLLMCostLogSchema:
    """LLM cost structured log events contain all required fields."""

    def test_emit_call_complete_includes_model(self) -> None:
        """_emit_call_complete metadata includes 'model' field."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_call_complete":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    '"model"' in fn_src or "'model'" in fn_src
                ), "_emit_call_complete must include 'model' in metadata"
                return

        pytest.fail("_emit_call_complete not found in governed_llm_client.py")

    def test_emit_call_complete_includes_prompt_tokens(self) -> None:
        """_emit_call_complete metadata includes 'prompt_tokens' field."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_call_complete":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "prompt_tokens" in fn_src
                ), "_emit_call_complete must include 'prompt_tokens' in metadata"
                return

        pytest.fail("_emit_call_complete not found in governed_llm_client.py")

    def test_emit_call_complete_includes_completion_tokens(self) -> None:
        """_emit_call_complete metadata includes 'completion_tokens' field."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_call_complete":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "completion_tokens" in fn_src
                ), "_emit_call_complete must include 'completion_tokens' in metadata"
                return

        pytest.fail("_emit_call_complete not found in governed_llm_client.py")

    def test_emit_call_complete_includes_cost_usd(self) -> None:
        """_emit_call_complete metadata includes 'cost_usd' field."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_call_complete":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "cost_usd" in fn_src
                ), "_emit_call_complete must include 'cost_usd' in metadata"
                return

        pytest.fail("_emit_call_complete not found in governed_llm_client.py")

    def test_emit_raw_injects_tenant_id_from_run(self) -> None:
        """_emit_raw injects tenant_id from self._run into HarnessTraceEvent."""
        source = _GOVERNED_LLM.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_emit_raw":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    "tenant_id" in fn_src
                ), "_emit_raw must include tenant_id from self._run"
                assert (
                    "self._run.tenant_id" in fn_src
                ), "_emit_raw must use self._run.tenant_id for tenant context"
                return

        pytest.fail("_emit_raw not found in governed_llm_client.py")

    def test_harness_trace_event_has_workflow_type_field(self) -> None:
        """HarnessTraceEvent includes workflow_type (serves as workflow context)."""
        source = _HARNESS_MODELS.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HarnessTraceEvent":
                class_src = ast.get_source_segment(source, node) or ""
                assert (
                    "workflow_type" in class_src
                ), "HarnessTraceEvent must include workflow_type field"
                assert (
                    "run_id" in class_src
                ), "HarnessTraceEvent must include run_id field (workflow run identifier)"
                assert (
                    "tenant_id" in class_src
                ), "HarnessTraceEvent must include tenant_id field"
                return

        pytest.fail("HarnessTraceEvent not found in harness/models.py")

    def test_lifecycle_logger_emits_workflow_id(self) -> None:
        """Layer4LifecycleLogger.emit() includes workflow_id in structured log payload."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "emit":
                fn_src = ast.get_source_segment(source, node) or ""
                assert (
                    '"workflow_id"' in fn_src or "'workflow_id'" in fn_src
                ), "Layer4LifecycleLogger.emit() must include 'workflow_id' in payload"
                assert (
                    '"tenant_id"' in fn_src or "'tenant_id'" in fn_src
                ), "Layer4LifecycleLogger.emit() must include 'tenant_id' in payload"
                return

        pytest.fail("Layer4LifecycleLogger.emit() not found in observability.py")

    def test_layer4_event_context_has_all_required_fields(self) -> None:
        """Layer4EventContext dataclass has all required structured log fields."""
        source = _OBSERVABILITY.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Layer4EventContext":
                class_src = ast.get_source_segment(source, node) or ""
                required = ["tenant_id", "workflow_id", "run_id", "trace_id"]
                for field in required:
                    assert (
                        field in class_src
                    ), f"Layer4EventContext must have '{field}' field"
                return

        pytest.fail("Layer4EventContext not found in observability.py")
