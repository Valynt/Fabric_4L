"""Tests for L2.5 health probe safety (P1-011)."""

from unittest.mock import AsyncMock, patch

import pytest

from layer2_5_signal_refinery.api.main import _probe_database, _probe_l3_client


@pytest.mark.asyncio
async def test_probe_database_does_not_leak_exception_string():
    with patch(
        "layer2_5_signal_refinery.database.get_engine",
        side_effect=RuntimeError("connection refused: secret-db-host:5432"),
    ):
        result = await _probe_database()
    assert result.healthy is False
    assert "secret-db-host" not in result.detail
    assert "postgresql:unavailable" in result.detail


@pytest.mark.asyncio
async def test_probe_l3_client_does_not_leak_exception_string():
    with patch(
        "layer2_5_signal_refinery.api.main.get_l3_client",
        side_effect=RuntimeError("timeout connecting to l3.internal:8003"),
    ):
        result = await _probe_l3_client()
    assert result.healthy is False
    assert "l3.internal" not in result.detail
    assert "l3_client:unavailable" in result.detail
