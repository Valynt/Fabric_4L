"""Neo4j driver management for Layer 6 Benchmark Service."""



from __future__ import annotations

import asyncio
import logging

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import AuthError, ConfigurationError, ServiceUnavailable, TransientError

from .config import Settings, get_settings

logger = logging.getLogger(__name__)



_driver: AsyncDriver | None = None





async def create_driver(settings: Settings | None = None) -> AsyncDriver:

    """Create and verify a Neo4j async driver with retry logic."""

    cfg = settings or get_settings()

    max_attempts = 5

    base_delay = 1.0



    for attempt in range(1, max_attempts + 1):

        try:

            driver = AsyncGraphDatabase.driver(

                cfg.neo4j_uri,

                auth=cfg.neo4j_auth,

                max_connection_pool_size=cfg.neo4j_max_pool_size,

                connection_timeout=10.0,

            )

            await driver.verify_connectivity()

            logger.info("Neo4j driver connected on attempt %d", attempt)

            return driver

        except AuthError as exc:

            logger.error("Neo4j auth failed: %s", exc)

            raise ConfigurationError(f"Neo4j auth failed: {exc}") from exc

        except ConfigurationError:

            logger.error("Neo4j configuration error")

            raise

        except (ServiceUnavailable, TransientError) as exc:

            if attempt == max_attempts:

                logger.error("Neo4j unreachable after %d attempts", max_attempts)

                raise ServiceUnavailable(f"Neo4j unreachable after {max_attempts} attempts") from exc

            delay = base_delay * (2 ** (attempt - 1))

            logger.warning("Neo4j connection attempt %d failed, retrying in %.1fs", attempt, delay)

            await asyncio.sleep(delay)



    raise ServiceUnavailable("Neo4j driver could not be created")





async def get_driver(settings: Settings | None = None) -> AsyncDriver:

    """Return singleton Neo4j driver, creating if necessary."""

    global _driver

    if _driver is None:

        _driver = await create_driver(settings)

    return _driver





async def close_driver() -> None:

    """Close the singleton driver."""

    global _driver

    if _driver is not None:

        await _driver.close()

        _driver = None

        logger.info("Neo4j driver closed")





async def health_check(settings: Settings | None = None) -> dict[str, str]:

    """Check Neo4j connectivity without raising."""

    cfg = settings or get_settings()

    try:

        driver = await get_driver(cfg)

        async with driver.session(database=cfg.neo4j_database) as session:

            result = await session.run("RETURN 1 AS check")

            record = await result.single()

            if record and record["check"] == 1:

                return {"status": "healthy", "uri": cfg.neo4j_uri}

        return {"status": "unhealthy", "error": "Unexpected query result"}

    except Exception as exc:
        logger.error("Neo4j health check failed: %s", exc)
        return {"status": "unhealthy", "error": "Neo4j health check failed"}

