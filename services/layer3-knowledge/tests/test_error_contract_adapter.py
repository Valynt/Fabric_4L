from value_fabric.shared.error_handling.exceptions import NotFoundError

from src.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer3_adapter_maps_shared_exception_to_canonical_error_envelope() -> None:
    exc = NotFoundError(resource_type="entity", resource_id="abc-123")

    body = map_exception_to_contract_detail(exc, request_id="req-l3")

    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "entity not found with id 'abc-123'"
    assert body["error"]["request_id"] == "req-l3"
    assert body["error"]["details"]["resource_id"] == "abc-123"
