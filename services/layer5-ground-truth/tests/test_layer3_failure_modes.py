from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from layer5_ground_truth.api.main import create_app
from layer5_ground_truth.integration.layer3_client import (
    ERR_LAYER3_CONTRACT_INVALID,
    ERR_LAYER3_POLICY_DENIED,
    ERR_LAYER3_TENANT_MISMATCH,
    ERR_LAYER3_TIMEOUT,
    Layer3Client,
    Layer3PolicyDeniedError,
    Layer3TenantMismatchError,
)
from tests.conftest import TEST_ORG_ID


class _FakePostClient:
    def __init__(self, side_effect):
        self.post = AsyncMock(side_effect=side_effect)


class _DummyMetrics:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.outcomes: list[tuple[str, str]] = []

    def increment_kg_sync(self, status: str) -> None:
        self.statuses.append(status)

    def increment_kg_sync_outcome(self, sync_status: str, transition: str) -> None:
        self.outcomes.append((sync_status, transition))


def _request() -> httpx.Request:
    return httpx.Request("POST", "http://layer3.test/api/v1/nodes")


def _response(
    status_code: int, *, json_payload=None, text: str | None = None
) -> httpx.Response:
    if json_payload is not None:
        return httpx.Response(status_code, json=json_payload, request=_request())
    return httpx.Response(status_code, text=text or "", request=_request())


def _enabled_client(fake_post_client: _FakePostClient) -> Layer3Client:
    client = Layer3Client()
    client._settings.layer3_sync_enabled = (
        True  # exercise sync error handling despite test env default.
    )
    client._client = fake_post_client  # type: ignore[assignment]
    return client


async def _sync(client: Layer3Client, *, tenant_id=TEST_ORG_ID) -> str | None:
    return await client.sync_truth_object(
        truth_object_id=uuid.uuid4(),
        tenant_id=tenant_id,
        claim="claim",
        claim_type="efficiency_gain",
        confidence=0.91,
        status="approved",
        maturity_level=4,
    )


@pytest.mark.asyncio
async def test_layer3_upstream_policy_denial_propagates_with_stable_error_code(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = _DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.get_metrics", lambda: metrics
    )
    fake = _FakePostClient(
        lambda *_args, **_kwargs: _response(403, json_payload={"detail": "denied"})
    )
    client = _enabled_client(fake)

    with pytest.raises(Layer3PolicyDeniedError):
        await _sync(client)

    assert "policy_denied" in metrics.statuses
    record = next(rec for rec in caplog.records if rec.msg == "layer3_policy_denied")
    assert record.error_code == ERR_LAYER3_POLICY_DENIED
    assert record.tenant_id == str(TEST_ORG_ID)
    assert record.upstream_status_code == 403
    assert record.request_id is None


@pytest.mark.asyncio
async def test_layer3_timeout_returns_none_and_logs_timeout_code(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = _DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.get_metrics", lambda: metrics
    )
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.asyncio.sleep", AsyncMock()
    )
    fake = _FakePostClient(httpx.ReadTimeout("timed out", request=_request()))
    client = _enabled_client(fake)

    assert await _sync(client) is None

    assert "timeout" in metrics.statuses
    record = next(rec for rec in caplog.records if rec.msg == "layer3_timeout")
    assert record.error_code == ERR_LAYER3_TIMEOUT
    assert record.tenant_id == str(TEST_ORG_ID)


@pytest.mark.asyncio
async def test_layer3_malformed_contract_response_returns_none_with_contract_code(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = _DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.get_metrics", lambda: metrics
    )
    fake = _FakePostClient(
        lambda *_args, **_kwargs: _response(200, json_payload={"unexpected": "shape"})
    )
    client = _enabled_client(fake)

    assert await _sync(client) is None

    assert "contract_invalid" in metrics.statuses
    record = next(
        rec for rec in caplog.records if rec.msg == "layer3_contract_missing_node_id"
    )
    assert record.error_code == ERR_LAYER3_CONTRACT_INVALID
    assert record.tenant_id == str(TEST_ORG_ID)


@pytest.mark.asyncio
async def test_layer3_tenant_mismatch_propagates_as_security_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = _DummyMetrics()
    monkeypatch.setattr(
        "layer5_ground_truth.integration.layer3_client.get_metrics", lambda: metrics
    )
    attacker_tenant = uuid.uuid4()
    fake = _FakePostClient(
        lambda *_args, **_kwargs: _response(
            200,
            json_payload={"id": "kg-node-1", "tenant_id": str(attacker_tenant)},
        )
    )
    client = _enabled_client(fake)

    with pytest.raises(Layer3TenantMismatchError):
        await _sync(client)

    assert "tenant_mismatch" in metrics.statuses
    record = next(rec for rec in caplog.records if rec.msg == "layer3_tenant_mismatch")
    assert record.error_code == ERR_LAYER3_TENANT_MISMATCH
    assert record.tenant_id == str(TEST_ORG_ID)


@pytest.mark.asyncio
async def test_main_returns_explicit_response_for_layer3_security_failures() -> None:
    app = create_app()

    @app.get("/api/v1/test-layer3-policy-denial")
    async def _raise_policy_denial():
        raise Layer3PolicyDeniedError(
            "Layer 3 policy denied Ground Truth sync", tenant_id=TEST_ORG_ID
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "X-Tenant-ID": str(TEST_ORG_ID),
            "X-Service-Auth": "test-service-auth-secret-that-is-32-chars-long-ok",
            "X-Request-ID": "req-layer3-policy-test",
        },
    ) as client:
        response = await client.get("/api/v1/test-layer3-policy-denial")

    assert response.status_code == 403
    payload = response.json()
    assert payload["code"] == ERR_LAYER3_POLICY_DENIED
    assert payload["trace_id"] == "req-layer3-policy-test"
    assert payload["details"]["tenant_id"] == str(TEST_ORG_ID)
from fastapi import HTTPException

from layer5_ground_truth.api.main import create_app
from layer5_ground_truth.integration.layer3_client import Layer3Client
from tests.conftest import TEST_ORG_ID


@pytest.mark.asyncio
async def test_layer3_entity_context_policy_denial_returns_none(monkeypatch) -> None:
    req = httpx.Request("GET", "http://layer3/api/v1/entities/e1")
    response = httpx.Response(403, request=req, json={"detail": "policy denied"})

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.HTTPStatusError("forbidden", request=req, response=response)
    monkeypatch.setattr("layer5_ground_truth.integration.layer3_client.Layer3Client._get_client", lambda self: mock_client)

    client = Layer3Client()
    result = await client.get_entity_context("e1", TEST_ORG_ID)
    assert result is None


@pytest.mark.asyncio
async def test_layer3_entity_context_timeout_returns_none(monkeypatch) -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ReadTimeout("timed out")
    monkeypatch.setattr("layer5_ground_truth.integration.layer3_client.Layer3Client._get_client", lambda self: mock_client)

    client = Layer3Client()
    result = await client.get_entity_context("e1", TEST_ORG_ID)
    assert result is None


@pytest.mark.asyncio
async def test_layer3_entity_context_malformed_contract_returns_none(monkeypatch) -> None:
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = ["unexpected-array"]
    mock_client.get.return_value = mock_response
    monkeypatch.setattr("layer5_ground_truth.integration.layer3_client.Layer3Client._get_client", lambda self: mock_client)

    client = Layer3Client()
    result = await client.get_entity_context("e1", TEST_ORG_ID)
    assert result is None


@pytest.mark.asyncio
async def test_layer3_entity_context_tenant_mismatch_returns_none(monkeypatch) -> None:
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"id": "e1", "tenant_id": str(uuid.uuid4())}
    mock_client.get.return_value = mock_response
    monkeypatch.setattr("layer5_ground_truth.integration.layer3_client.Layer3Client._get_client", lambda self: mock_client)

    client = Layer3Client()
    result = await client.get_entity_context("e1", TEST_ORG_ID)
    assert result is None


def test_security_http_exception_uses_explicit_security_error_payload() -> None:
    app = create_app()

    @app.get("/test/security-error")
    async def _route() -> None:
        raise HTTPException(status_code=403, detail={"error_code": "INSUFFICIENT_SCOPE", "message": "Denied"})

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/test/security-error", headers={"X-Tenant-ID": str(TEST_ORG_ID), "X-Service-Auth": "test-service-auth-secret-that-is-32-chars-long-ok"})

    assert response.status_code == 403
    assert response.json()["error"] == "security_error"
    assert response.json()["error_code"] == "INSUFFICIENT_SCOPE"
