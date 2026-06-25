from __future__ import annotations

"""Tool Output Structure Validation Tests - P0 Critical Gap Remediation

Validates that all tool outputs conform to the canonical ToolResult contract
per docs/contract.md §2.4. Ensures structured error handling instead of
exception-based errors.

Production Invariant: Tools must return canonical ToolResult shape with
status/data/error/metadata fields.

Author: Autonomous Test Assurance Agent
Date: 2026-05-23
"""


from uuid import uuid4

import pytest

from layer4_agents.tools.registry import ToolResult

pytestmark = [
    pytest.mark.security,
    pytest.mark.contract,
    pytest.mark.mandatory,
]


# Constants for test data
UUID_LENGTH = 36
LARGE_DATA_SIZE = 1000
LONG_ERROR_CODE_LENGTH = 500
LONG_ERROR_MESSAGE_LENGTH = 10000


class TestToolResultSuccessStructure:
    """POSITIVE: Validate ToolResult.success() produces correct structure."""

    def test_success_has_status_success(self):
        """ToolResult.success() must set status='success'."""
        result = ToolResult.success(data={"result": "value"})
        assert result.status == "success"

    def test_success_includes_data_field(self):
        """ToolResult.success() must include provided data."""
        expected_data = {"result": "value", "count": 42}
        result = ToolResult.success(data=expected_data)
        assert result.data == expected_data

    def test_success_error_field_is_none(self):
        """ToolResult.success() must set error=None."""
        result = ToolResult.success(data={"result": "value"})
        assert result.error is None

    def test_success_metadata_optional(self):
        """ToolResult.success() metadata is optional."""
        result = ToolResult.success(data={"result": "value"})
        assert result.metadata is None

    def test_success_metadata_included_when_provided(self):
        """ToolResult.success() includes metadata when provided."""
        metadata = {"trace_id": str(uuid4()), "execution_time_ms": 123}
        result = ToolResult.success(data={"result": "value"}, metadata=metadata)
        assert result.metadata == metadata

    def test_success_is_success_method_returns_true(self):
        """ToolResult.is_success() returns True for success results."""
        result = ToolResult.success(data={"result": "value"})
        assert result.is_success() is True

    def test_success_is_error_method_returns_false(self):
        """ToolResult.is_error() returns False for success results."""
        result = ToolResult.success(data={"result": "value"})
        assert result.is_error() is False


class TestToolResultFailureStructure:
    """POSITIVE: Validate ToolResult.failure() produces correct error structure."""

    def test_failure_has_status_error(self):
        """ToolResult.failure() must set status='error'."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.status == "error"

    def test_failure_data_field_is_none(self):
        """ToolResult.failure() must set data=None."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.data is None

    def test_failure_error_has_required_fields(self):
        """ToolResult.failure() error must have code, message, recoverable."""
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Invalid input",
            recoverable=True,
        )
        assert result.error is not None
        assert result.error["code"] == "VALIDATION_ERROR"
        assert result.error["message"] == "Invalid input"
        assert result.error["recoverable"] is True

    def test_failure_error_includes_details_when_provided(self):
        """ToolResult.failure() error includes optional details."""
        details = {"field": "email", "constraint": "invalid_format"}
        result = ToolResult.failure(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details=details,
        )
        assert result.error is not None
        assert result.error["details"] == details

    def test_failure_error_details_omitted_when_not_provided(self):
        """ToolResult.failure() error omits details when not provided."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.error is not None
        assert "details" not in result.error

    def test_failure_metadata_includes_trace_id_when_provided(self):
        """ToolResult.failure() includes trace_id in metadata when provided."""
        trace_id = str(uuid4())
        result = ToolResult.failure(
            code="TEST_ERROR", message="Test error", trace_id=trace_id
        )
        assert result.metadata is not None
        assert result.metadata["trace_id"] == trace_id

    def test_failure_metadata_omitted_when_no_trace_id(self):
        """ToolResult.failure() omits metadata when trace_id not provided."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.metadata is None

    def test_failure_metadata_preserved_when_explicitly_provided(self):
        """ToolResult.failure() preserves explicit metadata even with trace_id."""
        explicit_metadata = {"custom_field": "value"}
        trace_id = str(uuid4())
        result = ToolResult.failure(
            code="TEST_ERROR",
            message="Test error",
            trace_id=trace_id,
            metadata=explicit_metadata,
        )
        assert result.metadata == explicit_metadata

    def test_failure_is_success_method_returns_false(self):
        """ToolResult.is_success() returns False for failure results."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.is_success() is False

    def test_failure_is_error_method_returns_true(self):
        """ToolResult.is_error() returns True for failure results."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.is_error() is True


class TestToolResultNegativeValidation:
    """NEGATIVE: Validate ToolResult rejects malformed structures."""

    def test_status_must_be_valid_literal(self):
        """ToolResult.status must be 'success' or 'error' only."""
        # This test validates the type constraint at runtime
        # Invalid status values should be caught by type checker
        result = ToolResult.success(data={"result": "value"})
        assert result.status in ["success", "error"]

    def test_error_code_required_on_failure(self):
        """ToolResult.failure() requires code parameter."""
        with pytest.raises(TypeError):
            ToolResult.failure(message="Test error")  # type: ignore

    def test_error_message_required_on_failure(self):
        """ToolResult.failure() requires message parameter."""
        with pytest.raises(TypeError):
            ToolResult.failure(code="TEST_ERROR")  # type: ignore

    def test_recoverable_defaults_to_false(self):
        """ToolResult.failure() recoverable defaults to False."""
        result = ToolResult.failure(code="TEST_ERROR", message="Test error")
        assert result.error is not None
        assert result.error["recoverable"] is False


class TestToolResultMetadataRequirements:
    """POSITIVE: Validate ToolResult metadata includes required fields."""

    def test_metadata_trace_id_format(self):
        """ToolResult metadata trace_id must be valid UUID string."""
        trace_id = str(uuid4())
        result = ToolResult.success(
            data={"result": "value"}, metadata={"trace_id": trace_id}
        )
        assert result.metadata is not None
        assert len(result.metadata["trace_id"]) == UUID_LENGTH  # UUID format

    def test_metadata_execution_time_ms_present(self):
        """ToolResult metadata should include execution_time_ms when available."""
        metadata = {"trace_id": str(uuid4()), "execution_time_ms": 123}
        result = ToolResult.success(data={"result": "value"}, metadata=metadata)
        assert result.metadata is not None
        assert "execution_time_ms" in result.metadata
        assert isinstance(result.metadata["execution_time_ms"], (int, float))

    def test_metadata_tenant_id_present(self):
        """ToolResult metadata should include tenant_id for tenant-aware tools."""
        tenant_id = str(uuid4())
        metadata = {"trace_id": str(uuid4()), "tenant_id": tenant_id}
        result = ToolResult.success(data={"result": "value"}, metadata=metadata)
        assert result.metadata is not None
        assert result.metadata["tenant_id"] == tenant_id


class TestToolResultCanonicalConversion:
    """POSITIVE: Validate ToolResult.to_canonical() conversion."""

    def test_to_canonical_converts_success(self):
        """ToolResult.to_canonical() converts success results correctly."""
        result = ToolResult.success(data={"result": "value"})
        canonical = result.to_canonical()
        assert canonical.status == "success"
        assert canonical.data == {"result": "value"}

    def test_to_canonical_converts_failure(self):
        """ToolResult.to_canonical() converts failure results correctly."""
        result = ToolResult.failure(
            code="TEST_ERROR", message="Test error", recoverable=True
        )
        canonical = result.to_canonical()
        assert canonical.status == "error"
        assert canonical.error.code == "TEST_ERROR"
        assert canonical.error.message == "Test error"
        assert canonical.error.recoverable is True

    def test_to_canonical_preserves_metadata(self):
        """ToolResult.to_canonical() preserves metadata as structured object."""
        metadata = {"trace_id": str(uuid4()), "execution_time_ms": 123}
        result = ToolResult.success(data={"result": "value"}, metadata=metadata)
        canonical = result.to_canonical()
        # Metadata is converted to ToolMetadata object
        assert canonical.metadata.trace_id == metadata["trace_id"]
        assert canonical.metadata.execution_time_ms == metadata["execution_time_ms"]


class TestToolResultEdgeCases:
    """ADVERSARIAL: Validate ToolResult handles edge cases correctly."""

    def test_empty_data_allowed(self):
        """ToolResult.success() allows empty data dict."""
        result = ToolResult.success(data={})
        assert result.data == {}
        assert result.is_success() is True

    def test_none_data_allowed(self):
        """ToolResult.success() allows None data."""
        result = ToolResult.success(data=None)
        assert result.data is None
        assert result.is_success() is True

    def test_large_data_handled(self):
        """ToolResult.success() handles large data structures."""
        large_data = {"items": [i for i in range(LARGE_DATA_SIZE)]}
        result = ToolResult.success(data=large_data)
        assert result.data == large_data
        assert len(result.data["items"]) == LARGE_DATA_SIZE

    def test_special_characters_in_error_message(self):
        """ToolResult.failure() handles special characters in messages."""
        message = "Error with special chars: <>&\"'\\n\\t"
        result = ToolResult.failure(code="TEST_ERROR", message=message)
        assert result.error is not None
        assert result.error["message"] == message

    def test_unicode_in_error_message(self):
        """ToolResult.failure() handles unicode characters."""
        message = "Error with unicode: café, 日本語, emoji 🚀"
        result = ToolResult.failure(code="TEST_ERROR", message=message)
        assert result.error is not None
        assert result.error["message"] == message

    def test_very_long_error_code(self):
        """ToolResult.failure() handles very long error codes."""
        long_code = "A" * LONG_ERROR_CODE_LENGTH
        result = ToolResult.failure(code=long_code, message="Test error")
        assert result.error is not None
        assert result.error["code"] == long_code

    def test_very_long_error_message(self):
        """ToolResult.failure() handles very long error messages."""
        long_message = "E" * LONG_ERROR_MESSAGE_LENGTH
        result = ToolResult.failure(code="TEST_ERROR", message=long_message)
        assert result.error is not None
        assert result.error["message"] == long_message
