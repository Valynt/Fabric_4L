from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from layer1_ingestion.compliance.robots_checker import RobotsChecker
from layer1_ingestion.shared.exceptions import RobotsFetchError


@pytest.mark.asyncio
async def test_fetch_failure_permissive_mode_raises() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001", strict_mode=False)

    with patch.object(checker, "_get_robots_txt", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RobotsFetchError("timeout", domain="example.com")
        with pytest.raises(RobotsFetchError):
            await checker.check_url("https://example.com/path", job_id="job-1")


@pytest.mark.asyncio
async def test_fetch_failure_strict_mode_blocks_with_reason_code() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001", strict_mode=True)

    with patch.object(checker, "_get_robots_txt", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RobotsFetchError("timeout", domain="example.com")
        allowed, reason, rules = await checker.check_url("https://example.com/path", job_id="job-1")

    assert allowed is False
    assert "strict mode" in (reason or "").lower()
    assert rules is not None
    assert rules["reason_code"] == "ROBOTS_FETCH_ERROR"


@pytest.mark.asyncio
async def test_parse_failure_permissive_mode_allows_with_reason_code() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001", strict_mode=False)

    with patch.object(checker, "_get_robots_txt", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"content": "bad content"}
        with patch("layer1_ingestion.compliance.robots_checker.Protego.parse", side_effect=Exception("boom")):
            allowed, reason, rules = await checker.check_url("https://example.com/path", job_id="job-2")

    assert allowed is True
    assert reason is None
    assert rules is not None
    assert rules["parse_error"] == "ROBOTS_PARSE_ERROR"


@pytest.mark.asyncio
async def test_parse_failure_strict_mode_blocks_with_reason_code() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001", strict_mode=True)

    with patch.object(checker, "_get_robots_txt", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"content": "bad content"}
        with patch("layer1_ingestion.compliance.robots_checker.Protego.parse", side_effect=Exception("boom")):
            allowed, reason, rules = await checker.check_url("https://example.com/path", job_id="job-3")

    assert allowed is False
    assert "parse error" in (reason or "").lower()
    assert rules is not None
    assert rules["reason_code"] == "ROBOTS_PARSE_ERROR"
