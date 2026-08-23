from __future__ import annotations

from unittest.mock import Mock

import pytest

import layer4_agents.model_registry_client as module
from layer4_agents.model_registry_client import ModelRegistryClient, ModelSpec, RegistryUnavailable


@pytest.mark.asyncio
async def test_registry_result_is_returned_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ModelRegistryClient("https://registry.test")
    expected = ModelSpec(id="canonical", source="registry", version="1")

    async def fetch(_model_id: str) -> ModelSpec:
        return expected

    monkeypatch.setattr(client, "_fetch_from_registry", fetch)
    assert await client.get_model("requested") is expected
    assert client.get_fallback_stats()["fallback_count"] == 0


@pytest.mark.asyncio
async def test_registry_fallback_is_observable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FALLBACK_MODEL", "safe-fallback")
    monkeypatch.setenv("GATEWAY_BOOTSTRAP_MODE", "true")
    warning = Mock()
    monkeypatch.setattr(module.audit_log, "warning", warning)
    client = ModelRegistryClient("https://registry.test")

    model = await client.get_model("requested")

    assert model == ModelSpec(
        id="safe-fallback",
        source="bootstrap",
        metadata={
            "requested": "requested",
            "fallback_reason": "registry_unavailable",
            "degraded": True,
        },
    )
    assert client.get_fallback_stats().model_dump() == {
        "fallback_count": 1,
        "fallback_model": "safe-fallback",
        "strict_mode": False,
        "registry_url": "https://registry.test",
    }
    warning.assert_called_once()


@pytest.mark.asyncio
async def test_registry_without_fallback_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FALLBACK_MODEL", raising=False)
    monkeypatch.delenv("GATEWAY_BOOTSTRAP_MODE", raising=False)
    error = Mock()
    monkeypatch.setattr(module.audit_log, "error", error)
    client = ModelRegistryClient()
    with pytest.raises(RegistryUnavailable):
        await client.get_model("requested")
    error.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_model_without_bootstrap_mode_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FALLBACK_MODEL", "fallback")
    monkeypatch.delenv("GATEWAY_BOOTSTRAP_MODE", raising=False)
    error = Mock()
    monkeypatch.setattr(module.audit_log, "error", error)
    with pytest.raises(RegistryUnavailable):
        await ModelRegistryClient().get_model("requested")
    error.assert_called_once()


@pytest.mark.asyncio
async def test_http_fetch_success_parsing() -> None:
    import httpx

    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        assert request.url.path == "/models/gpt-4o"
        return httpx.Response(
            200,
            json={
                "id": "11111111-2222-3333-4444-555555555555",
                "model_name": "gpt-4o-2024-08-06",
                "model_version": "v2.1",
                "provider": "openai",
                "stage": "production",
                "eval_score": 0.95,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient(
            "https://registry.local",
            http_client=http_client,
        )
        spec = await client.get_model("gpt-4o", tenant_id="tenant-123")

    assert spec.id == "gpt-4o-2024-08-06"
    assert spec.source == "registry"
    assert spec.version == "v2.1"
    assert spec.metadata["eval_score"] == 0.95
    assert captured_headers.get("x-tenant-id") == "tenant-123"


@pytest.mark.asyncio
async def test_http_caching_avoids_redundant_calls() -> None:
    import httpx

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json={"model_name": "claude-3-5-sonnet", "version": "20241022"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient(
            "https://registry.local",
            cache_ttl=60.0,
            http_client=http_client,
        )
        spec1 = await client.get_model("claude-sonnet")
        spec2 = await client.get_model("claude-sonnet")

    assert spec1 == spec2
    assert call_count == 1


@pytest.mark.asyncio
async def test_http_404_raises_registry_unavailable() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient("https://registry.local", http_client=http_client)
        with pytest.raises(RegistryUnavailable) as exc:
            await client._fetch_from_registry("non-existent")
        assert "404" in str(exc.value)


@pytest.mark.asyncio
async def test_http_500_raises_registry_unavailable() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient("https://registry.local", http_client=http_client)
        with pytest.raises(RegistryUnavailable) as exc:
            await client._fetch_from_registry("broken")
        assert "500" in str(exc.value)


@pytest.mark.asyncio
async def test_http_network_error_raises_registry_unavailable() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient("https://registry.local", http_client=http_client)
        with pytest.raises(RegistryUnavailable) as exc:
            await client._fetch_from_registry("any-model")
        assert "Failed to connect" in str(exc.value)


@pytest.mark.asyncio
async def test_http_non_dict_response_raises_registry_unavailable() -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["invalid", "array", "payload"])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient("https://registry.local", http_client=http_client)
        with pytest.raises(RegistryUnavailable) as exc:
            await client._fetch_from_registry("any-model")
        assert "non-object" in str(exc.value)


@pytest.mark.asyncio
async def test_http_canonical_v1_path_resolution() -> None:
    import httpx

    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(200, json={"model_name": "gpt-4o", "version": "v1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ModelRegistryClient("https://registry.local/v1", http_client=http_client)
        spec = await client.get_model("gpt-4o")

    assert spec.id == "gpt-4o"
    assert requested_paths == ["/v1/models/gpt-4o"]


