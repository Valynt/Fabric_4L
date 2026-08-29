"""Contract tests for the canonical Layer 5 transport."""

from __future__ import annotations

from typing import Self

import pytest
from value_fabric.shared.clients.layer5 import (
    Layer5Transport,
    Layer5TransportError,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.text = text

    def json(self) -> object:
        return self._payload


class _FakeAsyncClient:
    """Context-manager httpx.AsyncClient stand-in driven by a script of responses."""

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[object, ...]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        outcome = self._responses.pop(0) if self._responses else _FakeResponse()
        self.calls.append((method, url, kwargs))
        return outcome


class _FakeHttpx:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.client = _FakeAsyncClient(list(responses))

    def AsyncClient(self, **_: object) -> _FakeAsyncClient:
        return self.client


@pytest.mark.asyncio
async def test_transport_builds_s2s_auth_headers() -> None:
    headers = Layer5Transport.build_headers("tenant-abc", "service-secret")
    assert headers == {
        "X-Tenant-ID": "tenant-abc",
        "X-Service-Auth": "service-secret",
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_transport_sends_tenant_scoped_request(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = Layer5Transport(base_url="https://l5.example/internal/", timeout=5.0)
    fake = _FakeHttpx([_FakeResponse()])
    monkeypatch.setattr("value_fabric.shared.clients.layer5.httpx", fake)

    await transport.request("GET", "/api/v1/maturity-ladder", tenant_id="tenant-abc")

    (method, url, kwargs) = fake.client.calls[0]
    assert method == "GET"
    assert url == "https://l5.example/internal/api/v1/maturity-ladder"
    assert kwargs["headers"]["X-Tenant-ID"] == "tenant-abc"
    assert kwargs["headers"]["X-Service-Auth"] == ""


@pytest.mark.asyncio
async def test_transport_raises_transport_error_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = Layer5Transport(base_url="https://l5.example")
    fake = _FakeHttpx([_FakeResponse(status_code=422, text="detail body")])
    monkeypatch.setattr("value_fabric.shared.clients.layer5.httpx", fake)

    with pytest.raises(Layer5TransportError) as excinfo:
        await transport.request("POST", "/api/v1/truths", tenant_id="tenant-abc")
    assert excinfo.value.status_code == 422
    assert excinfo.value.response_text == "detail body"
    assert str(excinfo.value) == "detail body"


@pytest.mark.asyncio
async def test_transport_uses_generic_message_when_body_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = Layer5Transport(base_url="https://l5.example")
    fake = _FakeHttpx([_FakeResponse(status_code=500)])
    monkeypatch.setattr("value_fabric.shared.clients.layer5.httpx", fake)

    with pytest.raises(Layer5TransportError) as excinfo:
        await transport.request("GET", "/api/v1/truths", tenant_id="tenant-abc")
    assert str(excinfo.value) == "Layer 5 request failed (500)"


@pytest.mark.asyncio
async def test_transport_returns_success_json(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = Layer5Transport(base_url="https://l5.example")
    fake = _FakeHttpx([_FakeResponse(status_code=200, payload={"items": []})])
    monkeypatch.setattr("value_fabric.shared.clients.layer5.httpx", fake)

    response = await transport.request("GET", "/api/v1/truths", tenant_id="t")
    assert response.json() == {"items": []}
