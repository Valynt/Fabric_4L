from api.exception_mapping import map_exception_to_http_error
from api.exceptions import (
    ContractViolationError,
    DatabaseError,
    SearchError,
    TenantAccessError,
    ValidationError,
)


def test_validation_error_maps_to_422_with_context():
    exc = ValidationError("bad input")
    err = map_exception_to_http_error(exc, context={"tenant": "t1", "endpoint": "/v1/entities", "operation": "list"})
    assert err.status_code == 422
    assert err.detail["code"] == "VALIDATION_ERROR"
    assert err.detail["context"]["tenant"] == "t1"


def test_database_error_maps_to_503():
    exc = DatabaseError("db down")
    err = map_exception_to_http_error(exc, context={"tenant": "t1", "endpoint": "/v1/models", "operation": "read"})
    assert err.status_code == 503
    assert err.detail["code"] == "DEPENDENCY_UNAVAILABLE"


def test_search_error_maps_to_502():
    exc = SearchError("bad gateway")
    err = map_exception_to_http_error(exc, context={"tenant": "t1", "endpoint": "/v1/search", "operation": "search"})
    assert err.status_code == 502
    assert err.detail["code"] == "SEARCH_BACKEND_ERROR"


def test_tenant_access_error_maps_to_403():
    exc = TenantAccessError()
    err = map_exception_to_http_error(exc, context={"tenant": "unknown", "endpoint": "/v1/entities", "operation": "list"})
    assert err.status_code == 403
    assert err.detail["code"] == "TENANT_ACCESS_DENIED"


def test_timeout_maps_to_504():
    err = map_exception_to_http_error(TimeoutError("timed out"), context={"tenant": "t1", "endpoint": "/v1/search", "operation": "query"})
    assert err.status_code == 504
    assert err.detail["code"] == "UPSTREAM_TIMEOUT"


def test_contract_violation_maps_to_500_contract_code():
    err = map_exception_to_http_error(ContractViolationError("bad shape"), context={"tenant": "t1", "endpoint": "/v1/query", "operation": "graph_rag"})
    assert err.status_code == 500
    assert err.detail["code"] == "CONTRACT_VIOLATION"
