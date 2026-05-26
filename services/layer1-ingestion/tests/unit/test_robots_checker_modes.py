from unittest.mock import AsyncMock, patch

import pytest

from value_fabric.layer1.compliance.robots_checker import RobotsChecker
from value_fabric.layer1.shared.exceptions import RobotsFetchError


@pytest.mark.asyncio
async def test_permissive_mode_reraises_fetch_errors():
    checker = RobotsChecker(strict_mode=False)
    checker.strict_robots_enforcement = False

    with patch.object(checker, "_get_robots_txt", new=AsyncMock(side_effect=RobotsFetchError("boom", domain="example.com"))):
        with pytest.raises(RobotsFetchError):
            await checker.check_url("https://example.com/path")


@pytest.mark.asyncio
async def test_strict_enforcement_blocks_on_fetch_errors():
    checker = RobotsChecker(strict_mode=False)
    checker.strict_robots_enforcement = True

    with patch.object(checker, "_get_robots_txt", new=AsyncMock(side_effect=RobotsFetchError("boom", domain="example.com"))):
        allowed, reason, rules = await checker.check_url("https://example.com/path")

    assert allowed is False
    assert "strict enforcement" in reason
    assert rules["reason_code"] == "ROBOTS_FETCH_FAILED_STRICT"


@pytest.mark.asyncio
async def test_permissive_mode_allows_parse_failures_with_reason_code():
    checker = RobotsChecker(strict_mode=False)
    checker.strict_robots_enforcement = False

    with patch.object(checker, "_get_robots_txt", new=AsyncMock(return_value={"content": "User-agent: *"})):
        with patch("value_fabric.layer1.compliance.robots_checker.Protego.parse", side_effect=ValueError("parse fail")):
            allowed, reason, rules = await checker.check_url("https://example.com/path")

    assert allowed is True
    assert reason is None
    assert rules["reason_code"] == "ROBOTS_PARSE_FAILED"


@pytest.mark.asyncio
async def test_strict_enforcement_blocks_parse_failures():
    checker = RobotsChecker(strict_mode=False)
    checker.strict_robots_enforcement = True

    with patch.object(checker, "_get_robots_txt", new=AsyncMock(return_value={"content": "User-agent: *"})):
        with patch("value_fabric.layer1.compliance.robots_checker.Protego.parse", side_effect=ValueError("parse fail")):
            allowed, reason, rules = await checker.check_url("https://example.com/path")

    assert allowed is False
    assert "strict enforcement" in reason
    assert rules["reason_code"] == "ROBOTS_PARSE_FAILED"


@pytest.mark.asyncio
async def test_compliance_log_emitted_for_network_failures():
    checker = RobotsChecker(tenant_id="11111111-1111-1111-1111-111111111111", strict_mode=False)
    checker.strict_robots_enforcement = True

    with patch.object(checker, "_get_robots_txt", new=AsyncMock(side_effect=RobotsFetchError("network", domain="example.com"))):
        with patch.object(checker.logger, "warning") as warning_log:
            await checker.check_url("https://example.com/path")

    warning_log.assert_any_call(
        "Robots compliance failure enforced",
        domain="example.com",
        job_id=None,
        tenant_id="11111111-1111-1111-1111-111111111111",
        decision="blocked",
        reason_code="ROBOTS_FETCH_FAILED_STRICT",
    )
