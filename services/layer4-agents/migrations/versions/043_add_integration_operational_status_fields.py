"""Add observed/operational status fields to integrations.

Introduces the state-reducer columns that separate what the sync engine
observed from the operational status derived by the reducer:
- observed_sync_status: raw outcome of the last sync event
- operational_status: derived, stable state shown to users
- last_known_good_at: timestamp of the last fully successful sync
- error_class: taxonomy class of the most recent failure

The legacy sync_status column is kept as a read shim and backfilled from
the new operational_status values.

Revision ID: 043_add_integration_operational_status_fields
Revises: 042_add_api_key_revoked_at_creator
Create Date: 2026-07-14
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "043_add_integration_operational_status_fields"
down_revision: Union[str, None] = "042_add_api_key_revoked_at_creator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "integrations",
        sa.Column(
            "observed_sync_status",
            sa.String(32),
            nullable=True,
            comment="Raw outcome observed from the last sync/connection event.",
        ),
    )
    op.add_column(
        "integrations",
        sa.Column(
            "operational_status",
            sa.String(32),
            nullable=True,
            comment="Derived, stable operational state produced by the reducer.",
        ),
    )
    op.add_column(
        "integrations",
        sa.Column(
            "last_known_good_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of the last fully successful sync.",
        ),
    )
    op.add_column(
        "integrations",
        sa.Column(
            "error_class",
            sa.String(64),
            nullable=True,
            comment="Taxonomy class of the most recent failure.",
        ),
    )

    op.execute(
        """
        UPDATE integrations
        SET observed_sync_status = CASE
            WHEN sync_status = 'active' THEN 'ready'
            WHEN sync_status = 'failed' THEN 'failure'
            WHEN sync_status = 'running' THEN 'running'
            WHEN sync_status = 'pending' THEN 'idle'
            WHEN sync_status = 'degraded' THEN 'partial'
            ELSE sync_status
        END,
        operational_status = CASE
            WHEN sync_status = 'active' THEN 'ready'
            WHEN sync_status = 'failed' AND last_successful_sync_at IS NOT NULL THEN 'degraded'
            WHEN sync_status = 'failed' THEN 'blocked'
            WHEN sync_status = 'running' THEN 'running'
            WHEN sync_status = 'pending' THEN 'idle'
            WHEN sync_status = 'degraded' THEN 'degraded'
            ELSE sync_status
        END,
        last_known_good_at = last_successful_sync_at
        """
    )

    op.create_index(
        "ix_integrations_operational_status",
        "integrations",
        ["operational_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_integrations_operational_status", table_name="integrations")
    op.drop_column("integrations", "error_class")
    op.drop_column("integrations", "last_known_good_at")
    op.drop_column("integrations", "operational_status")
    op.drop_column("integrations", "observed_sync_status")
