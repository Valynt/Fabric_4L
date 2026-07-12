"""Tests for ToolResult structured error handling (Contract §2.4).

Verifies that tools return structured ToolResult instead of raising exceptions.
"""

import pytest
from layer4_agents.tools.calculation_tools import CalculateROITool, EvaluateFormulaTool
from layer4_agents.tools.registry import BaseTool, ToolRegistry, ToolResult
from pydantic import BaseModel


def validate_tool_result(result):
    """Validate ToolResult structure per Contract §2.4.

    Ensures:
    - status is valid
    - error structure is correct when present
    - no sensitive internals leaked to user-facing message
    - trace_id available for debugging correlation (for execution errors)
    """
    assert result.status in {"success", "error"}

    if result.status == "error":
        assert result.error is not None, "error is required for error status"
        assert isinstance(result.error, dict), "error must be a dict"
        assert result.error.get("code"), "error.code is required"
        assert result.error.get("message"), "error.message is required"
        # Security: ensure no stack traces or sensitive details in user message
        message = result.error.get("message", "").lower()
        assert "traceback" not in message, "traceback leaked to user message"
        assert "exception" not in message or "expected" in message, "raw exception leaked"

    # Metadata should exist for traceability (except for input validation which occurs before execution)
    if result.status == "error" and result.error is not None and result.error.get("code") != "INPUT_VALIDATION_ERROR":
        assert result.metadata is not None, "metadata required for traceability"
        assert "trace_id" in result.metadata or "execution_time_ms" in result.metadata, \
            "metadata should contain trace_id or execution_time_ms"


class TestToolResultStructure:
    """Test ToolResult structure and factory methods."""

    def test_tool_result_success(self):
        """Test creating a success result."""
        data = {"result": 42, "message": "success"}
        metadata = {"execution_time_ms": 100}

        result = ToolResult.success(data=data, metadata=metadata)

        assert result.status == "success"
        assert result.data is not None
        assert result.data == data
        assert result.error is None
        assert result.metadata == metadata
        assert result.is_success() is True
        assert result.is_error() is False

    def test_tool_result_error(self):
        """Test creating an error result."""
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "value"},
            trace_id="trace-123",
            recoverable=False,
        )

        assert result.status == "error"
        assert result.error is not None
        assert result.data is None
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"
        assert result.error["message"] == "Invalid input"
        assert result.error["details"] == {"field": "value"}
        assert result.error["recoverable"] is False
        assert result.metadata == {"trace_id": "trace-123"}
        assert result.is_success() is False
        assert result.is_error() is True

    def test_tool_result_error_minimal(self):
        """Test creating a minimal error result."""
        result = ToolResult.failure(
            code="TIMEOUT",
            message="Tool timed out",
        )

        assert result.error is not None
        assert result.error["code"] == "TIMEOUT"
        assert result.error["message"] == "Tool timed out"
        assert result.error["recoverable"] is False
        assert "details" not in result.error
        assert result.metadata is None


class TestBaseToolContractCompliance:
    """Test that BaseTool returns ToolResult per Contract §2.4."""

    @pytest.fixture
    def registry(self):
        """Create a fresh tool registry."""
        return ToolRegistry()

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
        """Create a tool that always fails."""
        class FailingInput(BaseModel):
            message: str = "error"

        class FailingOutput(BaseModel):
            result: str

        class FailingTool(BaseTool):
            name = "failing_tool"
            input_schema = FailingInput
            output_schema = FailingOutput

            async def execute(self, input_data):
                raise ValueError(f"Execution failed: {input_data.message}")

        return FailingTool()

    @pytest.mark.asyncio
    async def test_tool_returns_tool_result_on_success(self, test_tool):
        """Verify tool returns ToolResult on successful execution."""
        result = await test_tool.run({"value": 5})

        assert isinstance(result, ToolResult)
        validate_tool_result(result)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["result"] == 10
        assert result.error is None
        assert result.metadata is not None
        assert "execution_time_ms" in result.metadata

    @pytest.mark.asyncio
    async def test_tool_returns_tool_result_on_failure(self, failing_tool):
        """Verify tool returns ToolResult on failure instead of raising."""
        result = await failing_tool.run({"message": "test error"})

        assert isinstance(result, ToolResult)
        validate_tool_result(result)
        assert result.status == "error"
        assert result.error is not None
        assert result.data is None
        assert result.error is not None
        assert result.error["code"] == "TOOL_EXECUTION_ERROR"
        # Safe user message - no raw exception details
        assert "test error" not in result.error["message"]
        # Metadata should be present for traceability (trace_id or execution_time_ms)
        assert result.metadata is not None
        assert "trace_id" in result.metadata or "execution_time_ms" in result.metadata
        # Metadata should be present for traceability (trace_id or execution_time_ms)
        assert result.metadata is not None
        assert "trace_id" in result.metadata or "execution_time_ms" in result.metadata
        assert result.error["recoverable"] is False

    @pytest.mark.asyncio
    async def test_tool_returns_error_on_invalid_input(self, test_tool):
        """Verify tool returns ToolResult error on invalid input."""
        result = await test_tool.run({"value": "not an integer"})

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "INPUT_VALIDATION_ERROR"
        assert "Invalid input" in result.error["message"]
        assert result.error["recoverable"] is False

    @pytest.mark.asyncio
    async def test_tool_returns_error_when_no_schema(self):
        """Verify tool returns error when no input schema defined."""
        class NoSchemaTool(BaseTool):
            name = "no_schema_tool"

            async def execute(self, input_data):
                return {"result": "ok"}

        tool = NoSchemaTool()
        result = await tool.run({})

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "CONFIGURATION_ERROR"

    @pytest.mark.asyncio
    async def test_registry_execute_returns_tool_result(self, registry, test_tool):
        """Verify registry.execute returns ToolResult."""
        registry.register(test_tool)

        result = await registry.execute("simple_tool", {"value": 10, "tenant_id": "tenant-test"})

        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["result"] == 20

    @pytest.mark.asyncio
    async def test_registry_execute_returns_error_for_unknown_tool(self, registry):
        """Verify registry returns ToolResult error for unknown tool."""
        result = await registry.execute("unknown_tool", {})

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "TOOL_NOT_FOUND"


class TestCalculationToolsContract:
    """Test calculation tools return structured results."""

    @pytest.mark.asyncio
    async def test_evaluate_formula_returns_tool_result(self):
        """Test EvaluateFormulaTool returns ToolResult."""
        tool = EvaluateFormulaTool()
        result = await tool.run({
            "formula": "x + y",
            "variables": {"x": 10, "y": 20},
        })

        assert isinstance(result, ToolResult)
        validate_tool_result(result)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["result"] == 30

    @pytest.mark.asyncio
    async def test_evaluate_formula_returns_error_on_invalid_formula(self):
        """Test EvaluateFormulaTool returns ToolResult error on invalid formula."""
        tool = EvaluateFormulaTool()
        result = await tool.run({
            "formula": "{x} + {y}",
            "variables": {"x": 10},  # Missing y
        })

        # This should still return a ToolResult (may be success with error field)
        assert isinstance(result, ToolResult)
        # The tool returns EvaluateFormulaOutput with error field set
        if result.status == "success":
            assert result.data is not None
            assert "Missing variables" in result.data.get("error", "")

    @pytest.mark.asyncio
    async def test_evaluate_formula_missing_variables_error_contract(self):
        """Regression: missing variables must return stable structured error payload."""
        tool = EvaluateFormulaTool()
        result = await tool.run({
            "formula": "x + y + z",
            "variables": {"x": 10, "y": 20},
        })

        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["success"] is False
        assert "Missing variables" in result.data["error"]

    @pytest.mark.asyncio
    async def test_evaluate_formula_invalid_variable_name_validation_contract(self):
        """Regression: invalid formula characters should preserve validation error contract."""
        tool = EvaluateFormulaTool()
        result = await tool.run({
            "formula": "x + $y",
            "variables": {"x": 10, "y": 20},
        })

        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "INPUT_VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_calculate_roi_returns_tool_result(self):
        """Test CalculateROITool returns ToolResult."""
        tool = CalculateROITool()
        result = await tool.run({
            "investment": 100000,
            "returns": [30000, 35000, 40000],
            "time_periods": 3,
            "discount_rate": 0.1,
        })

        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data is not None
        assert "simple_roi_percent" in result.data
        assert "npv" in result.data


class TestToolResultTraceId:
    """Test trace_id propagation through tool execution."""

    @pytest.mark.asyncio
    async def test_trace_id_in_success_result(self):
        """Test trace_id appears in success result metadata."""
        class SimpleInput(BaseModel):
            value: int

        class SimpleOutput(BaseModel):
            result: int

        class SimpleTool(BaseTool):
            name = "trace_test_tool"
            input_schema = SimpleInput
            output_schema = SimpleOutput

            async def execute(self, input_data):
                return SimpleOutput(result=input_data.value)

        tool = SimpleTool()
        result = await tool.run({"value": 5}, trace_id="trace-abc-123")

        assert result.metadata is not None
        assert result.metadata.get("trace_id") == "trace-abc-123"

    @pytest.mark.asyncio
    async def test_trace_id_in_error_result(self):
        """Test trace_id appears in error result metadata."""
        class FailingInput(BaseModel):
            should_fail: bool = True

        class FailingOutput(BaseModel):
            result: str

        class FailingTool(BaseTool):
            name = "failing_trace_tool"
            input_schema = FailingInput
            output_schema = FailingOutput

            async def execute(self, input_data):
                raise RuntimeError("Test error")

        tool = FailingTool()
        result = await tool.run({"should_fail": True}, trace_id="trace-error-456")

        assert result.status == "error"
        assert result.error is not None
        assert result.metadata is not None
        assert result.metadata.get("trace_id") == "trace-error-456"


class TestToolResultContractSchema:
    """Validate ToolResult contract schema compliance (Contract §2.4)."""

    def test_success_result_schema(self):
        """Validate success result has all required fields."""
        result = ToolResult.success(
            data={"key": "value"},
            metadata={"trace_id": "trace-123", "execution_time_ms": 50}
        )

        validate_tool_result(result)
        assert result.status == "success"
        assert result.data is not None
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata is not None
        assert result.metadata["trace_id"] == "trace-123"

    def test_error_result_schema(self):
        """Validate error result has all required fields."""
        result = ToolResult.failure(
            code="VALIDATION_FAILED",
            message="Input validation failed",
            details={"field": "email"},
            trace_id="trace-error-456",
            recoverable=True,
        )

        validate_tool_result(result)
        assert result.status == "error"
        assert result.error is not None
        assert result.data is None
        assert result.error["code"] == "VALIDATION_FAILED"
        assert result.error["message"] == "Input validation failed"
        assert result.error["details"] == {"field": "email"}
        assert result.error["recoverable"] is True
        assert result.metadata is not None
        assert result.metadata["trace_id"] == "trace-error-456"

    def test_error_result_no_leakage(self):
        """Ensure error results don't leak sensitive internals."""
        result = ToolResult.failure(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            trace_id="trace-secret-123",
        )

        # User-facing message should be safe
        assert result.error is not None
        assert result.metadata is not None
        assert "traceback" not in result.error["message"].lower()
        assert "exception" not in result.error["message"].lower()
        assert "internal" not in result.error["message"].lower() or "error" in result.error["message"].lower()

        # But trace_id should be in metadata for debugging
        assert result.metadata is not None
        assert result.metadata.get("trace_id") == "trace-secret-123"


class TestToolResultBackwardCompatibility:
    """Test that ToolResult changes maintain backward compatibility where possible."""

    @pytest.mark.asyncio
    async def test_legacy_tool_still_works(self):
        """Test that tools using old patterns still work through BaseTool wrapper."""
        class LegacyInput(BaseModel):
            value: str

        class LegacyOutput(BaseModel):
            result: str

        class LegacyTool(BaseTool):
            name = "legacy_tool"
            input_schema = LegacyInput
            output_schema = LegacyOutput

            async def execute(self, input_data):
                # Old pattern: just return the output model
                return LegacyOutput(result=f"processed: {input_data.value}")

        tool = LegacyTool()
        result = await tool.run({"value": "test"})

        # Should still be wrapped in ToolResult
        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["result"] == "processed: test"


class TestLLMResponseValidation:
    """Test Pydantic validation for LLM responses (Contract §2.5).

    Replaces raw json.loads with structured model validation.
    """

    def test_llm_response_model_validates_correct_json(self):
        """Test that valid LLM JSON response is parsed correctly."""
        from layer4_agents.tools.competitive_tools import (
            LLMDifferenceItem,
            LLMDifferencesResponse,
        )

        valid_json = '''{"differences": [
            {"category": "COST_STRUCTURE", "description": "20% cheaper", "impact_direction": "FAVORS_US", "confidence_score": 0.8}
        ]}'''

        result = LLMDifferencesResponse.model_validate_json(valid_json)
        assert len(result.differences) == 1
        assert result.differences[0].category == "COST_STRUCTURE"
        assert result.differences[0].confidence_score == 0.8

    def test_llm_response_model_handles_invalid_json(self):
        """Test that invalid JSON is handled gracefully."""
        from layer4_agents.tools.competitive_tools import (
            LLMDifferencesResponse,
        )

        # Malformed JSON should raise validation error
        invalid_json = '{"differences": [invalid]}'

        with pytest.raises(Exception):
            LLMDifferencesResponse.model_validate_json(invalid_json)

    def test_llm_response_model_uses_defaults_for_missing_fields(self):
        """Test that missing fields use sensible defaults."""
        from layer4_agents.tools.competitive_tools import (
            LLMDifferenceItem,
        )

        # Partial data should use defaults
        partial = {"description": "Some description"}
        item = LLMDifferenceItem.model_validate(partial)

        assert item.category == "CAPABILITY_TO_OUTCOME"  # default
        assert item.confidence_score == 0.5  # default
        assert item.is_unsupported_claim is False  # default
        assert item.description == "Some description"
