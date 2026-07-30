"""Contract-focused tests for synchronous and asynchronous SDK clients."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from valuefabric.client import ValueFabricClient
from valuefabric.errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)
from valuefabric.errors import (
    ConnectionError as SDKConnectionError,
)
from valuefabric.errors import (
    ValidationError as SDKValidationError,
)
from valuefabric.models import APIKey, FeatureFlag, HealthResponse, ModelVersion, Tenant, Workflow

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
    payload: Any,
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


def make_client(
    responder: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "sdk-secret",
) -> tuple[ValueFabricClient, RecordingTransport]:
    recorder = RecordingTransport(responder)
    transport = httpx.MockTransport(recorder)
    client = ValueFabricClient(BASE_URL, api_key=api_key)
    client._sync_client._transport = transport
    client._async_client._transport = transport
    return client, recorder


def api_key_payload() -> dict[str, Any]:
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


def workflow_payload() -> dict[str, Any]:
    return {
        "workflow_instance_id": "wf-1",
        "workflow_type": "roi_calculator",
        "status": "running",
        "current_state": "calculate",
        "current_node": "calculate",
        "progress_percentage": 50.0,
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


def tenant_payload() -> dict[str, Any]:
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
async def test_list_api_keys_preserves_public_enabled_only_query(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, [api_key_payload()])

    client, recorder = make_client(responder)
    try:
        if asynchronous:
            result = await client.alist_api_keys(enabled_only=False)
        else:
            result = client.list_api_keys(enabled_only=False)

        assert result == [APIKey.model_validate(api_key_payload())]
        assert recorder.requests[0].method == "GET"
        assert recorder.requests[0].url.path == "/v1/api-keys"
        assert dict(recorder.requests[0].url.params) == {"enabled_only": "false"}
        assert recorder.requests[0].headers["x-api-key"] == "sdk-secret"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_list_active_workflows_deserializes_public_list_shape(
    asynchronous: bool,
) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, [workflow_payload()])

    client, recorder = make_client(responder)
    try:
        if asynchronous:
            result = await client.alist_active_workflows()
        else:
            result = client.list_active_workflows()

        assert result == [Workflow.model_validate(workflow_payload())]
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

    client, recorder = make_client(responder)
    try:
        if asynchronous:
            result = await client.aget_workflow("wf-1")
        else:
            result = client.get_workflow("wf-1")

        assert result.workflow_instance_id == "wf-1"
        assert result.progress_percentage == 50.0
        assert recorder.requests[0].url.path == "/v1/workflows/wf-1"
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_execute_workflow_serializes_documented_identity_without_mutating_inputs(
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

    client, recorder = make_client(responder)
    try:
        kwargs = {
            "workflow_type": "roi_calculator",
            "tenant_id": "caller-tenant",
            "user_id": "caller-user",
            "inputs": inputs,
            "priority": "HIGH",
            "workflow_id": "wf-2",
        }
        if asynchronous:
            result = await client.aexecute_workflow(**kwargs)
        else:
            result = client.execute_workflow(**kwargs)

        assert result["workflow_instance_id"] == "wf-2"
        assert json.loads(recorder.requests[0].content) == {
            "workflow_type": "roi_calculator",
            "tenant_id": "caller-tenant",
            "user_id": "caller-user",
            "inputs": inputs,
            "priority": "HIGH",
            "workflow_id": "wf-2",
        }
        assert inputs == {"custom_data": {"revenue": 100}}
    finally:
        client.close()
        await client.aclose()


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_get_tenant_request_and_model(asynchronous: bool) -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        return json_response(request, tenant_payload())

    client, recorder = make_client(responder)
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


def model_payload() -> dict[str, Any]:
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

    client, recorder = make_client(responder)
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


def feature_flag_payload() -> dict[str, Any]:
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

    client, recorder = make_client(responder)
    try:
        kwargs = {
            "key": "new_ui",
            "enabled": False,
            "rollout_percentage": 25,
            "description": "Controlled rollout",
        }
        result = (
            await client.aset_feature_flag(**kwargs)
            if asynchronous
            else client.set_feature_flag(**kwargs)
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


def health_payload() -> dict[str, Any]:
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

    client, recorder = make_client(responder)
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
    asynchronous: bool, status_code: int, exception_type: type[Exception]
) -> None:
    body = {"detail": f"failure-{status_code}"}

    def responder(request: httpx.Request) -> httpx.Response:
        headers = {"retry-after": "7"} if status_code == 429 else None
        return json_response(request, body, status_code=status_code, headers=headers)

    client, _ = make_client(responder, api_key="must-not-leak")
    try:
        with pytest.raises(exception_type) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        error = captured.value
        assert error.response_body == body
        assert "must-not-leak" not in str(error)
        if isinstance(error, APIError):
            assert error.status_code == status_code
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

    client, _ = make_client(responder, api_key="must-not-leak")
    try:
        with pytest.raises(SDKConnectionError) as captured:
            if asynchronous:
                await client.ahealth()
            else:
                client.health()
        assert "connection refused" in str(captured.value)
        assert "must-not-leak" not in str(captured.value)
    finally:
        client.close()
        await client.aclose()
