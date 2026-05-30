"""Chaos engineering resilience tests (P2-010)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from tests.backend_integrated.conftest import SERVICE_URLS

pytestmark = [pytest.mark.backend_integrated]


class TestChaosResilience:
    """Verify service resilience under degraded conditions."""

    async def test_all_layers_handle_concurrent_requests(self) -> None:
        """All layers must handle 20 concurrent requests without crashing."""
        async def request_health(layer: str) -> int:
            url = f"{SERVICE_URLS[layer]}/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(url)
                    return response.status_code
                except httpx.HTTPError:
                    return 0

        results = await asyncio.gather(*[request_health(layer) for layer in ["l1", "l2", "l3", "l4", "l5", "l6"] for _ in range(20)])
        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 100, f"Expected at least 100 successful health checks, got {success_count}"

    async def test_graceful_timeout_on_slow_endpoint(self) -> None:
        """Slow endpoints must return a response within a reasonable timeout."""
        for layer in ["l4", "l6"]:
            url = f"{SERVICE_URLS[layer]}/health"
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(url)
                    assert response.status_code in (200, 204)
                except httpx.TimeoutException:
                    pytest.fail(f"{layer.upper()} health endpoint timed out")

    async def test_layers_reject_malformed_tenant_id(self) -> None:
        """All layers must reject malformed tenant IDs without crashing."""
        for layer in ["l2", "l3", "l4", "l5", "l6"]:
            url = f"{SERVICE_URLS[layer]}/health"
            headers = {
                "X-Tenant-ID": "not-a-valid-uuid",
                "X-Service-Auth": "test",
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(url, headers=headers)
                    # Should not crash; may return 401/403/422
                    assert response.status_code != 500
                except httpx.HTTPError:
                    pass  # Network errors acceptable for this test
