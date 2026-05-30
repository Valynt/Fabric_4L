"""Force RLS on fabric_api_records tenant policy.

Revision ID: 6f3b9c2d4a91
Revises: 2be6428bc79b
Create Date: 2026-05-30

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6f3b9c2d4a91"
down_revision = "2be6428bc79b"
branch_labels = None
depends_on = None


_UP_SQL = """
-- Fail closed even for table owners; application sessions must always satisfy
-- the tenant predicate set by app.tenant_id.
ALTER TABLE fabric_api_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE fabric_api_records FORCE ROW LEVEL SECURITY;

-- Do not allow admin/internal/system string bypasses for writes.  A privileged
-- maintenance session that needs to repair another tenant's row must SET LOCAL
-- app.tenant_id to that explicit tenant rather than relying on a reserved GUC
-- value supplied by application code.
DROP POLICY IF EXISTS fabric_api_records_tenant_isolation ON fabric_api_records;
CREATE POLICY fabric_api_records_tenant_isolation ON fabric_api_records
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
"""

_DOWN_SQL = """
DROP POLICY IF EXISTS fabric_api_records_tenant_isolation ON fabric_api_records;
CREATE POLICY fabric_api_records_tenant_isolation ON fabric_api_records
    USING (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE fabric_api_records NO FORCE ROW LEVEL SECURITY;
"""


def upgrade() -> None:
    op.execute(_UP_SQL)


def downgrade() -> None:
    op.execute(_DOWN_SQL)
