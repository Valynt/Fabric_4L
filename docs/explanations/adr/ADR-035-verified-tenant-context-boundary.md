---
title: "ADR-035: Verified Tenant Context Boundary"
category: "architecture"
audience: "advanced"
last-reviewed: "2026-07-20"
freshness: "current"
related: ["../../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy", "../../explanations/adr/ADR-028-tenant-context-ratification", "../../explanations/adr/ADR-034-request-context-contract"]
---

# ADR-035: Verified Tenant Context Boundary

**Status:** Accepted — partially implemented

**Date:** 2026-07-20

**Deciders:** Platform Engineering, Security Team

---

## Context

Fabric 4L enforces multi-tenant isolation through a combination of authentication,
tenant context propagation, and database-level Row-Level Security. ADR-010
established PostgreSQL RLS as the database isolation mechanism. ADR-028
ratified the canonical tenant context propagation pattern (AsyncLocalStorage /
contextvars with middleware injection). ADR-034 defined the RequestContext
contract shape.

However, the boundary between credential verification and tenant context
construction has never been formally documented as an architectural decision.
The current codebase has a `get_verified_tenant_id()` dependency in some
endpoints and `extract_tenant_from_bearer` / `TenantBearerContext` in others,
but adoption is not uniform across all layers. Repowise `get_why()` identified
the tenant context extraction refactor (commit `2303200e`) and the verified
tenant ID dependency as "proposed" decisions from git archaeology — evidence of
implicit practice, not formal approval.

This ADR ratifies and unifies these practices into a single, durable
architectural boundary.

## Decision

### Architectural Rule

Tenant request context may be constructed only from cryptographically verified
authentication claims. Every endpoint that reads, writes, schedules, publishes,
caches, or otherwise acts on tenant-scoped resources must require verified
tenant context. Request-supplied tenant identifiers are selectors only and must
be authorized against the verified security context.

### Credential-to-Context Pipeline

The system constructs tenant request context through four distinct stages:

1. **Token extraction:** Obtain the bearer credential from the request (header,
   cookie, or API key). This stage performs no trust establishment.
2. **Cryptographic verification:** Validate signature, issuer, audience,
   expiry, and algorithm. An unverified token must never produce trusted
   tenant context.
3. **Tenant claim validation:** Validate presence, syntax, and authorization
   of the tenant claim within the verified token.
4. **Context construction:** Create a trusted RequestContext (per ADR-034)
   from the verified claims.

A function that merely extracts tenant information from an unverified token
must never produce trusted tenant context.

### Endpoint Classification

Not every authenticated endpoint operates on tenant-owned data. The system
defines four endpoint classes:

| Class | Description | Tenant Context Required | Examples |
|---|---|---|---|
| **Public** | No authentication required | No | Health, readiness, auth callbacks |
| **Authenticated principal-only** | User-scoped, no tenant data access | No | User profile, user settings |
| **Tenant-scoped** | Reads/writes/caches tenant-owned resources | Yes | All CRUD on tenant resources |
| **Privileged cross-tenant** | Admin/control-plane operations | Separate privileged dependency + audit | Tenant management, support operations |

Cross-tenant operations require a separate privileged dependency and audit
path, not an exception to tenant verification.

### HTTP Status Semantics

| Status | Meaning |
|---|---|
| 401 Unauthorized | Credentials absent, malformed, expired, or cryptographically invalid |
| 403 Forbidden | Credentials valid but principal lacks access to requested tenant or operation |
| 400 Bad Request | Tenant ID missing or syntactically invalid in request structure |
| 404 Not Found | Resource not found or intentionally hidden (tenant-scoped 403 may map to 404 to prevent enumeration) |

### Request-Supplied Tenant Identifiers

Request-supplied tenant identifiers (e.g., path parameter `/tenants/{tenant_id}/resources`)
are selectors only. They must be compared with, or authorized against, the
verified security context. They must never establish authority.

### PostgreSQL RLS Bridge

Verified request context enters the database session through a canonical
transaction/session boundary (e.g., `SET LOCAL app.tenant_id`). This is a
required bridge between the FastAPI dependency injection layer and PostgreSQL
RLS policies — it is not an automatic side-effect of dependency injection.

Tenant context is transaction-scoped and must not persist across pooled
connection reuse. The connection pool must reset transaction-local settings
between checkouts.

### Non-PostgreSQL Storage Surfaces

PostgreSQL RLS does not protect Neo4j, Redis, object storage, queues, search
indexes, or observability data. Each storage surface requires its own explicit
tenant-boundary mechanism:

- **Neo4j:** See ADR-036 (Tenant-Bound Graph Query Execution)
- **Redis, object storage, queues, search indexes:** Future ADRs or engineering standards
- **Observability data:** Tenant ID in structured logs; access controls on query interfaces

## Alternatives Considered

### Application-level filtering only

- **Pros:** Simple to implement; no database-level configuration needed.
- **Cons:** Developer error risk (forgetting `WHERE tenant_id = X`); no protection from direct database access; fails compliance audits requiring database-level controls.
- **Why rejected:** ADR-010 already rejected this approach with a detailed comparison matrix. Defense in depth requires database-level enforcement.

### Separate database per tenant

- **Pros:** Strongest isolation guarantee; no RLS overhead.
- **Cons:** High operational overhead (connection management, backups, migrations); resource fragmentation; complex cross-tenant analytics; higher infrastructure costs.
- **Why rejected:** ADR-010 comparison matrix demonstrated cost and operational disadvantages at current scale.

### Request-supplied tenant ID as authority

- **Pros:** Simpler API design; no need for verified context propagation.
- **Cons:** Enables tenant spoofing — any client can claim any tenant ID; no cryptographic binding between identity and tenant.
- **Why rejected:** Fundamental security violation; incidents INC-2026-0412 and INC-2026-0614 (documented in ADR-028) demonstrated this failure mode.

### Single middleware without endpoint classification

- **Pros:** Uniform enforcement; no need to classify endpoints.
- **Cons:** Overbroad — not all authenticated endpoints operate on tenant data (health, user profile, auth callbacks); blanket requirement creates false positives and migration friction.
- **Why rejected:** Endpoint classification is necessary to apply tenant context requirements precisely without blocking legitimate non-tenant-scoped endpoints.

### Conditions for revisiting

- If the platform moves to a separate-database-per-tenant model (ADR-010 revisit), the RLS bridge section would need revision.
- If a new storage surface is added, a corresponding tenant-boundary mechanism must be defined before it stores tenant data.

## Consequences

### Positive

- **Single canonical boundary:** Credential verification, tenant validation, and context construction are unified into one documented pipeline.
- **Fails-closed:** Missing or invalid authentication returns 401; valid authentication without tenant authorization returns 403. No fallback to unauthenticated context.
- **Defense in depth:** Tenant isolation enforced at dependency injection, database (RLS), and static analysis layers.
- **No tenant spoofing:** Request-supplied tenant IDs are selectors, never authority.
- **Precise endpoint classification:** Non-tenant-scoped endpoints are not blocked by tenant context requirements.

### Negative

- **Migration burden:** Existing endpoints without verified tenant context dependency must be updated. Adoption is not yet uniform across all layers.
- **No anonymous tenant-scoped endpoints:** Any endpoint requiring tenant data access must authenticate and verify tenant context.
- **Multi-surface enforcement:** Each non-PostgreSQL storage surface requires its own tenant-boundary mechanism — this ADR does not cover them all.

## Compliance and Migration

### Existing noncompliant paths

Endpoints that operate on tenant-scoped data but do not yet declare verified
tenant context are identified by security test suites. Known gaps exist in
some Layer 3 and Layer 6 endpoints.

### Migration owner

Platform Engineering

### Enforcement mechanism

- **Runtime:** RLS policies fail-closed when tenant context is absent (exists, per ADR-010).
- **Static analysis:** Planned — endpoint classification coverage verification.
- **CI gate:** `mandatory-security-regression` (planned enhancement to verify endpoint classification).

### Exception process

Privileged cross-tenant endpoints are documented via a separate privileged
dependency with audit logging. These are not exceptions — they are a distinct,
audited endpoint class.

### Rollback strategy

N/A — this is a ratification of existing architecture, not a new pattern.
Non-compliant endpoints are migrated incrementally.

### Evidence required to transition to Accepted (fully implemented)

- All tenant-scoped endpoints declare verified tenant context dependency
- RLS tests pass for all tenant-scoped tables
- No endpoint accepts request-supplied tenant ID as authority
- Test proving tenant context does not persist across pooled connection reuse

## Current Enforcement (Exists)

- PostgreSQL RLS policies with `SET LOCAL app.tenant_id` (ADR-010)
- `get_verified_tenant_id()` FastAPI dependency (partial adoption)
- `extract_tenant_from_bearer` / `TenantBearerContext` (Layer 3)
- `tests/security/test_cross_tenant_api.py` — cross-tenant isolation tests
- `test_rls_enforcement.py` — RLS policy enforcement tests

## Planned Enforcement (Not Yet Existing)

- Static analysis pass verifying endpoint classification coverage
- Test proving tenant context does not persist across pooled connection reuse
- CI gate enhancement for endpoint classification verification

## References

- ADR-010: PostgreSQL RLS for Multi-Tenancy (database enforcement)
- ADR-028: Tenant Context Propagation Contract (mechanics of context propagation)
- ADR-034: RequestContext Contract Definition (context shape and fields)
- ADR-036: Tenant-Bound Graph Query Execution (Neo4j enforcement)
- `packages/shared/src/value_fabric/shared/identity/middleware.py` (current implementation)
- `services/layer3-knowledge/src/api/auth_context.py` (current implementation example)
- Commit `2303200e`: Tenant context extraction refactor
