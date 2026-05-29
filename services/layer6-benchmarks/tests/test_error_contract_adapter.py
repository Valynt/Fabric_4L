from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

from layer6_benchmarks.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer6_adapter_maps_shared_exception_to_current_contract_shape() -> None:
    exc = ServiceUnavailableError(service="neo4j")

    body = map_exception_to_contract_detail(exc, request_id="req-l6")

    # Adapter returns flat structure with error_code, not nested error
    assert body["error_code"] == "ErrorCode.SERVICE_UNAVAILABLE"
    assert body["message"] == "Service temporarily unavailable"
    assert body["request_id"] == "req-l6"
    assert body["details"]["service"] == "neo4j"
