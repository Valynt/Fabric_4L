"""Unit tests for OIDCClient.discover() retry and error-classification behavior.

Validates:
- Transient errors (5xx, 429, timeout, connection error) trigger exactly one retry.
- Non-transient errors (4xx, malformed JSON, missing required fields) fail
  immediately without a retry.
- Both exception types preserve the root cause via __cause__.
- Happy path returns the discovery document.

Uses respx to mock HTTP calls without a live server.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from value_fabric.shared.identity.oidc import (
    OIDCClient,
    OIDCDiscoveryError,
    TransientOIDCDiscoveryError,
    _validate_discovery_document,
)

_ISSUER = "https://idp.example.com/realms/fabric"
_WELL_KNOWN = f"{_ISSUER}/.well-known/openid-configuration"

_VALID_DOC = {
    "issuer": _ISSUER,
    "authorization_endpoint": f"{_ISSUER}/protocol/openid-connect/auth",
    "token_endpoint": f"{_ISSUER}/protocol/openid-connect/token",
    "jwks_uri": f"{_ISSUER}/protocol/openid-connect/certs",
    "response_types_supported": ["code"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_count(mock_route) -> int:
    return len(mock_route.calls)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_success():
    """Returns the discovery document on a clean 200 response."""
    respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(200, json=_VALID_DOC))

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["authorization_endpoint"] == _VALID_DOC["authorization_endpoint"]
    assert doc["token_endpoint"] == _VALID_DOC["token_endpoint"]
    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]


# ---------------------------------------------------------------------------
# Retry tests — transient errors trigger exactly one retry; second succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_500():
    """HTTP 500 triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_502():
    """HTTP 502 triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(502, text="Bad Gateway"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_503():
    """HTTP 503 triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_504():
    """HTTP 504 triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(504, text="Gateway Timeout"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_429():
    """HTTP 429 (rate limit) triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(429, text="Too Many Requests"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_timeout():
    """TimeoutException triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.TimeoutException("timed out"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_retries_on_connection_error():
    """ConnectError triggers one retry; second attempt succeeds."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.ConnectError("connection refused"),
        httpx.Response(200, json=_VALID_DOC),
    ]

    client = OIDCClient()
    doc = await client.discover(_ISSUER)

    assert doc["jwks_uri"] == _VALID_DOC["jwks_uri"]
    assert _call_count(route) == 2


# ---------------------------------------------------------------------------
# No-retry tests — non-transient errors fail immediately (one HTTP call)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_400():
    """HTTP 400 raises OIDCDiscoveryError immediately; exactly one call made."""
    route = respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(400, text="Bad Request"))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert _call_count(route) == 1
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_401():
    """HTTP 401 raises OIDCDiscoveryError immediately; exactly one call made."""
    route = respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(401, text="Unauthorized"))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_403():
    """HTTP 403 raises OIDCDiscoveryError immediately; exactly one call made."""
    route = respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(403, text="Forbidden"))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_404():
    """HTTP 404 raises OIDCDiscoveryError immediately; exactly one call made."""
    route = respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(404, text="Not Found"))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_malformed_json():
    """200 with non-JSON body raises OIDCDiscoveryError immediately; one call."""
    route = respx.get(_WELL_KNOWN).mock(
        return_value=httpx.Response(200, text="not valid json {{{{")
    )

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert "invalid JSON" in str(exc_info.value)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_json_array():
    """200 with a JSON array raises OIDCDiscoveryError immediately; one call."""
    route = respx.get(_WELL_KNOWN).mock(
        return_value=httpx.Response(200, json=[{"keys": []}])
    )

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert "not a JSON object" in str(exc_info.value)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_json_string():
    """200 with a JSON string raises OIDCDiscoveryError immediately; one call."""
    route = respx.get(_WELL_KNOWN).mock(
        return_value=httpx.Response(200, text='"just a string"')
    )

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert "not a JSON object" in str(exc_info.value)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_missing_required_fields():
    """200 with doc missing all required fields raises OIDCDiscoveryError; one call."""
    route = respx.get(_WELL_KNOWN).mock(
        return_value=httpx.Response(200, json={"issuer": _ISSUER})
    )

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert not isinstance(exc_info.value, TransientOIDCDiscoveryError)
    assert "missing required fields" in str(exc_info.value)
    assert _call_count(route) == 1


@pytest.mark.asyncio
@respx.mock
async def test_discover_does_not_retry_on_partial_missing_fields():
    """200 with only authorization_endpoint present raises OIDCDiscoveryError listing missing fields."""
    partial_doc = {
        "issuer": _ISSUER,
        "authorization_endpoint": f"{_ISSUER}/auth",
        # token_endpoint and jwks_uri are absent
    }
    route = respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(200, json=partial_doc))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    error_msg = str(exc_info.value)
    assert "token_endpoint" in error_msg
    assert "jwks_uri" in error_msg
    assert _call_count(route) == 1


# ---------------------------------------------------------------------------
# Exhausted retry tests — both attempts fail with transient error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_raises_after_two_5xx_attempts():
    """Both attempts return 503; raises TransientOIDCDiscoveryError; exactly two calls."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(503, text="Service Unavailable"),
    ]

    client = OIDCClient()
    with pytest.raises(TransientOIDCDiscoveryError):
        await client.discover(_ISSUER)

    assert _call_count(route) == 2


@pytest.mark.asyncio
@respx.mock
async def test_discover_raises_after_two_connection_errors():
    """Both attempts raise ConnectError; raises TransientOIDCDiscoveryError; two calls."""
    route = respx.get(_WELL_KNOWN)
    route.side_effect = [
        httpx.ConnectError("connection refused"),
        httpx.ConnectError("connection refused"),
    ]

    client = OIDCClient()
    with pytest.raises(TransientOIDCDiscoveryError):
        await client.discover(_ISSUER)

    assert _call_count(route) == 2


# ---------------------------------------------------------------------------
# Root cause preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_discover_error_preserves_cause_on_4xx():
    """OIDCDiscoveryError.__cause__ is the original httpx.HTTPStatusError."""
    respx.get(_WELL_KNOWN).mock(return_value=httpx.Response(404, text="Not Found"))

    client = OIDCClient()
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
    assert exc_info.value.__cause__.response.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_discover_error_preserves_cause_on_timeout():
    """TransientOIDCDiscoveryError.__cause__ is the original httpx.TimeoutException."""
    respx.get(_WELL_KNOWN).side_effect = [
        httpx.TimeoutException("read timeout"),
        httpx.TimeoutException("read timeout"),
    ]

    client = OIDCClient()
    with pytest.raises(TransientOIDCDiscoveryError) as exc_info:
        await client.discover(_ISSUER)

    assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)


# ---------------------------------------------------------------------------
# _validate_discovery_document unit tests (pure function)
# ---------------------------------------------------------------------------


def test_validate_discovery_document_passes_with_all_fields():
    """No exception when all required fields are present."""
    _validate_discovery_document(_VALID_DOC, _ISSUER)  # must not raise


def test_validate_discovery_document_raises_on_empty_doc():
    """Empty dict raises OIDCDiscoveryError listing all three missing fields."""
    with pytest.raises(OIDCDiscoveryError) as exc_info:
        _validate_discovery_document({}, _ISSUER)

    msg = str(exc_info.value)
    assert "authorization_endpoint" in msg
    assert "token_endpoint" in msg
    assert "jwks_uri" in msg


def test_validate_discovery_document_raises_on_single_missing_field():
    """Doc missing only jwks_uri raises OIDCDiscoveryError mentioning that field."""
    doc = dict(_VALID_DOC)
    del doc["jwks_uri"]

    with pytest.raises(OIDCDiscoveryError) as exc_info:
        _validate_discovery_document(doc, _ISSUER)

    assert "jwks_uri" in str(exc_info.value)
    assert "authorization_endpoint" not in str(exc_info.value)
