"""Contract-focused tests for synchronous and asynchronous SDK clients."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from valuefabric.auth import APIKeyAuth, JWTAuth
from valuefabric.client import JSONValue, ValueFabricClient
from valuefabric.errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    ValueFabricError,
)
from valuefabric.errors import (
    ConnectionError as SDKConnectionError,
)
from valuefabric.errors import (
    ValidationError as SDKValidationError,
)
from valuefabric.models import (
    APIKey,
    APIKeyCreateResult,
    FeatureFlag,
    HealthResponse,
    ModelVersion,
    Tenant,
    User,
    WorkflowCreateResponse,
    WorkflowListResponse,
    WorkflowStatus,
    WorkflowTypeInfo,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"
MODEL_ID = "44444444-4444-4444-4444-444444444444"
BASE_URL = "https://api.example.com"


class RecordingTransport:
    """Deterministic transport that records requests and never uses the network."""

    def __init__(
        self,
        responder: Callable[[httpx.Request], httpx.Response],
    ) -> None:
        self.requests: list[httpx.Request] = []
        self._responder = responder

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responder(request)


def json_response(
    request: httpx.Request,
    payload: JSONValue,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        headers=headers,
        request=request,
    )


async def make_client(
    responder: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "sdk-secret",
) -> tuple[ValueFabricClient, RecordingTransport]:
    recorder = RecordingTransport(responder)
    transport = httpx.MockTransport(recorder)
    client = ValueFabricClient(BASE_URL, api_key=api_key)
    client.close()
    await client.aclose()
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    client._sync_client = httpx.Client(
        base_url=BASE_URL, headers=headers, auth=APIKeyAuth(api_key), transport=transport
    )
    client._async_client = httpx.AsyncClient(
        base_url=BASE_URL, headers=headers, auth=APIKeyAuth(api_key), transport=transport
    )
    return client, recorder


def api_key_payload() -> dict[str, JSONValue]:
    return {
        "key_id": "vf_abc",
        "tenant_id": TENANT_ID,
        "name": "test-key",
        "prefix": "vf_ab",
        "role": "analyst",
        "permissions": [],
        "enabled": True,
        "created_at": "2024-01-01T00:00:00Z",
    }


def workflow_payload() -> dict[str, JSONValue]:
    return {
        "id": "wf-1",
        "workflow_type": "roi_calculator",
        "status": "running",
        "current_state": "calculate",
        "current_node": "calculate",
        "progress": 50.0,
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": None,
        "error_count": 0,
        "has_output": False,
        "results": None,
        "tenant_id": TENANT_ID,
        "user_id": "user-1",
        "priority": 1,
        "scheduler_status": "running",
    }


def tenant_payload() -> dict[str, JSONValue]:
    return {
        "id": TENANT_ID,
        "name": "Acme",
        "slug": "acme",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_list_api_keys_uses_canonical_active_only_query(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, [api_key_payload()])

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await client.alist_api_keys(active_only=False)
        else:
            result = client.list_api_keys(active_only=False)

        assert result == [APIKey.model_validate(api_key_payload())]
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == "/v1/api-keys"
        assert dict(recorder.requests[0].url.params) == {"active_only": "false"}
        assert recorder.requests[0].headers["x-api-key"] == "sdk-secret"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_list_workflows_uses_canonical_page_query(
    asynchronous: bool,
) -> None:
    payload: JSONValue = {
        "items": [workflow_payload()],
        "total": 1,
        "limit": 25,
        "offset": 5,
        "has_more": False,
    }

    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, payload)

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await client.alist_workflows(
                limit=25,
                offset=5,
                workflow_type="roi_calculator",
                include_completed=False,
            )
        else:
            result = client.list_workflows(
                limit=25,
                offset=5,
                workflow_type="roi_calculator",
                include_completed=False,
            )

        assert result == WorkflowListResponse.model_validate(payload)
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == "/v1/workflows"
        assert dict(recorder.requests[0].url.params) == {
            "limit": "25",
            "offset": "5",
            "type": "roi_calculator",
            "include_completed": "false",
        }
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_list_active_workflows_deserializes_canonical_page(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(
            request,
            {
                "items": [workflow_payload()],
                "total": 1,
                "limit": 100,
                "offset": 0,
                "has_more": False,
            },
        )

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await client.alist_active_workflows()
        else:
            result = client.list_active_workflows()

        assert result == WorkflowListResponse.model_validate(
            {
                "items": [workflow_payload()],
                "total": 1,
                "limit": 100,
                "offset": 0,
                "has_more": False,
            }
        )
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == "/v1/workflows/active"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_get_workflow_deserializes_public_status_fields(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, workflow_payload())

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await client.aget_workflow("wf-1")
        else:
            result = client.get_workflow("wf-1")

        assert result == WorkflowStatus.model_validate(workflow_payload())
        assert result.id == "wf-1"
        assert result.progress == 50.0
        assert recorder.requests[0].url.path == "/v1/workflows/wf-1"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_execute_workflow_omits_caller_identity_and_returns_typed_response(
    asynchronous: bool,
) -> None:
    inputs = {"custom_data": {"revenue": 100}}

    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(
            request,
            {
                "workflow_instance_id": "wf-2",
                "status": "scheduled",
                "estimated_duration_seconds": 300,
            },
            status_code=201,
        )

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await client.aexecute_workflow(
                "roi_calculator",
                inputs=inputs,
                priority="HIGH",
                workflow_id="wf-2",
            )
        else:
            result = client.execute_workflow(
                "roi_calculator",
                inputs=inputs,
                priority="HIGH",
                workflow_id="wf-2",
            )

        assert result == WorkflowCreateResponse(
            workflow_instance_id="wf-2",
            status="scheduled",
            estimated_duration_seconds=300,
        )
        assert json.loads(recorder.requests[0].content) == {
            "workflow_type": "roi_calculator",
            "inputs": inputs,
            "priority": "HIGH",
            "workflow_id": "wf-2",
        }
        assert inputs == {"custom_data": {"revenue": 100}}
        assert "x-tenant-id" not in recorder.requests[0].headers
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_get_tenant_request_and_model(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, tenant_payload())

    client, recorder = await make_client(responder)
    try:
        result = (
            await client.aget_tenant(TENANT_ID) if asynchronous else client.get_tenant(TENANT_ID)
        )
        assert result == Tenant.model_validate(tenant_payload())
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == f"/v1/tenants/{TENANT_ID}"
    finally:
        client.close()
        await client.aclose()


def model_payload() -> dict[str, JSONValue]:
    return {
        "id": MODEL_ID,
        "tenant_id": TENANT_ID,
        "provider": "openai",
        "model_name": "gpt-4",
        "model_version": "1.0",
        "stage": "staging",
        "config": {},
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_list_models_request_and_model(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, [model_payload()])

    client, recorder = await make_client(responder)
    try:
        result = (
            await client.alist_models(stage="staging")
            if asynchronous
            else client.list_models(stage="staging")
        )
        assert result == [ModelVersion.model_validate(model_payload())]
        assert recorder.requests[0].url.path == "/v1/models"
        assert dict(recorder.requests[0].url.params) == {"stage": "staging"}
    finally:
        client.close()
        await client.aclose()


def feature_flag_payload() -> dict[str, JSONValue]:
    return {
        "id": "55555555-5555-5555-5555-555555555555",
        "tenant_id": TENANT_ID,
        "flag_key": "new_ui",
        "enabled": False,
        "rollout_percentage": 25,
        "description": "Controlled rollout",
        "metadata": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_set_feature_flag_request_and_model(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, feature_flag_payload())

    client, recorder = await make_client(responder)
    try:
        result = (
            await client.aset_feature_flag(
                "new_ui",
                False,
                rollout_percentage=25,
                description="Controlled rollout",
            )
            if asynchronous
            else client.set_feature_flag(
                "new_ui",
                False,
                rollout_percentage=25,
                description="Controlled rollout",
            )
        )
        assert result == FeatureFlag.model_validate(feature_flag_payload())
        assert recorder.requests[0].method == "PUT"
        assert recorder.requests[0].url.path == "/v1/feature-flags/new_ui"
        assert json.loads(recorder.requests[0].content) == {
            "enabled": False,
            "rollout_percentage": 25,
            "description": "Controlled rollout",
        }
    finally:
        client.close()
        await client.aclose()


def health_payload() -> dict[str, JSONValue]:
    return {
        "status": "healthy",
        "service": "layer4-agents",
        "version": "0.2.0",
        "timestamp": "2024-01-01T00:00:00Z",
        "executor_ready": True,
        "uptime_seconds": 123.0,
        "dependencies": [],
        "metrics": {},
    }


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_health_request_and_model(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, health_payload())

    client, recorder = await make_client(responder)
    try:
        result = await client.ahealth() if asynchronous else client.health()
        assert result == HealthResponse.model_validate(health_payload())
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == "/health"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (400, SDKValidationError),
        (401, AuthenticationError),
        (403, APIError),
        (404, NotFoundError),
        (409, APIError),
        (422, APIError),
        (429, RateLimitError),
        (500, APIError),
        (503, APIError),
    ],
)
@pytest.mark.asyncio
async def test_http_error_mapping_preserves_safe_context(
    asynchronous: bool,
    status_code: int,
    exception_type: type[ValueFabricError],
) -> None:
    body: JSONValue = {
        "detail": f"failure-{status_code}",
        "api_key": "server-secret",
        "nested": {"authorization": "Bearer server-token"},
    }

    def responder(request: httpx.Request) -> httpx.Response:
        headers = {"retry-after": "7"} if status_code == 429 else None
        return json_response(request, body, status_code=status_code, headers=headers)

    client, _ = await make_client(responder, api_key="must-not-leak")
    try:
        with pytest.raises(exception_type) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        error = captured.value
        assert error.response_body == {
            "detail": f"failure-{status_code}",
            "api_key": "[REDACTED]",
            "nested": {"authorization": "[REDACTED]"},
        }
        assert error.status_code == status_code
        assert error.endpoint == "/health"
        assert error.__cause__ is None
        assert "must-not-leak" not in str(error)
        assert "server-secret" not in repr(error.response_body)
        assert "server-token" not in repr(error.response_body)
        if isinstance(error, RateLimitError):
            assert error.retry_after == 7
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_transport_errors_map_to_connection_error(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client, _ = await make_client(responder, api_key="must-not-leak")
    try:
        with pytest.raises(SDKConnectionError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert "connection refused" in str(captured.value)
        assert captured.value.endpoint == "/health"
        assert captured.value.__cause__ is None
        assert "must-not-leak" not in str(captured.value)
    finally:
        client.close()
        await client.aclose()


USER_PAYLOAD = {
    "id": "22222222-2222-2222-2222-222222222222",
    "tenant_id": TENANT_ID,
    "email": "alice@example.com",
    "display_name": "Alice",
    "role": "analyst",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}
API_KEY_CREATE_PAYLOAD = {
    "key_id": "vf_new",
    "tenant_id": TENANT_ID,
    "name": "automation",
    "api_key": "vf_new_secret",
    "prefix": "vf_ne",
    "role": "analyst",
    "permissions": ["read"],
    "expires_at": "2027-01-01T00:00:00Z",
    "rate_limit_per_minute": 60,
    "created_at": "2024-01-01T00:00:00Z",
}
WORKFLOW_TYPES_PAYLOAD = {
    "workflows": [
        {
            "type": "roi_calculator",
            "name": "ROI Calculator",
            "description": "Calculate ROI",
        }
    ]
}

PUBLIC_METHOD_CASES = [
    pytest.param(
        "list_tenants",
        "alist_tenants",
        (),
        {"status": "active", "limit": 25, "offset": 5},
        [tenant_payload()],
        [Tenant.model_validate(tenant_payload())],
        "GET",
        "/v1/tenants",
        {"status": "active", "limit": "25", "offset": "5"},
        None,
        id="list-tenants",
    ),
    pytest.param(
        "list_users",
        "alist_users",
        (),
        {"limit": 20, "offset": 4},
        [USER_PAYLOAD],
        [User.model_validate(USER_PAYLOAD)],
        "GET",
        "/v1/users",
        {"limit": "20", "offset": "4"},
        None,
        id="list-users",
    ),
    pytest.param(
        "invite_user",
        "ainvite_user",
        ("alice@example.com", "analyst"),
        {"display_name": "Alice"},
        {**USER_PAYLOAD, "status": "invited"},
        User.model_validate({**USER_PAYLOAD, "status": "invited"}),
        "POST",
        "/v1/users/invite",
        {},
        {"email": "alice@example.com", "role": "analyst", "display_name": "Alice"},
        id="invite-user",
    ),
    pytest.param(
        "create_api_key",
        "acreate_api_key",
        ("automation", "analyst"),
        {"expires_at": "2027-01-01T00:00:00Z", "rate_limit_per_minute": 60},
        API_KEY_CREATE_PAYLOAD,
        APIKeyCreateResult.model_validate(API_KEY_CREATE_PAYLOAD),
        "POST",
        "/v1/api-keys",
        {},
        {
            "name": "automation",
            "role": "analyst",
            "expires_at": "2027-01-01T00:00:00Z",
            "rate_limit_per_minute": 60,
        },
        id="create-api-key",
    ),
    pytest.param(
        "list_workflow_types",
        "alist_workflow_types",
        (),
        {},
        WORKFLOW_TYPES_PAYLOAD,
        [
            WorkflowTypeInfo(
                type="roi_calculator", name="ROI Calculator", description="Calculate ROI"
            )
        ],
        "GET",
        "/v1/workflows/types",
        {},
        None,
        id="list-workflows",
    ),
    pytest.param(
        "promote_model",
        "apromote_model",
        (MODEL_ID, "staging"),
        {"reason": "evaluation passed"},
        model_payload(),
        ModelVersion.model_validate(model_payload()),
        "POST",
        f"/v1/models/{MODEL_ID}/promote",
        {},
        {"to_stage": "staging", "reason": "evaluation passed"},
        id="promote-model",
    ),
    pytest.param(
        "list_feature_flags",
        "alist_feature_flags",
        (),
        {"limit": 15, "offset": 3},
        [feature_flag_payload()],
        [FeatureFlag.model_validate(feature_flag_payload())],
        "GET",
        "/v1/feature-flags",
        {"limit": "15", "offset": "3"},
        None,
        id="list-feature-flags",
    ),
]


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(
    (
        "sync_method",
        "async_method",
        "args",
        "kwargs",
        "response_payload",
        "expected_result",
        "http_method",
        "path",
        "query",
        "body",
    ),
    PUBLIC_METHOD_CASES,
)
@pytest.mark.asyncio
async def test_remaining_public_method_contracts(
    asynchronous: bool,
    sync_method: str,
    async_method: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
    response_payload: JSONValue,
    expected_result: object,
    http_method: str,
    path: str,
    query: dict[str, str],
    body: dict[str, JSONValue] | None,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, response_payload)

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            result = await getattr(client, async_method)(*args, **kwargs)
        else:
            result = getattr(client, sync_method)(*args, **kwargs)
        assert result == expected_result
        request = recorder.requests[0]
        assert (request.method, request.url.path) == (http_method, path)
        assert dict(request.url.params) == query
        if body is not None:
            assert json.loads(request.content) == body
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_jwt_authentication_header(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, health_payload())

    recorder = RecordingTransport(responder)
    transport = httpx.MockTransport(recorder)
    client = ValueFabricClient(BASE_URL, jwt_token="jwt-secret")
    client.close()
    await client.aclose()
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    client._sync_client = httpx.Client(
        base_url=BASE_URL, headers=headers, auth=JWTAuth("jwt-secret"), transport=transport
    )
    client._async_client = httpx.AsyncClient(
        base_url=BASE_URL, headers=headers, auth=JWTAuth("jwt-secret"), transport=transport
    )
    try:
        if asynchronous:
            await client.ahealth()
        else:
            client.health()
        request = recorder.requests[0]
        assert request.headers["authorization"] == "Bearer jwt-secret"
        assert "x-api-key" not in request.headers
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_timeout_maps_to_connection_error(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client, _ = await make_client(responder, api_key="must-not-leak")
    try:
        with pytest.raises(SDKConnectionError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert "timed out" in str(captured.value)
        assert "must-not-leak" not in str(captured.value)
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_empty_success_body_raises_typed_response_error(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"", request=request)

    client, _ = await make_client(responder)
    try:
        with pytest.raises(ResponseError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert captured.value.status_code == 204
        assert captured.value.endpoint == "/health"
        assert captured.value.__cause__ is None
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_malformed_json_is_exposed_deterministically(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{broken", request=request)

    client, _ = await make_client(responder)
    try:
        with pytest.raises(ResponseError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert captured.value.status_code == 200
        assert captured.value.endpoint == "/health"
        assert captured.value.__cause__ is None
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_malformed_model_payload_is_rejected(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, {"status": "healthy"})

    client, _ = await make_client(responder)
    try:
        with pytest.raises(ResponseError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert captured.value.status_code == 200
        assert captured.value.endpoint == "/health"
        assert captured.value.__cause__ is None
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(
    ("sync_method", "async_method", "args", "response_payload", "expected_body"),
    [
        pytest.param(
            "create_api_key",
            "acreate_api_key",
            ("automation", "analyst"),
            {**API_KEY_CREATE_PAYLOAD, "expires_at": None, "rate_limit_per_minute": None},
            {"name": "automation", "role": "analyst"},
            id="create-api-key",
        ),
        pytest.param(
            "set_feature_flag",
            "aset_feature_flag",
            ("new_ui", False),
            feature_flag_payload(),
            {"enabled": False, "rollout_percentage": 100},
            id="set-feature-flag",
        ),
        pytest.param(
            "execute_workflow",
            "aexecute_workflow",
            ("roi_calculator",),
            {"workflow_instance_id": "wf-default", "status": "scheduled"},
            {
                "workflow_type": "roi_calculator",
                "inputs": {},
                "priority": "NORMAL",
            },
            id="execute-workflow",
        ),
    ],
)
@pytest.mark.asyncio
async def test_optional_arguments_are_omitted_or_defaulted(
    asynchronous: bool,
    sync_method: str,
    async_method: str,
    args: tuple[str, ...],
    response_payload: dict[str, JSONValue],
    expected_body: dict[str, JSONValue],
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, response_payload)

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            await getattr(client, async_method)(*args)
        else:
            getattr(client, sync_method)(*args)
        assert json.loads(recorder.requests[0].content) == expected_body
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_optional_model_stage_omits_query(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, [model_payload()])

    client, recorder = await make_client(responder)
    try:
        if asynchronous:
            await client.alist_models()
        else:
            client.list_models()
        assert dict(recorder.requests[0].url.params) == {}
    finally:
        client.close()
        await client.aclose()


@pytest.mark.asyncio
async def test_constructor_timeout_configures_sync_and_async_clients() -> None:
    client = ValueFabricClient(BASE_URL, api_key="sdk-secret", timeout=12.5)
    try:
        assert client.timeout == 12.5
        assert client._sync_client.timeout.read == 12.5
        assert client._async_client.timeout.read == 12.5
    finally:
        client.close()
        await client.aclose()


@pytest.mark.asyncio
async def test_sync_context_manager_closes_sync_client() -> None:
    client = ValueFabricClient(BASE_URL, api_key="sdk-secret")
    async with client:
        with client as entered:
            assert entered is client
            assert not client._sync_client.is_closed
        assert client._sync_client.is_closed


@pytest.mark.asyncio
async def test_async_context_manager_closes_async_client() -> None:
    client = ValueFabricClient(BASE_URL, api_key="sdk-secret")
    with client:
        async with client as entered:
            assert entered is client
            assert not client._async_client.is_closed
        assert client._async_client.is_closed


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_invalid_retry_after_preserves_rate_limit_error(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(
            request,
            {"detail": "rate limited"},
            status_code=429,
            headers={"retry-after": "not-a-delay-or-date"},
        )

    client, _ = await make_client(responder)
    try:
        with pytest.raises(RateLimitError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert captured.value.status_code == 429
        assert captured.value.retry_after is None
        assert captured.value.__cause__ is None
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_invalid_created_model_preserves_actual_success_status(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(
            request,
            {"status": "scheduled"},
            status_code=201,
        )

    client, _ = await make_client(responder)
    try:
        with pytest.raises(ResponseError) as captured:
            if asynchronous:
                await client.aexecute_workflow("roi_calculator")
            else:
                client.execute_workflow("roi_calculator")
        assert captured.value.status_code == 201
        assert captured.value.endpoint == "/v1/workflows"
        assert captured.value.__cause__ is None
    finally:
        client.close()
        await client.aclose()


def test_retry_after_http_date_is_converted_to_delta_seconds() -> None:
    retry_after = ValueFabricClient._parse_retry_after("Wed, 21 Oct 2099 07:28:00 GMT")

    assert retry_after is not None
    assert retry_after > 0
