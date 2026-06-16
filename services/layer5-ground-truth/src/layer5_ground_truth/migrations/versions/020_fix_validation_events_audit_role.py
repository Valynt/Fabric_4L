"""Allow the local application role to append validation_events.

In local/development deployments the Layer 5 service connects as the Postgres
superuser. The append-only trigger installed by migration 010 only permitted
'system_role' and 'admin_role', which blocked legitimate truth-object creation.
This migration adds the application role to the allowlist without weakening the
update/delete protections.

Revision ID: 020
Revises: 019
Create Date: 2026-06-16
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

ALLOWED_USERS = "'system_role', 'admin_role', 'postgres'"


def upgrade() -> None:
    op.execute(f"""
    CREATE OR REPLACE FUNCTION l5_block_audit_mutation() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ({ALLOWED_USERS}) THEN
            RAISE EXCEPTION 'validation_events is append-only for role %', current_user;
        END IF;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute(f"""
    CREATE OR REPLACE FUNCTION l5_require_privileged_audit_insert() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ({ALLOWED_USERS}) THEN
            RAISE EXCEPTION 'validation_events inserts require privileged service account role';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute(f"""
    CREATE OR REPLACE FUNCTION l5_block_audit_mutation() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ('system_role', 'admin_role') THEN
            RAISE EXCEPTION 'validation_events is append-only for role %', current_user;
        END IF;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute(f"""
    CREATE OR REPLACE FUNCTION l5_require_privileged_audit_insert() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ('system_role', 'admin_role') THEN
            RAISE EXCEPTION 'validation_events inserts require privileged service account role';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
