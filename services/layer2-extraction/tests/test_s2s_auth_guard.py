from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.responses import PlainTextResponse
from starlette.requests import Request

from layer2_extraction.api import s2s_auth


def _request(path: str, *, method: str = "POST", headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": raw_headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
        }
    )


async def _pass_through(request: Request) -> PlainTextResponse:
    return PlainTextResponse(f"passed:{request.method}:{request.url.path}")


@pytest.mark.asyncio
async def test_non_internal_route_bypasses_s2s_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/health"),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 200
    assert response.body == b"passed:POST:/health"


@pytest.mark.asyncio
async def test_internal_get_route_bypasses_s2s_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract", method="GET"),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 200
    assert response.body == b"passed:GET:/v1/extract"


@pytest.mark.asyncio
async def test_internal_post_without_secret_bypasses_in_non_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract"),
        _pass_through,
        is_strict_runtime=lambda: False,
    )

    assert response.status_code == 200
    assert response.body == b"passed:POST:/v1/extract"


@pytest.mark.asyncio
async def test_internal_post_without_secret_fails_closed_in_strict_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract"),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 503
    assert response.body == (
        b'{"detail":"S2S authentication not configured in strict environment",'
        b'"code":"s2s_misconfiguration"}'
    )


@pytest.mark.asyncio
async def test_internal_post_with_secret_requires_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract"),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 401
    assert response.body == (
        b'{"detail":"S2S Bearer token required for internal extraction routes",'
        b'"code":"s2s_token_required"}'
    )


@pytest.mark.asyncio
async def test_internal_post_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract", headers={"Authorization": "Bearer invalid"}),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 401
    assert response.body == (
        b'{"detail":"Invalid or expired S2S token for internal extraction route",'
        b'"code":"s2s_token_invalid"}'
    )


@pytest.mark.asyncio
async def test_internal_post_rejects_unexpected_service_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)
    monkeypatch.setattr(
        "value_fabric.shared.identity.jwt.decode_service_jwt",
        lambda token, expected_audience: SimpleNamespace(sub="layer3-knowledge"),
    )

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract", headers={"Authorization": "Bearer valid"}),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 403
    assert response.body == (
        b'{"detail":"Unexpected service caller: \'layer3-knowledge\'",'
        b'"code":"s2s_caller_forbidden"}'
    )


@pytest.mark.asyncio
async def test_internal_post_accepts_expected_service_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "x" * 64)
    monkeypatch.setattr(
        "value_fabric.shared.identity.jwt.decode_service_jwt",
        lambda token, expected_audience: SimpleNamespace(sub=s2s_auth.S2S_EXPECTED_SUB),
    )

    response = await s2s_auth.enforce_s2s_auth_guard(
        _request("/v1/extract", headers={"Authorization": "Bearer valid"}),
        _pass_through,
        is_strict_runtime=lambda: True,
    )

    assert response.status_code == 200
    assert response.body == b"passed:POST:/v1/extract"
