# Tenant Isolation Governance Rule

Tenant isolation is an absolute invariant across all layers of Value Fabric.

## Invariants
1. **Authenticated Context**: Every request must extract `tenant_id` from authenticated context (JWT, claims, or verified session), NEVER trusting unvalidated request bodies or client query parameters.
2. **Database Queries**: Every repository method, SQL query, and Neo4j graph query MUST filter by `tenant_id`.
3. **PostgreSQL RLS**: Row-Level Security (RLS) policies must never be bypassed or disabled.
4. **Cross-Tenant Prevention**: Tenant A must never be able to read, mutate, or observe data belonging to Tenant B.
5. **Fail-Closed Default**: Requests lacking valid tenant context must fail closed immediately with `401 Unauthorized` or `403 Forbidden`.

## Hostile Testing
- All service changes touching data models must include cross-tenant access regression tests (`pytest -m tenant_boundary`).
