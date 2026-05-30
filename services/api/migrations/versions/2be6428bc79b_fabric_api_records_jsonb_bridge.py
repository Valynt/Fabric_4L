"""Fabric API records JSONB bridge.

Revision ID: 2be6428bc79b
Revises: f94ebc1a1c0f
Create Date: 2026-05-20

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "2be6428bc79b"
down_revision = "f94ebc1a1c0f"
branch_labels = None
depends_on = None


_UP_SQL = """
-- fabric_api_records (JSONB bridge for API-level data)
CREATE TABLE IF NOT EXISTS fabric_api_records (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    record_key TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, record_type, record_key)
);

CREATE INDEX IF NOT EXISTS fabric_api_records_tenant_idx
    ON fabric_api_records (tenant_id);

CREATE INDEX IF NOT EXISTS fabric_api_records_type_idx
    ON fabric_api_records (record_type);

CREATE INDEX IF NOT EXISTS fabric_api_records_key_idx
    ON fabric_api_records (record_key);

CREATE INDEX IF NOT EXISTS fabric_api_records_payload_idx
    ON fabric_api_records USING GIN (payload);
"""

_DOWN_SQL = """
DROP INDEX IF EXISTS fabric_api_records_payload_idx;
DROP INDEX IF EXISTS fabric_api_records_key_idx;
DROP INDEX IF EXISTS fabric_api_records_type_idx;
DROP INDEX IF EXISTS fabric_api_records_tenant_idx;
DROP TABLE IF EXISTS fabric_api_records CASCADE;
"""


def upgrade() -> None:
    op.execute(_UP_SQL)


def downgrade() -> None:
    op.execute(_DOWN_SQL)
