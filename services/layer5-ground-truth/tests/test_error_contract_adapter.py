from value_fabric.shared.error_handling.exceptions import AuthorizationError

from layer5_ground_truth.adapters.value_fabric_api import (
    map_exception_to_http_contract,
    map_exception_to_unhandled_contract,
)


def test_layer5_http_adapter_preserves_custom_http_error_envelope_shape() -> None:
    exc = AuthorizationError(message="forbidden")

    body = map_exception_to_http_contract(exc, request_id="req-l5")

    assert body["error"]["code"] == "AUTHORIZATION_ERROR"
    assert body["error"]["message"] == "forbidden"
    assert body["error"]["request_id"] == "req-l5"
    assert body["error"]["details"] is None


def test_layer5_catch_all_adapter_preserves_unhandled_semantics() -> None:
    body = map_exception_to_unhandled_contract()

    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "unexpected error occurred" in body["error"]["message"]
    assert body["error"]["request_id"] is None
