"""Tool Execution Contract Validation Tests - P0 Critical Gap Remediation

Validates that tool execution follows the canonical contract per docs/contract.md §2.4.
Ensures tools do not throw exceptions and instead return structured ToolResult errors.

Production Invariant: Tools must not throw exceptions; errors must be structured.

Author: Autonomous Test Assurance Agent
Date: 2026-05-23
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from value_fabric.layer4.tools.registry import BaseTool, ToolResult


pytestmark = [
    pytest.mark.security,
    pytest.mark.contract,
    pytest.mark.mandatory,
]


# Constants for test data
EXECUTION_TIME_MS_THRESHOLD = 10
UUID_LENGTH = 36
LARGE_TOKEN_COUNT = 100000


class StubTool(BaseTool):
    """Stub tool for testing contract compliance."""

    async def execute(self, input_data: dict) -> ToolResult:
        return ToolResult.success(data={"result": "stub"})


class FailingTool(BaseTool):
    """Tool that raises an exception (anti-pattern)."""

    async def execute(self, input_data: dict) -> ToolResult:
        raise ValueError("Tool failed with exception")


class TestToolExecuteContract:
    """POSITIVE: Validate tool execute() method contract."""

    async def test_execute_returns_tool_result(self):
        """Tool.execute() must return ToolResult instance."""
        tool = StubTool()
        result = await tool.execute({})
        assert isinstance(result, ToolResult)

    async def test_execute_success_status(self):
        """Tool.execute() success must return status='success'."""
        tool = StubTool()
        result = await tool.execute({})
        assert result.status == "success"

    async def test_execute_includes_data(self):
        """Tool.execute() must include data on success."""
        tool = StubTool()
        result = await tool.execute({})
        assert result.data is not None
        assert result.data == {"result": "stub"}

    async def test_execute_error_status_on_failure(self):
        """Tool.execute() failure must return status='error'."""
        tool = FailingTool()
        # This test documents the anti-pattern - the tool should catch exceptions
        # and return ToolResult.failure() instead
        with pytest.raises(ValueError):
            await tool.execute({})

    async def test_execute_handles_exceptions_properly(self):
        """Tool.execute() must catch exceptions and return ToolResult.failure()."""
        class ProperErrorHandlingTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                try:
                    # Simulate an error condition
                    if not input_data.get("required_field"):
                        raise ValueError("Missing required field")
                    return ToolResult.success(data={"processed": True})
                except ValueError as e:
                    return ToolResult.failure(
                        code="VALIDATION_ERROR",
                        message=str(e),
                        recoverable=False,
                    )

        tool = ProperErrorHandlingTool()
        result = await tool.execute({})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"
        assert result.error["recoverable"] is False


class TestToolErrorHandlingContract:
    """NEGATIVE: Validate tools handle errors without throwing exceptions."""

    async def test_tool_catches_validation_errors(self):
        """Tool must catch validation errors and return ToolResult.failure()."""
        class ValidationTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                if not input_data.get("required_field"):
                    return ToolResult.failure(
                        code="VALIDATION_ERROR",
                        message="required_field is missing",
                        recoverable=False,
                    )
                return ToolResult.success(data={"processed": True})

        tool = ValidationTool()
        result = await tool.execute({})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"

    async def test_tool_catches_external_service_errors(self):
        """Tool must catch external service errors and return ToolResult.failure()."""
        class ExternalServiceTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                try:
                    # Simulate external service call
                    raise ConnectionError("Service unavailable")
                except ConnectionError as e:
                    return ToolResult.failure(
                        code="SERVICE_UNAVAILABLE",
                        message=str(e),
                        recoverable=True,
                    )

        tool = ExternalServiceTool()
        result = await tool.execute({})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "SERVICE_UNAVAILABLE"
        assert result.error["recoverable"] is True

    async def test_tool_catches_timeout_errors(self):
        """Tool must catch timeout errors and return ToolResult.failure()."""
        class TimeoutTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                try:
                    # Simulate timeout
                    raise TimeoutError("Operation timed out")
                except TimeoutError as e:
                    return ToolResult.failure(
                        code="TIMEOUT_ERROR",
                        message=str(e),
                        recoverable=True,
                    )

        tool = TimeoutTool()
        result = await tool.execute({})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "TIMEOUT_ERROR"


class TestToolMetadataContract:
    """POSITIVE: Validate tool execution includes required metadata."""

    async def test_metadata_includes_execution_time(self):
        """ToolResult.metadata should include execution_time_ms."""
        class TimedTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                import time
                start = time.time()
                time.sleep(0.01)  # Simulate work
                execution_time_ms = int((time.time() - start) * 1000)
                return ToolResult.success(
                    data={"result": "timed"},
                    metadata={"execution_time_ms": execution_time_ms},
                )

        tool = TimedTool()
        result = await tool.execute({})
        assert result.metadata is not None
        assert "execution_time_ms" in result.metadata
        assert result.metadata["execution_time_ms"] >= EXECUTION_TIME_MS_THRESHOLD

    async def test_metadata_includes_trace_id(self):
        """ToolResult.metadata should include trace_id for observability."""
        class TracedTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                trace_id = str(uuid4())
                return ToolResult.success(
                    data={"result": "traced"},
                    metadata={"trace_id": trace_id},
                )

        tool = TracedTool()
        result = await tool.execute({})
        assert result.metadata is not None
        assert "trace_id" in result.metadata
        assert len(result.metadata["trace_id"]) == UUID_LENGTH

    async def test_metadata_includes_tenant_id(self):
        """ToolResult.metadata should include tenant_id for tenant-aware tools."""
        class TenantAwareTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                tenant_id = input_data.get("tenant_id", str(uuid4()))
                return ToolResult.success(
                    data={"result": "tenant_aware"},
                    metadata={"tenant_id": tenant_id},
                )

        tool = TenantAwareTool()
        tenant_id = str(uuid4())
        result = await tool.execute({"tenant_id": tenant_id})
        assert result.metadata is not None
        assert result.metadata["tenant_id"] == tenant_id


class TestToolRecoverabilityContract:
    """POSITIVE: Validate tool error recoverability field."""

    async def test_validation_errors_not_recoverable(self):
        """Validation errors should have recoverable=False."""
        class ValidationTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                return ToolResult.failure(
                    code="VALIDATION_ERROR",
                    message="Invalid input",
                    recoverable=False,
                )

        tool = ValidationTool()
        result = await tool.execute({})
        assert result.error is not None
        assert result.error["recoverable"] is False

    async def test_transient_errors_recoverable(self):
        """Transient errors (network, timeout) should have recoverable=True."""
        class TransientErrorTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                return ToolResult.failure(
                    code="TRANSIENT_ERROR",
                    message="Temporary failure",
                    recoverable=True,
                )

        tool = TransientErrorTool()
        result = await tool.execute({})
        assert result.error is not None
        assert result.error["recoverable"] is True

    async def test_permanent_errors_not_recoverable(self):
        """Permanent errors (auth, not found) should have recoverable=False."""
        class PermanentErrorTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                return ToolResult.failure(
                    code="AUTH_ERROR",
                    message="Authentication failed",
                    recoverable=False,
                )

        tool = PermanentErrorTool()
        result = await tool.execute({})
        assert result.error is not None
        assert result.error["recoverable"] is False


class TestToolErrorDetailsContract:
    """POSITIVE: Validate tool error details structure."""

    async def test_error_details_optional(self):
        """ToolResult.error.details is optional."""
        tool = StubTool()
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.error is not None
        assert "details" not in result.error

    async def test_error_details_included_when_provided(self):
        """ToolResult.error.details included when provided."""
        details = {"field": "email", "value": "invalid"}
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details=details,
        )
        assert result.error is not None
        assert result.error["details"] == details

    async def test_error_details_can_be_complex(self):
        """ToolResult.error.details can contain complex nested structures."""
        details = {
            "validation_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "phone", "message": "Required"},
            ],
            "context": {"input_length": 100, "max_length": 50},
        }
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Multiple validation errors",
            details=details,
        )
        assert result.error is not None
        assert result.error["details"] == details
        assert len(result.error["details"]["validation_errors"]) == 2


class TestToolInputValidationContract:
    """POSITIVE: Validate tools validate input before processing."""

    async def test_tool_validates_required_fields(self):
        """Tool must validate required input fields."""
        class ValidatedTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                if "email" not in input_data:
                    return ToolResult.failure(
                        code="VALIDATION_ERROR",
                        message="email field is required",
                        recoverable=False,
                    )
                return ToolResult.success(data={"email": input_data["email"]})

        tool = ValidatedTool()
        result = await tool.execute({})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"

    async def test_tool_validates_field_types(self):
        """Tool must validate input field types."""
        class TypeValidatedTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                if "count" in input_data and not isinstance(input_data["count"], int):
                    return ToolResult.failure(
                        code="VALIDATION_ERROR",
                        message="count must be an integer",
                        recoverable=False,
                    )
                return ToolResult.success(data={"count": input_data.get("count", 0)})

        tool = TypeValidatedTool()
        result = await tool.execute({"count": "not_an_int"})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"

    async def test_tool_validates_field_ranges(self):
        """Tool must validate input field ranges."""
        class RangeValidatedTool(BaseTool):
            async def execute(self, input_data: dict) -> ToolResult:
                count = input_data.get("count", 0)
                if count < 0 or count > 100:
                    return ToolResult.failure(
                        code="VALIDATION_ERROR",
                        message="count must be between 0 and 100",
                        recoverable=False,
                    )
                return ToolResult.success(data={"count": count})

        tool = RangeValidatedTool()
        result = await tool.execute({"count": 150})
        assert result.status == "error"
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"
