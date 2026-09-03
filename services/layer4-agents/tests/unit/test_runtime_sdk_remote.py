"""Tests for the async HTTP transport behind the runtime SDK surface."""

from __future__ import annotations

import httpx
import pytest

from layer4_agents.runtime import RunStatus
from layer4_agents.runtime.errors import AgentRuntimeError, TenantRequiredError
from layer4_agents.runtime.sdk import RemoteAgentRuntimeClient, SDKTimeoutError

pytestmark = pytest.mark.unit


def _payload(run_id: str = "run-1", tenant_id: str = "tenant-a") -> dict[str, object]:
    return {
        "run_id": run_id,
        "workflow_id": "workflow-1",
        "trace_id": "trace-1",
        "tenant_id": tenant_id,
        "workflow_type": "echo",
        "status": RunStatus.COMPLETED.value,
        "created_at": "2026-01-01T00:00:00+00:00",
        "output": {"ok": True},
        "metadata": {},
    }


async def test_remote_client_preserves_tenant_header_and_surface() -> None:
    seen: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (request.method, request.url.path, request.headers.get("X-Tenant-ID"))
        )
        if request.url.path.endswith("/runs") and request.method == "POST":
            envelope = _payload()
            envelope.pop("output")
            envelope.pop("metadata")
            return httpx.Response(202, json=envelope)
        if request.url.path.endswith("/runs/run-1"):
            return httpx.Response(200, json=_payload())
        if request.url.path.endswith("/runs") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "runs": [
                        {
                            "run_id": "run-1",
                            "workflow_id": "workflow-1",
                            "workflow_type": "echo",
                            "status": "completed",
                            "created_at": "2026-01-01T00:00:00+00:00",
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"detail": {"code": "RUN_NOT_FOUND"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = RemoteAgentRuntimeClient(
            "http://runtime",
            default_tenant_id="tenant-a",
            http_client=http_client,
        )
        submitted = await client.submit_run("echo", {"x": 1})
        fetched = await client.get_run(submitted.run_id)
        listed = await client.list_runs()

    assert submitted.run_id == "run-1"
    assert fetched is not None and fetched.output == {"ok": True}
    assert len(listed) == 1
    assert all(tenant == "tenant-a" for _, _, tenant in seen)


async def test_remote_client_maps_errors_and_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/runs/missing"):
            return httpx.Response(
                404,
                json={"detail": {"code": "RUN_NOT_FOUND", "message": "missing"}},
            )
        return httpx.Response(
            400,
            json={
                "detail": {
                    "code": "TENANT_REQUIRED",
                    "message": "tenant required",
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = RemoteAgentRuntimeClient("http://runtime", http_client=http_client)
        with pytest.raises(TenantRequiredError):
            await client.submit_run("echo", {})
        client_with_tenant = RemoteAgentRuntimeClient(
            "http://runtime", default_tenant_id="tenant-a", http_client=http_client
        )
        assert await client_with_tenant.get_run("missing") is None


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.ReadError("broken")])
async def test_remote_client_maps_transport_errors(error: httpx.HTTPError) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = RemoteAgentRuntimeClient("http://runtime", default_tenant_id="tenant-a", http_client=http_client)
        with pytest.raises(AgentRuntimeError, match="Runtime transport failed"):
            await client.get_run("run-1")


async def test_remote_client_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = RemoteAgentRuntimeClient("http://runtime", default_tenant_id="tenant-a", http_client=http_client)
        with pytest.raises(SDKTimeoutError):
            await client.get_run("run-1")
