from __future__ import annotations

import pytest
from value_fabric.shared.error_handling.exceptions import BadRequestError

from layer4_agents.api.routes.billing import _raise_billing_bad_request


class TestBillingRouteErrorSanitization:
    """Ensure billing routes never leak raw exception text to clients (ban_str_e)."""

    def test_raise_billing_bad_request_masks_original_value_error_message(self) -> None:
        """The helper must raise BadRequestError with a safe message and stable code."""
        original_message = "internal database connection postgres://secret"
        exc = ValueError(original_message)

        with pytest.raises(BadRequestError) as exc_info:
            _raise_billing_bad_request(exc)

        assert exc_info.value.message == "Invalid billing request."
        assert exc_info.value.details == {"code": "BILLING_VALIDATION_ERROR"}
        assert original_message not in exc_info.value.message
        if exc_info.value.details:
            assert original_message not in str(exc_info.value.details)

    def test_raise_billing_bad_request_supports_custom_safe_message(self) -> None:
        """The helper may be called with a caller-supplied safe message."""
        exc = ValueError("internal failure")

        with pytest.raises(BadRequestError) as exc_info:
            _raise_billing_bad_request(exc, message="Invalid webhook payload")

        assert exc_info.value.message == "Invalid webhook payload"
        assert exc_info.value.details == {"code": "BILLING_VALIDATION_ERROR"}
