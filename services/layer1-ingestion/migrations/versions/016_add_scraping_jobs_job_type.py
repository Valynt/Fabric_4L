"""Add job_type to scraping_jobs.

Revision ID: 016
Revises: 015
Create Date: 2026-06-01
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add job_type column, backfill from configuration JSON, then enforce non-nullable."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("scraping_jobs")]

    # Add column initially nullable so backfill can run without errors.
    if "job_type" not in columns:
        op.add_column(
            "scraping_jobs",
            sa.Column("job_type", sa.String(50), nullable=True),
        )

    # Backfill: prefer configuration['job_type'] when present, fallback to model default.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            UPDATE scraping_jobs
            SET job_type = COALESCE(configuration->>'job_type', 'generic_scrape')
            WHERE job_type IS NULL
            """
        )
    else:
        # SQLite / generic dialect path
        metadata = sa.MetaData()
        table = sa.Table("scraping_jobs", metadata, autoload_with=bind)
        conn = bind
        for row in conn.execute(table.select().where(table.c.job_type.is_(None))):
            config = row.configuration or {}
            job_type = config.get("job_type") if isinstance(config, dict) else None
            if not job_type:
                job_type = "generic_scrape"
            conn.execute(
                table.update().where(table.c.id == row.id).values(job_type=job_type)
            )

    # Enforce non-nullable with server default to match the ScrapingJob model.
    op.alter_column(
        "scraping_jobs",
        "job_type",
        existing_type=sa.String(50),
        nullable=False,
        server_default="generic_scrape",
    )


def downgrade() -> None:
    """Remove job_type column."""
    op.drop_column("scraping_jobs", "job_type")
