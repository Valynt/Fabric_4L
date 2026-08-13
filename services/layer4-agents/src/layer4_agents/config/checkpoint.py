from __future__ import annotations

"""LangGraph checkpoint configuration for Postgres persistence.

Provides AsyncPostgresSaver configuration for durable workflow state storage,
enabling pause/resume and human-in-the-loop capabilities.
"""
import asyncio
import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from langgraph.checkpoint.base import BaseCheckpointSaver
from value_fabric.shared.security.config import is_production_like_environment

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)


class CheckpointConnectionError(Exception):
    """Raised when checkpoint database connection fails."""

    pass


class CheckpointConfig:
    """Configuration for LangGraph checkpoint storage.

    Uses PostgreSQL for durable checkpoint persistence. Workflows can be
    resumed from their last checkpoint after interruptions or restarts.

    Environment Variables:
        CHECKPOINT_DATABASE_URL: Postgres connection URL (defaults to ground_truth DB)

    Example:
        >>> from src.config.checkpoint import CheckpointConfig
        >>> async with CheckpointConfig.get_saver() as saver:
        ...     workflow = BaseWorkflow(config, tool_registry, saver)
        ...     result = await workflow.run(initial_state, thread_id="wf-123")
    """

    @classmethod
    def get_database_url(cls) -> str:
        """Get checkpoint database URL from environment."""
        url = (
            os.getenv("CHECKPOINT_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or "postgresql://localhost/value_fabric_checkpoints"
        )
        if not url:
            raise RuntimeError(
                "CHECKPOINT_DATABASE_URL environment variable is required. "
                "Set it to a valid PostgreSQL connection string."
            )
        return url

    @classmethod
    def _clean_url(cls, url: str) -> str:
        """Convert SQLAlchemy-style URL to plain postgresql:// format.

        Handles various driver suffixes that SQLAlchemy uses but psycopg/asyncpg
        don't need in the connection string.

        Args:
            url: SQLAlchemy-style database URL

        Returns:
            Plain postgresql:// URL
        """
        # Remove any driver suffix after postgresql+ (e.g., +asyncpg, +psycopg2, +pg8000)
        cleaned = re.sub(
            r"^postgresql\+[^/]+://",
            "postgresql://",
            url.strip(),
            flags=re.IGNORECASE,
        )
        return cleaned

    @classmethod
    async def create_saver(cls) -> AsyncPostgresSaver:
        """Create and initialize AsyncPostgresSaver.

        Creates a psycopg async connection for LangGraph's AsyncPostgresSaver.
        Caller is responsible for closing the connection when done.

        Returns:
            Configured AsyncPostgresSaver instance with an active connection.
            The connection is stored in the saver for later cleanup.

        Raises:
            ConnectionError: If database connection fails

        Example:
            >>> saver = await CheckpointConfig.create_saver()
            >>> try:
            ...     # Use saver
            ...     pass
            ... finally:
            ...     await saver.conn.close()
        """
        # Lazy imports to avoid import-time dependencies
        import psycopg
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        url = cls._clean_url(cls.get_database_url())
        conn = await psycopg.AsyncConnection.connect(
            url, row_factory=psycopg.rows.dict_row, autocommit=True, prepare_threshold=0
        )
        saver = AsyncPostgresSaver(conn)
        # LangGraph requires setup() once per database to provision the
        # checkpoints/checkpoint_writes/... tables. It is idempotent and
        # cheap, so run it on every startup connection rather than relying
        # on an external provisioning step that does not exist.
        await saver.setup()
        # Store connection reference for cleanup only if the saver does not
        # already expose it via a public attribute.
        if not hasattr(saver, "conn"):
            saver._conn = conn
        return saver

    @classmethod
    async def close_saver(cls, saver: AsyncPostgresSaver | None) -> None:
        """Close the connection associated with a checkpoint saver.

        Args:
            saver: The saver to close, or None (no-op)
        """
        if saver is None:
            return
        # Attempt to close via public attribute first, then private fallback.
        connection = getattr(saver, "conn", None) or getattr(saver, "_conn", None)
        if connection is not None:
            try:
                await connection.close()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass  # Already closed or never fully connected

    @classmethod
    @asynccontextmanager
    async def get_saver(cls) -> AsyncGenerator[AsyncPostgresSaver, None]:
        """Context manager for short-lived checkpoint saver usage.

        Automatically handles connection cleanup on exit.
        Use this for one-off operations; for long-lived usage, use create_saver()
        and call close_saver() manually.

        Example:
            >>> async with CheckpointConfig.get_saver() as saver:
            ...     # Use saver within context
            ...     pass
        """
        # Lazy imports to avoid import-time dependencies
        import psycopg
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        conn = None
        try:
            url = cls._clean_url(cls.get_database_url())
            conn = await psycopg.AsyncConnection.connect(
                url, row_factory=psycopg.rows.dict_row, autocommit=True, prepare_threshold=0
            )
            saver = AsyncPostgresSaver(conn)
            yield saver
        except psycopg.Error as e:
            logger.error(f"Failed to connect to checkpoint database: {e}")
            raise CheckpointConnectionError(f"Database connection failed: {e}") from e
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating checkpoint saver: {e}")
            raise CheckpointConnectionError(f"Failed to initialize checkpoint saver: {e}") from e
        finally:
            if conn:
                try:
                    await conn.close()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass  # Already closed or never connected


async def get_checkpoint_saver() -> BaseCheckpointSaver | None:
    """Factory function for dependency injection.

    Returns a checkpoint saver if CHECKPOINT_DATABASE_URL is configured,
    otherwise returns None (no checkpointing).

    Note: This silently handles connection failures to allow graceful degradation
    in development/testing environments. For explicit error handling in production,
    use CheckpointConfig.create_saver() directly.

    Returns:
        AsyncPostgresSaver instance or None if unavailable/unconfigured
    """
    environment = os.getenv("ENVIRONMENT") or os.getenv("ENV") or os.getenv("APP_ENV")

    # Skip if no database URL configured (explicit opt-out in development/test only)
    if not os.getenv("CHECKPOINT_DATABASE_URL"):
        if is_production_like_environment(environment):
            raise CheckpointConnectionError(
                "CHECKPOINT_DATABASE_URL is required in production-like environments"
            )
        logger.debug("Checkpointing disabled: CHECKPOINT_DATABASE_URL not set")
        return None

    try:
        saver = await CheckpointConfig.create_saver()
        return saver
    except CheckpointConnectionError:
        if is_production_like_environment(environment):
            raise
        return None
    except asyncio.CancelledError:
        raise
    except Exception as e:
        if is_production_like_environment(environment):
            raise CheckpointConnectionError(
                f"Failed to initialize production checkpoint saver: {e}"
            ) from e
        # Unexpected failure - log for debugging but don't crash
        logger.warning(
            f"Checkpointing unavailable due to unexpected error: {type(e).__name__}: {e}"
        )
        return None
