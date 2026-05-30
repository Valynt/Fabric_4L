# services/api migrations

Phase 1 of the Clerk + Fabric4L integration ships its baseline schema as
plain SQL (`versions/0001_clerk_auth_baseline.sql`). The gateway today
runs against the in-memory persistence layer in
`app/core/database.py`; once it adopts PostgreSQL these files will be
wrapped by an Alembic revision so they participate in the per-service
"exactly one head" governance enforced by `make check-migration-heads`.

Until then this directory is the **canonical DDL artifact** for:

- `users`
- `tenants`
- `tenant_memberships`
- `account_memberships`     (Phase-1 schema only; enforced in Phase 3)
- `tenant_entitlements`     (Phase-1 schema only; enforced in Phase 3)
- `auth_audit_events`       (append-only; populated in Phase 4)
- `clerk_webhook_events`    (webhook idempotency dedupe)
- `fabric_api_records`      (P0-01 JSONB bridge facade for API gateway domain objects)

Every tenant-scoped table enables RLS with the canonical
`tenant_id = current_setting('app.tenant_id', true)` predicate.
`fabric_api_records` also forces RLS for table owners and applies the same
predicate as both `USING` and `WITH CHECK`, so reserved tenant keywords such
as `admin`, `internal`, and `system` do not bypass write isolation. The
`apply_tenant_rls` helper in `value_fabric.shared.identity.fabric_auth.rls`
sets that GUC from the verified `AuthContext` envelope on each request.
