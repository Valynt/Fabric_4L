"""Unit tests for Neo4j driver management."""

from unittest.mock import AsyncMock, MagicMock, patch

import layer6_benchmarks.database as db_module
import pytest
from layer6_benchmarks.database import close_driver, create_driver, get_driver, health_check
from neo4j.exceptions import AuthError, ServiceUnavailable, TransientError

# Capture the real health_check before conftest's autouse mock_neo4j_health fixture patches it.
_real_health_check = health_check


class TestCreateDriver:
    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self) -> None:
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()

        settings = MagicMock()
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_auth = ("neo4j", "password")
        settings.neo4j_max_pool_size = 10

        with patch(
            "layer6_benchmarks.database.AsyncGraphDatabase.driver",
            side_effect=[TransientError("conn lost"), mock_driver],
        ) as mock_db_driver:
            with patch("layer6_benchmarks.database.asyncio.sleep", new_callable=AsyncMock):
                driver = await create_driver(settings)

        assert driver is mock_driver
        assert mock_db_driver.call_count == 2

    @pytest.mark.asyncio
    async def test_fails_fast_on_auth_error(self) -> None:
        settings = MagicMock()
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_auth = ("neo4j", "wrong")
        settings.neo4j_max_pool_size = 10

        with patch(
            "layer6_benchmarks.database.AsyncGraphDatabase.driver",
            return_value=AsyncMock(
                verify_connectivity=AsyncMock(side_effect=AuthError("bad auth"))
            ),
        ):
            with pytest.raises(Exception) as exc_info:
                await create_driver(settings)
            assert "auth failed" in str(exc_info.value).lower() or "Neo4j auth failed" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_exhausts_retries(self) -> None:
        settings = MagicMock()
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.neo4j_auth = ("neo4j", "password")
        settings.neo4j_max_pool_size = 10

        with patch(
            "layer6_benchmarks.database.AsyncGraphDatabase.driver",
            side_effect=ServiceUnavailable("down"),
        ) as mock_db_driver:
            with patch("layer6_benchmarks.database.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ServiceUnavailable) as exc_info:
                    await create_driver(settings)

        assert mock_db_driver.call_count == 5
        assert "unreachable after 5 attempts" in str(exc_info.value)


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_healthy_on_success(self) -> None:
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"check": 1})
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        settings = MagicMock()
        settings.neo4j_database = "neo4j"

        with patch("layer6_benchmarks.database.get_driver", return_value=mock_driver):
            result = await _real_health_check(settings)

        assert result == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_returns_unhealthy_on_exception(self) -> None:
        with patch(
            "layer6_benchmarks.database.get_driver",
            side_effect=ServiceUnavailable("down"),
        ):
            result = await _real_health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestSingleton:
    @pytest.mark.asyncio
    async def test_get_driver_returns_singleton(self) -> None:
        mock_driver = AsyncMock()

        with patch.object(db_module, "_driver", None):
            with patch.object(
                db_module, "create_driver", new_callable=AsyncMock, return_value=mock_driver
            ) as mock_create:
                driver1 = await get_driver()
                driver2 = await get_driver()
                assert driver1 is driver2
                mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_driver_clears_singleton(self) -> None:
        mock_driver = AsyncMock()

        with patch.object(db_module, "_driver", mock_driver):
            await close_driver()
            mock_driver.close.assert_awaited_once()
            assert db_module._driver is None
