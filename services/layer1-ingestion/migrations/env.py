"""Alembic environment configuration."""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add paths so imports match Docker layout:
# - shared.* -> packages/shared/src/value_fabric/shared
# - layer1_ingestion.* -> layer1-ingestion/src/layer1_ingestion
layer1_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
value_fabric_root = os.path.abspath(os.path.join(layer1_root, '..'))

# Add layer1-ingestion/src so canonical imports work
layer1_src = os.path.join(layer1_root, 'src')
if layer1_src not in sys.path:
    sys.path.insert(0, layer1_src)

# Add value-fabric root so 'shared' resolves correctly
if value_fabric_root not in sys.path:
    sys.path.insert(0, value_fabric_root)

# Import models using canonical layer1_ingestion.shared path
from layer1_ingestion.shared.config import settings
from layer1_ingestion.shared.models import Base

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with environment variable
config.set_main_option('sqlalchemy.url', settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
