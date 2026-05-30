"""Chaos tests with real failure injection (not mocked).

P2-010: Verify chaos tests are not all mocked by adding tests that
use actual network failures, connection refusals, and timeouts against
localhost ports with no listener.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

pytestmark = [pytest.mark.chaos]


class TestRealNetworkFailure:
    """Un-mocked failure injection using actual connection failures."""

    @pytest.mark.asyncio
    async def test_connection_refused_to_unused_port(self):
        """Attempting to connect to an unused localhost port must fail.

        On some platforms this raises ConnectError immediately; on others it
        times out as ConnectTimeout. Either outcome proves real failure
        injection without mocks.
        """
        async with httpx.AsyncClient() as client:
            with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
                await client.get("http://localhost:59999/", timeout=3.0)

    @pytest.mark.asyncio
    async def test_connection_timeout_to_blackhole_port(self):
        """Connecting to a blackhole address must raise TimeoutException.

        Uses RFC 5737 TEST-NET-1 (192.0.2.0/24) which is guaranteed unrouted.
        This tests real timeout behavior without any mocking.
        """
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.TimeoutException):
                await client.get("http://192.0.2.1:8080/", timeout=1.0)

    @pytest.mark.asyncio
    async def test_asyncio_gather_with_real_cancel(self):
        """Cancel a real asyncio task mid-flight — no mocks involved.

        Verifies that structured concurrency behaves correctly under cancellation.
        """
        async def slow_work():
            await asyncio.sleep(60)
            return "should never reach"

        task = asyncio.create_task(slow_work())
        await asyncio.sleep(0)  # let task start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert task.cancelled()
