from value_fabric.shared.error_handling.exceptions import ValidationError

from src.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer4_adapter_maps_shared_exception_to_http_detail_schema() -> None:
    exc = ValidationError(message="bad payload", field="tenant_id")

    detail = map_exception_to_contract_detail(exc, request_id="req-l4")

    assert detail["error_code"] == "VALIDATION_ERROR"
    assert detail["message"] == "bad payload"
    assert detail["request_id"] == "req-l4"
    assert detail["correlation_id"] == "req-l4"
    assert detail["details"]["field"] == "tenant_id"
