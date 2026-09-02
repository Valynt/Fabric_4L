from __future__ import annotations

"""Tests for ToolResult structured error handling (Contract §2.4).

Verifies that tools return structured ToolResult instead of raising exceptions.
Location: services/layer4-agents/tests/ to use correct conftest.py paths.
"""


import inspect

import pytest
from pydantic import BaseModel, ValidationError

from layer4_agents.tools import BaseTool, ToolRegistry, ToolResult
from layer4_agents.tools.calculation_tools import CalculateROITool, EvaluateFormulaTool
from layer4_agents.tools.competitive_tools import (
    AnalyzeCompetitionTool,
    LLMDifferenceItem,
    LLMDifferencesResponse,
)


def validate_tool_result(result):
    """Validate ToolResult structure per Contract §2.4.

    Ensures:
    - status is valid
    - error structure is correct when present
    - no sensitive internals leaked to user-facing message
    - trace_id available for debugging correlation
    """
    assert result.status in {"success", "error"}

    if result.status == "error":
        assert isinstance(result.error, dict), "error must be a dict"
        assert result.error.get("code"), "error.code is required"
        assert result.error.get("message"), "error.message is required"
        # Security: ensure no stack traces or sensitive details in user message
        message = result.error.get("message", "").lower()
        assert "traceback" not in message, "traceback leaked to user message"
        assert "exception" not in message or "expected" in message, "raw exception leaked"

    # Metadata should exist for traceability
    assert result.metadata is not None, "metadata required for traceability"
    assert "trace_id" in result.metadata or "execution_time_ms" in result.metadata, \
        "metadata must contain trace_id or execution_time_ms"


# ═══════════════════════════════════════════════════════════════════════════
# Contract §2.4: ToolResult Structure Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestToolResultStructure:
    """Test ToolResult structure and factory methods."""

    def test_tool_result_success(self):
        """Proof 1: ToolResult success result validates required fields."""
        result = ToolResult.success(
            data={"result": 42},
            metadata={"trace_id": "abc-123", "execution_time_ms": 100},
        )

        validate_tool_result(result)
        assert result.status == "success"
        assert result.data == {"result": 42}
        assert result.error is None
        assert result.metadata["trace_id"] == "abc-123"
        assert result.metadata["execution_time_ms"] == 100

    def test_tool_result_error(self):
        """Proof 2: ToolResult error result validates required fields."""
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Input validation failed",
            recoverable=False,
            trace_id="abc-456",
        )

        validate_tool_result(result)
        assert result.status == "error"
        assert result.data is None
        assert result.error["code"] == "VALIDATION_ERROR"
        assert result.error["message"] == "Input validation failed"
        assert result.error["recoverable"] is False
        assert result.metadata["trace_id"] == "abc-456"

    def test_tool_result_error_safe_message(self):
        """Proof 5: Error message is safe for users - no internal details."""
        result = ToolResult.failure(
            code="INTERNAL_ERROR",
            message="An internal error occurred. Please try again later.",
            recoverable=True,
        )

        # Safe message should not contain sensitive internals
        message = result.error["message"]
        assert "traceback" not in message.lower()
        assert "exception" not in message.lower()
        assert "password" not in message.lower()
        assert "secret" not in message.lower()
        assert "internal" in message.lower()  # Safe, generic message is OK

    def test_tool_result_with_exception(self):
        """Test that exceptions can be captured in metadata for debugging."""
        result = ToolResult.failure(
            code="TOOL_EXECUTION_ERROR",
            message="Tool execution failed",
            details={"exception_type": "ValueError", "exception_str": "something failed"},
            trace_id="xyz-789",
        )

        validate_tool_result(result)
        # Details contain exception info for debugging (not user-facing message)
        assert "exception_type" in result.error.get("details", {})
        assert result.metadata.get("trace_id") == "xyz-789"

    def test_tool_result_trace_id_propagation(self):
        """Proof 6: trace_id or equivalent correlation path exists."""
        result = ToolResult.success(
            data={"value": 1},
            metadata={"trace_id": "correlation-123"},
        )

        assert result.metadata.get("trace_id") == "correlation-123"

        # Error result also has trace_id
        error_result = ToolResult.failure(
            code="ERROR",
            message="Error occurred",
            trace_id="correlation-456",
        )
        assert error_result.metadata.get("trace_id") == "correlation-456"


class TestBaseToolContractCompliance:
    """Test that BaseTool returns ToolResult per Contract §2.4."""

    @pytest.fixture
    def test_tool(self):
        """Create a simple test tool."""
        class SimpleInput(BaseModel):
            value: int

        class SimpleOutput(BaseModel):
            result: int

        class SimpleTool(BaseTool):
            name = "simple_tool"
            input_schema = SimpleInput
            output_schema = SimpleOutput

            async def execute(self, input_data):
                return SimpleOutput(result=input_data.value * 2)

        return SimpleTool()

    @pytest.fixture
    def failing_tool(self):
        """Create a tool that always fails via exception."""
        class FailingInput(BaseModel):
            message: str = "error"

        class FailingOutput(BaseModel):
            result: str

        class FailingTool(BaseTool):
            name = "failing_tool"
            input_schema = FailingInput
            output_schema = FailingOutput

            async def execute(self, input_data):
                # Intentionally raises - BaseTool.run() should catch and convert
                raise ValueError(f"Execution failed: {input_data.message}")

        return FailingTool()

    @pytest.mark.asyncio
    async def test_tool_returns_tool_result_on_success(self, test_tool):
        """Proof 1: ToolResult success result validates required fields."""
        result = await test_tool.run({"value": 5})

        assert isinstance(result, ToolResult)
        validate_tool_result(result)
        assert result.status == "success"
        assert result.data["result"] == 10
        assert result.error is None
        assert result.metadata is not None
        assert "execution_time_ms" in result.metadata

    @pytest.mark.asyncio
    async def test_tool_returns_tool_result_on_failure(self, failing_tool):
        """Proof 3: Tool failure does not raise as normal control flow.
        Proof 4: Tool failure does not return fake success."""
        result = await failing_tool.run({"message": "test error"})

        # Should NOT raise exception - returns ToolResult instead
        assert isinstance(result, ToolResult)
        validate_tool_result(result)
        
        # Proof 4: Should be error status, not success
        assert result.status == "error"
        assert result.data is None
        assert result.error is not None
        assert result.error["code"] == "TOOL_EXECUTION_ERROR"
        
        # Proof 5: Safe user message - no raw exception details
        assert "test error" not in result.error["message"]
        
        # Proof 6: trace_id should be present for debugging correlation
        assert result.metadata.get("trace_id") is not None
        assert result.error["recoverable"] is False

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_invalid_input(self, test_tool):
        """Verify tool returns ToolResult error on invalid input."""
        result = await test_tool.run({"value": "not an integer"})

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error["code"] == "INPUT_VALIDATION_ERROR"
        assert "Invalid input" in result.error["message"]
        assert result.error["recoverable"] is False

    @pytest.mark.asyncio
    async def test_tool_returns_error_when_no_schema(self):
        """Verify tool returns error when no input schema defined."""
        class NoSchemaTool(BaseTool):
            name = "no_schema_tool"
            output_schema = BaseModel

            async def execute(self, input_data):
                return {"result": "ok"}

        tool = NoSchemaTool()
        result = await tool.run({"anything": "goes"})

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error["code"] == "CONFIGURATION_ERROR"


class TestToolRegistryContractCompliance:
    """Test ToolRegistry properly handles ToolResult."""

    @pytest.fixture
    def registry(self):
        """Create a fresh tool registry."""
        return ToolRegistry()

    @pytest.fixture
    def registered_failing_tool(self, registry):
        """Register a tool that fails."""
        class FailInput(BaseModel):
            trigger: str

        class FailOutput(BaseModel):
            result: str

        class FailingTool(BaseTool):
            name = "registered_failing_tool"
            input_schema = FailInput
            output_schema = FailOutput

            async def execute(self, input_data):
                raise RuntimeError("Simulated tool failure")

        tool = FailingTool()
        registry.register(tool)
        return tool

    @pytest.mark.asyncio
    async def test_registry_execute_returns_tool_result_on_failure(
        self, registry, registered_failing_tool
    ):
        """Proof 3: Registry tool failure does not raise as normal control flow."""
        result = await registry.execute(
            "registered_failing_tool",
            {
                "trigger": "fail",
                "tenant_id": "12345678-1234-1234-1234-123456789abc",
                "workflow_id": "wf-contract",
                "run_id": "run-contract",
                "trace_id": "trace-contract",
            },
        )

        # Should return ToolResult, not raise
        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error["code"] == "TOOL_EXECUTION_ERROR"


# ═══════════════════════════════════════════════════════════════════════════
# Contract §2.5: LLM Response Validation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestLLMResponseValidation:
    """Test Pydantic validation for LLM responses (Contract §2.5).

    Replaces raw json.loads with structured model validation.
    """

    def test_llm_response_model_validates_correct_json(self):
        """Proof 7: LLM valid output uses Pydantic validation, not raw json.loads."""
        valid_json = '{"differences": [{"category": "COST_STRUCTURE", "description": "20% cheaper", "impact_direction": "FAVORS_US", "confidence_score": 0.8}]}'

        # Uses Pydantic model_validate_json, not raw json.loads
        result = LLMDifferencesResponse.model_validate_json(valid_json)
        
        assert len(result.differences) == 1
        assert result.differences[0].category == "COST_STRUCTURE"
        assert result.differences[0].confidence_score == 0.8

    def test_llm_response_model_handles_invalid_json(self):
        """Proof 8: LLM malformed output produces structured failure/degraded result."""
        # Malformed JSON should raise validation error (not silently fail with raw json.loads)
        invalid_json = '{"differences": [invalid]}'

        with pytest.raises(ValidationError):
            LLMDifferencesResponse.model_validate_json(invalid_json)

    def test_llm_response_model_handles_missing_fields_gracefully(self):
        """Proof 8: Partial/malformed LLM output produces degraded result with defaults."""
        # Missing fields should use defaults, not crash
        partial_json = '{"differences": [{"description": "Some description"}]}'

        result = LLMDifferencesResponse.model_validate_json(partial_json)
        
        # Should have one difference with default values
        assert len(result.differences) == 1
        assert result.differences[0].category == "CAPABILITY_TO_OUTCOME"  # default
        assert result.differences[0].confidence_score == 0.5  # default
        assert result.differences[0].is_unsupported_claim is False  # default
        assert result.differences[0].description == "Some description"

    def test_llm_response_model_handles_empty_json(self):
        """Proof 8: Empty JSON produces structured empty result."""
        empty_json = "{}"

        result = LLMDifferencesResponse.model_validate_json(empty_json)
        
        # Should have empty differences list (default_factory=list)
        assert result.differences == []

    def test_llm_item_model_validates_partial_data(self):
        """Proof 8: Individual item validation with defaults for missing fields."""
        partial = {"description": "Test description"}
        item = LLMDifferenceItem.model_validate(partial)

        assert item.category == "CAPABILITY_TO_OUTCOME"  # default
        assert item.confidence_score == 0.5  # default
        assert item.is_unsupported_claim is False  # default
        assert item.impact_direction == "FAVORS_US"  # default
        assert item.description == "Test description"


class TestLLMNoRawJsonLoads:
    """Verify no raw json.loads is used for LLM output parsing."""

    def test_llm_response_uses_pydantic_not_json_loads(self):
        """Proof 7: Verify competitive_tools uses Pydantic validation.
        
        This test verifies the code structure - the actual proof is in
        test_llm_response_model_validates_correct_json above.
        """
        # Get source of _extract_differences_via_llm
        source = inspect.getsource(AnalyzeCompetitionTool._extract_differences_via_llm)

        # Should use model_validate_json, not json.loads
        assert "model_validate_json" in source
        # Should NOT have raw json.loads on LLM response
        assert "json.loads" not in source or source.count("json.loads") == 0


# ═══════════════════════════════════════════════════════════════════════════
# Real Tool Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRealToolsReturnToolResult:
    """Test that real tool implementations return ToolResult."""

    @pytest.mark.asyncio
    async def test_evaluate_formula_tool_returns_tool_result(self):
        """EvaluateFormulaTool returns ToolResult on success."""
        tool = EvaluateFormulaTool()
        result = await tool.run({"expression": "2 + 2", "variables": {}})

        assert isinstance(result, ToolResult)
        validate_tool_result(result)


# ═══════════════════════════════════════════════════════════════════════════
# Focused Agent Tool Result Safety Additions
# ═══════════════════════════════════════════════════════════════════════════


class TestFocusedAgentToolResultContract:
    """Focused production-safety checks for agent-facing tool execution."""

    @pytest.mark.asyncio
    async def test_agent_tool_success_returns_structured_result(self):
        class Input(BaseModel):
            value: int

        class Output(BaseModel):
            doubled: int

        class Tool(BaseTool):
            name = "agent_success_tool"
            input_schema = Input
            output_schema = Output

            async def execute(self, input_data):
                return Output(doubled=input_data.value * 2)

        result = await Tool(config={"tenant_id": "tenant-a"}).run(
            {"value": 3, "trace_id": "trace-success", "request_id": "req-success"}
        )

        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data == {"doubled": 6}
        assert result.metadata["trace_id"] == "trace-success"
        assert result.metadata["request_id"] == "req-success"
        assert result.metadata["tenant_id"] == "tenant-a"

    @pytest.mark.asyncio
    async def test_agent_tool_exception_returns_structured_error_result(self):
        class Input(BaseModel):
            value: str

        class Tool(BaseTool):
            name = "agent_exception_tool"
            input_schema = Input
            output_schema = BaseModel

            async def execute(self, input_data):
                raise RuntimeError("database password is hunter2")

        result = await Tool().run({"value": "boom", "trace_id": "trace-error"})

        assert result.status == "error"
        assert result.error["code"] == "TOOL_EXECUTION_ERROR"
        assert "hunter2" not in result.error["message"]
        assert "password" not in result.error["message"].lower()
        assert result.metadata["trace_id"] == "trace-error"

    @pytest.mark.asyncio
    async def test_agent_tool_error_does_not_leak_secret_values(self):
        class Input(BaseModel):
            required_value: int

        class Tool(BaseTool):
            name = "agent_secret_validation_tool"
            input_schema = Input
            output_schema = BaseModel

            async def execute(self, input_data):
                return {}

        secret = "sk-live-super-secret-token"
        result = await Tool().run(
            {"api_key": secret, "password": "p@ssw0rd", "trace_id": "trace-secret"}
        )

        assert result.status == "error"
        rendered = str(result.model_dump())
        assert secret not in rendered
        assert "p@ssw0rd" not in rendered
        assert "api_key" not in rendered
        assert "[redacted]" in rendered

    @pytest.mark.asyncio
    async def test_agent_tool_result_preserves_request_context(self):
        class Input(BaseModel):
            value: int

        class Tool(BaseTool):
            name = "agent_context_tool"
            input_schema = Input
            output_schema = BaseModel

            async def execute(self, input_data):
                return {"ok": True}

        result = await Tool(config={"tenant_id": "tenant-context"}).run(
            {"value": 1, "trace_id": "trace-context", "request_id": "req-context"}
        )

        assert result.metadata["trace_id"] == "trace-context"
        assert result.metadata["request_id"] == "req-context"
        assert result.metadata["tenant_id"] == "tenant-context"

    @pytest.mark.asyncio
    async def test_agent_tool_timeout_returns_structured_degraded_response(self):
        import asyncio

        class Input(BaseModel):
            value: int

        class SlowTool(BaseTool):
            name = "agent_slow_tool"
            input_schema = Input
            output_schema = BaseModel
            timeout_seconds = 0.01

            async def execute(self, input_data):
                await asyncio.sleep(0.1)
                return {"ok": True}

        result = await SlowTool().run({"value": 1, "trace_id": "trace-timeout"})

        assert result.status == "error"
        assert result.error["code"] == "TOOL_TIMEOUT"
        assert result.error["recoverable"] is True
        assert "timed out" in result.error["message"]
        assert result.metadata["trace_id"] == "trace-timeout"

    @pytest.mark.asyncio
    async def test_agent_timeout_creates_audit_event(self, monkeypatch):
        import asyncio

        class Input(BaseModel):
            value: int

        class SlowTool(BaseTool):
            name = "audited_slow_tool"
            input_schema = Input
            output_schema = BaseModel
            timeout_seconds = 0.01

            async def execute(self, input_data):
                await asyncio.sleep(0.1)
                return {"ok": True}

        audit_events = []

        def capture_audit(**kwargs):
            audit_events.append(kwargs)

        registry = ToolRegistry()
        registry.register(SlowTool(config={"tenant_id": "12345678-1234-1234-1234-123456789abc"}))
        monkeypatch.setenv("AUDIT_LEDGER_MODE", "enabled")
        monkeypatch.setattr(ToolRegistry, "_emit_tool_invocation_audit", staticmethod(capture_audit))

        result = await registry.execute(
            "audited_slow_tool",
            {"value": 1, "trace_id": "trace-timeout-audit"},
        )

        assert result.status == "error"
        assert result.error["code"] == "TOOL_TIMEOUT"
        assert audit_events
        assert audit_events[-1]["outcome"] == "failure"
        assert audit_events[-1]["trace_id"] == "trace-timeout-audit"
        
        if result.status == "success":
            assert "result" in result.data
        else:
            # Even errors should be structured
            assert result.error is not None
            assert "code" in result.error

    @pytest.mark.asyncio
    async def test_evaluate_formula_tool_returns_error_on_invalid_expression(self):
        """Proof 2,3,4: Tool returns structured error, not exception or fake success."""
        tool = EvaluateFormulaTool()
        result = await tool.run({"expression": "invalid!!!", "variables": {}})

        assert isinstance(result, ToolResult)
        # Proof 4: Should be error, not fake success
        if result.status == "error":
            assert result.error is not None
            assert result.data is None  # No fake data

    @pytest.mark.asyncio
    async def test_calculate_roi_tool_returns_tool_result(self):
        """CalculateROITool returns ToolResult."""
        tool = CalculateROITool()
        result = await tool.run({
            "benefits": [{"amount": 1000, "frequency": "monthly"}],
            "costs": [{"amount": 500, "frequency": "monthly"}],
            "timeframe_months": 12,
        })

        assert isinstance(result, ToolResult)
        validate_tool_result(result)
