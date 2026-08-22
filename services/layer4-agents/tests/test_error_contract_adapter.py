from value_fabric.shared.error_handling.exceptions import ValidationError

from layer4_agents.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer4_adapter_maps_shared_exception_to_canonical_error_envelope() -> None:
    exc = ValidationError(message="bad payload", field="tenant_id")

    body = map_exception_to_contract_detail(exc, request_id="req-l4")

    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "bad payload"
    assert body["error"]["request_id"] == "req-l4"
    assert body["error"]["details"]["field"] == "tenant_id"
