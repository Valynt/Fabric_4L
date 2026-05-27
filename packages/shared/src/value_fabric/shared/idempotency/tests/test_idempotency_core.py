from value_fabric.shared.idempotency import (
    IdempotencyConflictError,
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    InMemoryIdempotencyStore,
    build_request_fingerprint,
)
import time


def test_duplicate_request_returns_stored_response() -> None:
    service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)
    req = IdempotencyRequest(
        tenant_id="tenant-a",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-1",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "a"}),
    )
    service.store_response(req, IdempotencyRecord(status_code=201, body={"id": "a"}, headers={"X-Test": "1"}))
    replay = service.check_replay(req)
    assert replay is not None
    assert replay.status_code == 201
    assert replay.body == {"id": "a"}


def test_payload_mismatch_same_key_raises_conflict() -> None:
    service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)
    first = IdempotencyRequest(
        tenant_id="tenant-a",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-1",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "a"}),
    )
    second = IdempotencyRequest(
        tenant_id="tenant-a",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-1",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "b"}),
    )
    service.store_response(first, IdempotencyRecord(status_code=201, body={"id": "a"}, headers={}))
    try:
        service.check_replay(second)
    except IdempotencyConflictError:
        return
    raise AssertionError("Expected IdempotencyConflictError")


def test_idempotency_key_is_tenant_scoped() -> None:
    service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)
    tenant_a = IdempotencyRequest(
        tenant_id="tenant-a",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-1",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "a"}),
    )
    tenant_b = IdempotencyRequest(
        tenant_id="tenant-b",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-1",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "a"}),
    )
    service.store_response(tenant_a, IdempotencyRecord(status_code=201, body={"id": "a"}, headers={}))
    assert service.check_replay(tenant_b) is None


def test_idempotency_key_expires_after_ttl() -> None:
    service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=1)
    req = IdempotencyRequest(
        tenant_id="tenant-a",
        endpoint_key="POST:/v1/accounts",
        idempotency_key="k-ttl",
        request_fingerprint=build_request_fingerprint("POST", "/v1/accounts", {"id": "a"}),
    )
    service.store_response(req, IdempotencyRecord(status_code=201, body={"id": "a"}, headers={}))
    time.sleep(1.1)
    assert service.check_replay(req) is None
