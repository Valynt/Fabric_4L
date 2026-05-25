"""Add idempotency_key to scraping_jobs.

Revision ID: 015
Revises: 014
Create Date: 2026-05-25
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add idempotency_key column and partial unique index."""
    op.add_column("scraping_jobs", op.Column("idempotency_key", op.String(255), nullable=True))

    # Partial unique index: only enforce uniqueness when idempotency_key is present
    op.execute("""
        CREATE UNIQUE INDEX idx_scraping_jobs_tenant_idempotency
        ON scraping_jobs (tenant_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL;
    """)


def downgrade() -> None:
    """Remove idempotency_key."""
    op.execute("DROP INDEX IF EXISTS idx_scraping_jobs_tenant_idempotency;")
    op.drop_column("scraping_jobs", "idempotency_key")
