"""
Alembic environment configuration for Layer 4 Agents.

Supports both online (sync) and offline migration modes.
Uses the DATABASE_URL_SYNC env var for the synchronous psycopg2 driver
that Alembic requires (Alembic does not support asyncpg natively).
"""

import logging
import os
import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import OperationalError

# Module-level logger for migration retry messages
logger = logging.getLogger(__name__)

# Import the declarative Base so Alembic can detect model changes
from layer4_agents.database import Base

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------

config = context.config

# Override sqlalchemy.url from environment variable if set
# Priority: LAYER4_DATABASE_URL_SYNC > LAYER4_DATABASE_URL
# NOTE: No fallback - explicit configuration required for security.
# CHECKPOINT_DATABASE_URL is deliberately NOT a fallback: it targets the
# ground_truth database (LangGraph checkpoint storage, owned by Layer 5).
# Falling back to it would silently apply the Layer 4 revision chain to a
# database Layer 4 does not own.
database_url_sync = os.environ.get(
    "LAYER4_DATABASE_URL_SYNC",
    os.environ.get("LAYER4_DATABASE_URL"),
)

if not database_url_sync:
    raise ValueError(
        "Database URL not configured. Set LAYER4_DATABASE_URL_SYNC or "
        "LAYER4_DATABASE_URL. CHECKPOINT_DATABASE_URL is not an accepted "
        "fallback: it targets the Layer 5 ground_truth database."
    )
config.set_main_option("sqlalchemy.url", database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for generating migration scripts for review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode
# ---------------------------------------------------------------------------


def _migration_retry_settings() -> tuple[int, float]:
    """Return bounded migration connection retry settings for container startup."""
    attempts = int(os.environ.get("MIGRATION_CONNECT_ATTEMPTS", "12"))
    delay_seconds = float(os.environ.get("MIGRATION_CONNECT_DELAY_SECONDS", "5"))
    return max(attempts, 1), max(delay_seconds, 0.1)


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates a synchronous engine connection and applies migrations directly. In
    compose-based live validation Postgres can be marked healthy before the
    target database accepts the first application connection, so connection
    acquisition is retried for a bounded window before Alembic fails closed.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    attempts, delay_seconds = _migration_retry_settings()
    last_error: OperationalError | None = None
    for attempt in range(1, attempts + 1):
        try:
            with connectable.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    compare_type=True,
                    compare_server_default=True,
                )

                with context.begin_transaction():
                    context.run_migrations()
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == attempts:
                break
            logger.warning(
                f"Alembic database connection failed on attempt {attempt}/{attempts}; "
                f"retrying in {delay_seconds:.1f}s..."
            )
            time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
