from __future__ import annotations

"""Header-correctness tests for the shared cross-layer HTTP scaffolding.

W1 of the Layer 4 decomposition: ``integration/_base.py`` is the single
source of truth for tenant / service-auth / trace header injection. These
tests lock in the header contract so a header or auth regression in any edge
client is caught in one place instead of being reviewed per-client.
"""

import asyncio

from value_fabric.shared.observability.trace_context import CANONICAL_TRACE_HEADER

from layer4_agents.integration._base import (
    DEFAULT_CONNECTION_LIMITS,
    SERVICE_AUTH_HEADER,
    TENANT_ID_HEADER,
    ServiceAuthHeaders,
    ServiceHttpClient,
)

_SERVICE_SECRET = "svc-secret-test"


def _async_close(awaitable) -> None:
    """Run a one-shot async coroutine (e.g. client.close())."""
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(awaitable)


# ---------------------------------------------------------------------------
# ServiceAuthHeaders
# ---------------------------------------------------------------------------


def test_service_auth_headers_build_injects_tenant_service_auth_and_trace(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    headers = ServiceAuthHeaders().build("tenant-1", trace_id="trace-1")
    assert headers[TENANT_ID_HEADER] == "tenant-1"
    assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET
    assert headers[CANONICAL_TRACE_HEADER] == "trace-1"


def test_service_auth_headers_omits_tenant_when_absent(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    headers = ServiceAuthHeaders().build()
    assert TENANT_ID_HEADER not in headers
    assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET
    assert CANONICAL_TRACE_HEADER not in headers


def test_service_auth_headers_drops_service_auth_when_no_secret(monkeypatch) -> None:
    monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)
    headers = ServiceAuthHeaders().build("tenant-1")
    assert headers[TENANT_ID_HEADER] == "tenant-1"
    assert SERVICE_AUTH_HEADER not in headers


# ---------------------------------------------------------------------------
# ServiceHttpClient
# ---------------------------------------------------------------------------


def test_service_http_client_get_headers_uses_default_tenant(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    client = ServiceHttpClient(base_url="http://svc.test", tenant_id="default-tenant")
    headers = client._get_headers()
    assert headers[TENANT_ID_HEADER] == "default-tenant"
    assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET


def test_service_http_client_get_headers_per_call_tenant_override(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    client = ServiceHttpClient(base_url="http://svc.test", tenant_id="default-tenant")
    headers = client._get_headers("override-tenant")
    assert headers[TENANT_ID_HEADER] == "override-tenant"


def test_service_http_client_get_headers_trace_injection(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    client = ServiceHttpClient(base_url="http://svc.test", tenant_id="t1")
    headers = client._get_headers("t1", trace_id="span-1")
    assert headers[CANONICAL_TRACE_HEADER] == "span-1"


def test_service_http_client_build_client_sets_bound_limits_and_timeout() -> None:
    client = ServiceHttpClient(base_url="http://svc.test", timeout=12.5)
    # Bound connection limits come from the shared public default.
    assert client._limits is DEFAULT_CONNECTION_LIMITS
    assert DEFAULT_CONNECTION_LIMITS.max_connections == 100
    http_client = client._build_client()
    assert http_client.timeout.connect == 12.5
    _async_close(http_client.aclose())


def test_service_http_client_close_handles_lazy_client_slot() -> None:
    """Base close() must not AttributeError on docstyle lazy-_client subclass."""

    class LazyServiceClient(ServiceHttpClient):
        def __init__(self) -> None:
            super().__init__(base_url="http://lazy.test")
            self._client = None

        def ensure(self) -> None:
            self._client = self._build_client()

    client = LazyServiceClient()
    client.ensure()
    assert getattr(client, "client", None) is None
    assert client._client is not None
    _async_close(client.close())


def test_service_http_client_close_is_noop_when_no_client() -> None:
    """close() with no client present must not raise."""

    class EmptyClient(ServiceHttpClient):
        pass

    client = EmptyClient(base_url="http://empty.test")
    _async_close(client.close())


# ---------------------------------------------------------------------------
# Edge clients delegate header building to the shared base
# ---------------------------------------------------------------------------


def test_layer1_client_delegates_headers_and_bearer_auth_to_base(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    from layer4_agents.integration.layer1_client import Layer1IngestionClient

    client = Layer1IngestionClient(base_url="http://l1.test", api_key="key", tenant_id="t1")
    try:
        headers = client._get_headers()
        assert headers[TENANT_ID_HEADER] == "t1"
        assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET
        assert "Bearer" in client.client.headers.get("Authorization", "")
    finally:
        _async_close(client.close())


def test_layer2_client_delegates_headers_to_base(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    from layer4_agents.integration.layer2_client import Layer2ExtractionClient

    client = Layer2ExtractionClient(base_url="http://l2.test", tenant_id="t2")
    try:
        headers = client._get_headers("t2")
        assert headers[TENANT_ID_HEADER] == "t2"
        assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET
    finally:
        _async_close(client.close())


def test_layer3_client_keeps_json_content_headers_on_top_of_base(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", _SERVICE_SECRET)
    from layer4_agents.integration.layer3_client import Layer3Client

    client = Layer3Client(base_url="http://l3.test", tenant_id="t3")
    headers = client._get_headers()
    assert headers[TENANT_ID_HEADER] == "t3"
    assert headers[SERVICE_AUTH_HEADER] == _SERVICE_SECRET
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"


def test_layer5_client_reuses_shared_header_constants() -> None:
    from layer4_agents.integration.layer5_client import (
        SERVICE_AUTH_HEADER as L5_SA,
    )
    from layer4_agents.integration.layer5_client import (
        TENANT_ID_HEADER as L5_TID,
    )

    assert L5_TID == TENANT_ID_HEADER
    assert L5_SA == SERVICE_AUTH_HEADER
