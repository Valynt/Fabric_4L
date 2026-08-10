-- =============================================================================n-- 0002_fabric_api_records_jsonb_bridge.sqln--n-- Bridge-facade table for the standalone API gateway (P0-01).n-- Stores domain records as JSONB payloads with composite key scoping.n--n-- RLS is enabled (and FORCED) so that even if a query predicate is bypassed,n-- the database layer fails closed on tenant isolation.n--n-- POLICY NOTE (aligned with Alembic revision 6f3b9c2d4a91): the policyn-- intentionally has NO admin/internal/system GUC bypass. A privilegedn-- maintenance session that needs to repair another tenant's row mustn-- SET LOCAL app.tenant_id to that explicit tenant; reserved GUC valuesn-- supplied by application code are not an escape hatch.n-- =============================================================================n
BEGIN;

CREATE TABLE IF NOT EXISTS fabric_api_records (
    table_name  TEXT NOT NULL,
    id          TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT '',
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (table_name, tenant_id, id)
);

CREATE INDEX IF NOT EXISTS fabric_api_records_tenant_idx
    ON fabric_api_records (table_name, tenant_id, id);

-- Enable and FORCE RLS on the bridge table: application sessions (including
-- the table owner) must always satisfy the tenant predicate.
ALTER TABLE fabric_api_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE fabric_api_records FORCE ROW LEVEL SECURITY;

-- Drop and recreate the policy so migrations are idempotent.
-- Fail closed: only rows for the explicitly-set tenant are visible/writable.
DROP POLICY IF EXISTS fabric_api_records_tenant_isolation ON fabric_api_records;
CREATE POLICY fabric_api_records_tenant_isolation ON fabric_api_records
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
