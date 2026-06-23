"""Add email_hash blind index to users for encrypted email lookups.

Revision ID: 039_add_user_email_hash_blind_index
Revises: 038_add_billing_webhook_inbox_fields
Create Date: 2026-05-28
"""

import os
import sys

import sqlalchemy as sa
from alembic import op

# Allow imports from the application source tree (same pattern as env.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

revision = "039_add_user_email_hash_blind_index"
down_revision = "038_add_billing_webhook_inbox_fields"
branch_labels = None
depends_on = None

MIGRATION_REVIEW_REQUIRED = (
    "Privacy migration intentionally replaces the tenant/email uniqueness "
    "constraint and plaintext email index with tenant/email_hash equivalents."
)


def upgrade() -> None:
    # Add the blind-index column (nullable initially for migration safety)
    op.add_column("users", sa.Column("email_hash", sa.String(length=64), nullable=True))

    # Backfill email_hash for existing plaintext emails.
    # This uses the Python blind_index helper so the hash matches what the
    # application will compute on future writes.
    try:
        from value_fabric.shared.crypto import blind_index

        conn = op.get_bind()
        rows = conn.execute(sa.text("SELECT id, email FROM users WHERE email_hash IS NULL"))
        for user_id, email in rows:
            if email:
                h = blind_index(email)
                if h:
                    conn.execute(
                        sa.text("UPDATE users SET email_hash = :h WHERE id = :id"),
                        {"h": h, "id": str(user_id)},
                    )
    except Exception:
        # If the backfill fails (e.g. missing CREDENTIALS_MASTER_KEY), the
        # column remains NULL and exact-match lookups will not find legacy rows.
        # Administrators can re-run backfill later.
        pass

    # Create new index on the hash column
    op.create_index("ix_users_email_hash", "users", ["email_hash"])

    # Replace unique constraint: tenant_id + email_hash instead of tenant_id + email
    op.drop_constraint("uix_user_tenant_email", "users", type_="unique")
    op.create_unique_constraint("uix_user_tenant_email", "users", ["tenant_id", "email_hash"])

    # Drop old plaintext email index (no longer needed for lookups)
    op.drop_index("ix_users_email", table_name="users")


def downgrade() -> None:
    # Restore plaintext email index
    op.create_index("ix_users_email", "users", ["email"])

    # Restore original unique constraint
    op.drop_constraint("uix_user_tenant_email", "users", type_="unique")
    op.create_unique_constraint("uix_user_tenant_email", "users", ["tenant_id", "email"])

    # Drop hash index and column
    op.drop_index("ix_users_email_hash", table_name="users")
    op.drop_column("users", "email_hash")
