from value_fabric.shared.error_handling.exceptions import NotFoundError

from src.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer3_adapter_maps_shared_exception_to_current_contract_shape() -> None:
    exc = NotFoundError(resource_type="entity", resource_id="abc-123")

    detail = map_exception_to_contract_detail(exc, request_id="req-l3")

    assert detail["error"] == "NOT_FOUND"
    assert detail["message"] == "entity not found with id 'abc-123'"
    assert detail["request_id"] == "req-l3"
    assert detail["details"]["resource_id"] == "abc-123"
