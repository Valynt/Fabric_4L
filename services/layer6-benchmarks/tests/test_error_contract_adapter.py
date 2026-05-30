from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

from layer6_benchmarks.adapters.value_fabric_api import map_exception_to_contract_detail


def test_layer6_adapter_maps_shared_exception_to_canonical_error_envelope() -> None:
    exc = ServiceUnavailableError(service="neo4j")

    body = map_exception_to_contract_detail(exc, request_id="req-l6")

    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["message"] == "Service temporarily unavailable"
    assert body["error"]["request_id"] == "req-l6"
    assert body["error"]["details"]["service"] == "neo4j"
