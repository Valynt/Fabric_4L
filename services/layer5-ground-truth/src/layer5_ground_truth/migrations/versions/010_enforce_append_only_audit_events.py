"""Enforce append-only guarantees for audit/event tables.

Revision ID: 010
Revises: 009
Create Date: 2026-05-25
"""

from alembic import op

revision = "010b"
down_revision = "010a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION l5_block_audit_mutation() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ('system_role', 'admin_role') THEN
            RAISE EXCEPTION 'validation_events is append-only for role %', current_user;
        END IF;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION l5_require_privileged_audit_insert() RETURNS trigger AS $$
    BEGIN
        IF current_user NOT IN ('system_role', 'admin_role') THEN
            RAISE EXCEPTION 'validation_events inserts require privileged service account role';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_no_update ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_no_delete ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_privileged_insert ON validation_events")

    op.execute("""
    CREATE TRIGGER trg_validation_events_no_update
    BEFORE UPDATE ON validation_events
    FOR EACH ROW EXECUTE FUNCTION l5_block_audit_mutation()
    """)
    op.execute("""
    CREATE TRIGGER trg_validation_events_no_delete
    BEFORE DELETE ON validation_events
    FOR EACH ROW EXECUTE FUNCTION l5_block_audit_mutation()
    """)
    op.execute("""
    CREATE TRIGGER trg_validation_events_privileged_insert
    BEFORE INSERT ON validation_events
    FOR EACH ROW EXECUTE FUNCTION l5_require_privileged_audit_insert()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_no_update ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_no_delete ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS trg_validation_events_privileged_insert ON validation_events")
    op.execute("DROP FUNCTION IF EXISTS l5_block_audit_mutation()")
    op.execute("DROP FUNCTION IF EXISTS l5_require_privileged_audit_insert()")
