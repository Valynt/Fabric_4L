"""Add tenant_registry system table for maintenance enumeration.

Revision ID: 014
Revises: 013
Create Date: 2026-05-25
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant_registry and seed from existing scraping_jobs."""
    op.create_table(
        "tenant_registry",
        Column("tenant_id", UUID(as_uuid=True), primary_key=True),
        Column("registered_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("last_activity_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("is_active", Boolean, nullable=False, server_default="true"),
    )

    # Seed with distinct tenant_ids from scraping_jobs
    op.execute("""
        INSERT INTO tenant_registry (tenant_id, registered_at, last_activity_at, is_active)
        SELECT DISTINCT tenant_id, MIN(created_at), MAX(created_at), true
        FROM scraping_jobs
        WHERE tenant_id IS NOT NULL
        GROUP BY tenant_id
        ON CONFLICT (tenant_id) DO UPDATE SET
            last_activity_at = EXCLUDED.last_activity_at,
            is_active = true;
    """)

    # tenant_registry is explicitly NOT covered by RLS — it is a system table


def downgrade() -> None:
    """Drop tenant_registry."""
    op.drop_table("tenant_registry")
