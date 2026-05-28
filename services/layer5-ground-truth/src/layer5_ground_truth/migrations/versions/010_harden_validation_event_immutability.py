"""Harden ValidationEvent immutability with triggers and RLS policies.

This migration adds:
1. PostgreSQL trigger to prevent UPDATE/DELETE on validation_events table
2. Row-level security (RLS) policy to restrict writes to admin role only
3. Similar protections for maturity_history table

Issue B: Audit log tamper resistance is not proven
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "010_harden_validation_event_immutability"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trigger function to prevent updates/deletes on validation_events
    validation_event_trigger = """
    CREATE OR REPLACE FUNCTION prevent_validation_event_modification()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'ValidationEvent records are immutable and cannot be modified or deleted';
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """
    op.execute(validation_event_trigger)

    # Create trigger to prevent updates on validation_events
    op.execute("""
        CREATE TRIGGER validation_event_update_protection
        BEFORE UPDATE ON validation_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_validation_event_modification();
    """)

    # Create trigger to prevent deletes on validation_events
    op.execute("""
        CREATE TRIGGER validation_event_delete_protection
        BEFORE DELETE ON validation_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_validation_event_modification();
    """)

    # Similar protection for maturity_history
    maturity_history_trigger = """
    CREATE OR REPLACE FUNCTION prevent_maturity_history_modification()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'MaturityHistory records are immutable and cannot be modified or deleted';
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """
    op.execute(maturity_history_trigger)

    op.execute("""
        CREATE TRIGGER maturity_history_update_protection
        BEFORE UPDATE ON maturity_history
        FOR EACH ROW
        EXECUTE FUNCTION prevent_maturity_history_modification();
    """)

    op.execute("""
        CREATE TRIGGER maturity_history_delete_protection
        BEFORE DELETE ON maturity_history
        FOR EACH ROW
        EXECUTE FUNCTION prevent_maturity_history_modification();
    """)

    # Enable RLS on validation_events (if not already enabled)
    op.execute("ALTER TABLE validation_events ENABLE ROW LEVEL SECURITY")

    # Create RLS policy to prevent any writes to validation_events except by admin
    # Note: This assumes an 'admin' role exists. Adjust role name as needed.
    op.execute("""
        CREATE POLICY validation_events_readonly_policy
        ON validation_events
        FOR ALL
        TO PUBLIC
        USING (true)
        WITH CHECK (false);
    """)

    # Enable RLS on maturity_history
    op.execute("ALTER TABLE maturity_history ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY maturity_history_readonly_policy
        ON maturity_history
        FOR ALL
        TO PUBLIC
        USING (true)
        WITH CHECK (false);
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS validation_event_update_protection ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS validation_event_delete_protection ON validation_events")
    op.execute("DROP TRIGGER IF EXISTS maturity_history_update_protection ON maturity_history")
    op.execute("DROP TRIGGER IF EXISTS maturity_history_delete_protection ON maturity_history")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS prevent_validation_event_modification()")
    op.execute("DROP FUNCTION IF EXISTS prevent_maturity_history_modification()")

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS validation_events_readonly_policy ON validation_events")
    op.execute("DROP POLICY IF EXISTS maturity_history_readonly_policy ON maturity_history")

    # Disable RLS
    op.execute("ALTER TABLE validation_events DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE maturity_history DISABLE ROW LEVEL SECURITY")
