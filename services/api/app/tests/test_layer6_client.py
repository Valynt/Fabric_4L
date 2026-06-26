import httpx
import pytest

from app.clients.layer6_client import Layer6Client


@pytest.fixture
def mock_transport():
    def handler(request: httpx.Request):
        if request.url.path == "/v1/benchmarks/datasets":
            return httpx.Response(200, json=[{"dataset_id": "ds1"}])
        if request.url.path == "/v1/benchmarks/compare":
            return httpx.Response(200, json={"percentile": 50})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_list_datasets(mock_transport, monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)
    client = Layer6Client(base_url="http://layer6", timeout=1.0)
    # Patch httpx.AsyncClient to use our mock transport.
    original_async_client = httpx.AsyncClient

    def _patched_async_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_async_client(transport=mock_transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)
    result = await client.list_datasets("tenant-1")
    assert result == [{"dataset_id": "ds1"}]


@pytest.mark.asyncio
async def test_compare(mock_transport, monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)
    client = Layer6Client(base_url="http://layer6", timeout=1.0)
    original_async_client = httpx.AsyncClient

    def _patched_async_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_async_client(transport=mock_transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)
    result = await client.compare(
        "tenant-1", {"dataset_id": "ds1", "metric": "revenue", "company_value": "100"}
    )
    assert result["percentile"] == 50
