"""Add idempotency window support for scraping_jobs.

Revision ID: 016
Revises: 015
Create Date: 2026-05-25
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scraping_jobs", sa.Column("idempotency_window_start", sa.DateTime(timezone=True), nullable=True))
    op.execute("DROP INDEX IF EXISTS idx_scraping_jobs_tenant_idempotency;")
    op.execute(
        """
        CREATE UNIQUE INDEX idx_scraping_jobs_tenant_idempotency_window
        ON scraping_jobs (tenant_id, idempotency_key, idempotency_window_start)
        WHERE idempotency_key IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scraping_jobs_tenant_idempotency_window;")
    op.execute(
        """
        CREATE UNIQUE INDEX idx_scraping_jobs_tenant_idempotency
        ON scraping_jobs (tenant_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL;
        """
    )
    op.drop_column("scraping_jobs", "idempotency_window_start")
