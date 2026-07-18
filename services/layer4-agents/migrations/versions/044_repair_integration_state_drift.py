"""Repair Integration reducer columns drifted by scheduler bypasses.

PR 2 introduced reducer columns (observed_sync_status, operational_status,
last_known_good_at, error_class) but PR 2.1 is the first change that routes
all scheduler/job-runner status writes through the reducer. Between those two
deployments, direct sync_status assignments may have left reducer fields
stale or contradictory. This migration idempotently re-derives the reducer
columns from the legacy sync_status column and last_successful_sync_at,
without ever clearing last_known_good_at.

Revision ID: 044_repair_integration_state_drift
Revises: 043_add_integration_operational_status_fields
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "044_repair_integration_state_drift"
down_revision: Union[str, None] = "043_add_integration_operational_status_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The derived operational_status mapping is intentionally the same logic
    # used in migration 043 so the repair is idempotent and consistent.
    op.execute(
        """
        WITH repair AS (
            SELECT
                id,
                CASE
                    WHEN sync_status = 'active' THEN 'ready'
                    WHEN sync_status = 'failed' AND last_successful_sync_at IS NOT NULL THEN 'degraded'
                    WHEN sync_status = 'failed' THEN 'blocked'
                    WHEN sync_status = 'running' THEN 'running'
                    WHEN sync_status = 'pending' THEN 'idle'
                    WHEN sync_status = 'degraded' THEN 'degraded'
                    WHEN sync_status = 'idle' THEN 'ready'
                    ELSE sync_status
                END AS new_operational_status,
                CASE
                    WHEN sync_status = 'active' THEN 'ready'
                    WHEN sync_status = 'failed' THEN 'failure'
                    WHEN sync_status = 'running' THEN 'running'
                    WHEN sync_status = 'pending' THEN 'idle'
                    WHEN sync_status = 'degraded' THEN 'partial'
                    WHEN sync_status = 'idle' THEN 'success'
                    ELSE sync_status
                END AS new_observed_sync_status,
                CASE
                    WHEN sync_status IN ('active', 'idle') THEN 'none'
                    WHEN sync_status = 'failed' AND last_successful_sync_at IS NOT NULL THEN 'transient'
                    WHEN sync_status = 'failed' THEN 'permanent'
                    WHEN sync_status = 'degraded' THEN 'transient'
                    WHEN sync_status = 'running' THEN 'none'
                    WHEN sync_status = 'pending' THEN 'none'
                    ELSE 'none'
                END AS new_error_class
            FROM integrations
        ),
        updated AS (
            UPDATE integrations i
            SET
                operational_status = r.new_operational_status,
                observed_sync_status = r.new_observed_sync_status,
                error_class = r.new_error_class,
                last_known_good_at = COALESCE(i.last_known_good_at, i.last_successful_sync_at)
            FROM repair r
            WHERE i.id = r.id
              AND (
                  COALESCE(i.operational_status, '') != r.new_operational_status
                  OR COALESCE(i.observed_sync_status, '') != r.new_observed_sync_status
                  OR COALESCE(i.error_class, '') != r.new_error_class
                  OR i.last_known_good_at IS NULL
              )
            RETURNING i.id
        )
        SELECT COUNT(*) AS repaired_rows FROM updated
        """
    )


def downgrade() -> None:
    # This is a data-repair migration; downgrade is a no-op. Reverting the
    # schema is handled by migration 043's downgrade.
    pass
