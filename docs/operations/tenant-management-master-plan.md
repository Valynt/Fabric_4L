# Fabric 4L Tenant Management — Rescoped Implementation Plans

Rescope tenant management phases based on actual codebase capabilities: RLS-based isolation is mature (not schema-per-tenant), OIDC is generic (not Keycloak-specific), and tier-aware routing already exists but only 'shared' tier is implemented.

---

## Executive Summary

The original proposal incorrectly assumed:
- `fastapi-tenancy` library was in use (it is not — custom RLS implementation exists)
- Keycloak was the identity provider (generic OIDC is implemented)
- Stripe billing was present (no billing integration exists)
- Schema-per-tenant was ready for Phase 1 (code shows it as future work with HTTP 501)

**Rescoped Approach:**
- **Phase 1**: Harden existing RLS-based isolation, normalize naming, enhance tenant registry
- **Phase 2**: Automated provisioning with existing Infisical + OIDC integrations
- **Phase 3**: Self-service control plane APIs with schema-per-tenant as Phase 4+ consideration

---

## Phase 1: RLS Hardening & Tenant Registry Enhancement

### Objective
Stabilize and enhance the existing RLS-based tenant isolation. Normalize column naming inconsistencies. Strengthen the tenant registry with lifecycle management. Keep schema-per-tenant as a future tier option (the architecture already supports this via `isolation_tier` field).

### 1.1 Current State Audit

**Verified Existing Infrastructure:**

| Component | Location | Status |
|-----------|----------|--------|
| RLS Session Management | `layer4-agents/src/database.py` | ✅ Mature, with fail-safe validation |
| Tenant Model | `layer4-agents/src/tenants/models/tenant.py` | ✅ Exists with `isolation_tier` field |
| RequestContext | `shared/identity/context.py` | ✅ Supports shared/schema/database tiers |
| Tier-aware Routing | `database.py:get_tiered_db_session()` | ✅ Framework exists, only 'shared' implemented |
| OIDC Client | `shared/identity/oidc.py` | ✅ Generic OIDC with python-jose |
| Infisical Config | `.infisical.json` | ✅ Configured for all environments |

**Naming Inconsistencies to Fix:**

| Layer | Current Column | Should Be | Files Affected |
|-------|---------------|-----------|----------------|
| Layer 1 | `organization_id` | `tenant_id` | ScrapingTarget, ScrapingJob, RawContent |
| Layer 5 | `organization_id` | `tenant_id` | TruthObject, TruthSource, ModelVersion |

### 1.2 Tasks

#### Task 1.1: Normalize Column Names (Layer 1)
**Estimated Effort:** 4 hours

Create migration to rename `organization_id` to `tenant_id` in Layer 1 tables. Update ORM models and Celery task references.

**Modified Files:**
- `services/layer1-ingestion/migrations/versions/006_rename_org_to_tenant.py` (new)
- `services/layer1-ingestion/src/models.py` (update column references)
- `services/layer1-ingestion/src/shared/tasks.py` (update queries)

#### Task 1.2: Normalize Column Names (Layer 5)
**Estimated Effort:** 3 hours

Create migration to rename `organization_id` to `tenant_id` in Layer 5 tables. Update ORM models.

**Modified Files:**
- `services/layer5-ground-truth/.../migrations/versions/004_rename_org_to_tenant.py` (new)
- `services/layer5-ground-truth/.../models.py` (update column references)

#### Task 1.3: Implement Tenant Status Lifecycle
**Estimated Effort:** 4 hours

Add proper tenant status management: `pending` → `active` → `suspended` → `deleted`. Add suspension checks to middleware.

**Modified Files:**
- `services/layer4-agents/src/layer4_agents/tenants/models/tenant.py` (add status transitions)
- `packages/shared/src/value_fabric/shared/identity/middleware.py` (add suspended tenant check)
- `services/layer4-agents/src/layer4_agents/tenants/service.py` (add lifecycle methods)

#### Task 1.4: Enhance RLS Policies
**Estimated Effort:** 6 hours

Review and harden existing RLS policies. Add missing tables. Ensure admin bypass policies work correctly.

**Audit Current RLS:**
- Layer 1: 8 tables covered (`004_add_rls_policies.py`)
- Layer 4: 8 tables covered (`007_add_rls_policies.py`)
- Layer 5: 7 tables covered (`002_add_rls_policies.py`, `003_add_model_registry.py`)

**New Migration:**
- `services/layer4-agents/migrations/versions/012_add_missing_rls.py` (cover any uncovered tables)

#### Task 1.5: Tenant Context Validation
**Estimated Effort:** 3 hours

Strengthen the existing tenant context validation. Add metrics for tenant context violations.

**Modified Files:**
- `services/layer4-agents/src/database.py` (enhance validate_tenant_id)
- `packages/shared/src/value_fabric/shared/identity/middleware.py` (add validation metrics)

#### Task 1.6: Create Tenant Provisioning Skeleton
**Estimated Effort:** 2 hours

Create the service structure for tenant provisioning (without full automation yet).

**New Files:**
- `services/layer4-agents/src/layer4_agents/tenants/provisioning.py` (skeleton service)
- `services/layer4-agents/src/layer4_agents/tenants/constants.py` (status enums, defaults)

### 1.3 Acceptance Criteria

1. All `organization_id` columns renamed to `tenant_id` in Layers 1 and 5
2. Tenant status lifecycle (pending → active → suspended → deleted) implemented
3. Suspended tenants blocked at middleware level
4. All tenant-scoped tables have RLS policies
5. No regression in existing tenant isolation tests
6. `isolation_tier` field remains in schema (future-proofing for Phase 4+)

### 1.4 File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `layer1-ingestion/migrations/versions/006_rename_org_to_tenant.py` | Rename column migration |
| **Create** | `layer5-ground-truth/.../migrations/versions/004_rename_org_to_tenant.py` | Rename column migration |
| **Create** | `layer4-agents/migrations/versions/012_add_missing_rls.py` | Add missing RLS policies |
| **Create** | `layer4-agents/src/tenants/provisioning.py` | Provisioning service skeleton |
| **Create** | `layer4-agents/src/tenants/constants.py` | Tenant constants |
| **Modify** | `layer4-agents/src/tenants/models/tenant.py` | Add status lifecycle |
| **Modify** | `shared/identity/middleware.py` | Add suspension checks |
| **Modify** | `layer4-agents/src/tenants/service.py` | Add lifecycle methods |
| **Modify** | `layer1-ingestion/src/models.py` | Update column references |
| **Modify** | `layer1-ingestion/src/shared/tasks.py` | Update queries |

---

## Phase 2: Automated Provisioning Pipeline

### Objective
Build automated tenant onboarding using existing infrastructure: Infisical for secrets, generic OIDC for identity. No external IdP automation (Keycloak) — instead, integrate with existing OIDC workflows.

### 2.1 Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use existing Infisical | Already configured in `.infisical.json` |
| Use generic OIDC | Already implemented in `shared/identity/oidc.py` |
| No Keycloak automation | No Keycloak in codebase; adding would be new vendor dependency |
| No Stripe integration | Not in current codebase; defer to future billing phase |
| Webhook-based provisioning | Layer 4 exposes API for external provisioning triggers |

### 2.2 Tasks

#### Task 2.1: Infisical Integration Service
**Estimated Effort:** 6 hours

Create service to programmatically create tenant secret paths in Infisical.

**New File:** `packages/shared/src/value_fabric/shared/secrets/tenant_secrets.py`

```python
"""Tenant-scoped secrets management via Infisical."""

class TenantSecretsService:
    """Manages secret paths for tenant provisioning."""

    async def create_tenant_path(self, tenant_slug: str) -> str:
        """Create /tenants/{tenant_slug} path in Infisical."""

    async def seed_default_secrets(self, tenant_slug: str) -> None:
        """Seed default configuration values."""
```

**Dependencies:** Infisical API credentials already in environment.

#### Task 2.2: OIDC Realm/Client Configuration Guide
**Estimated Effort:** 2 hours

Document how to configure new OIDC clients for tenants (manual or via IdP APIs).

**New File:** `docs/operations/tenant-oidc-configuration.md`

Contents:
- OIDC discovery URL format
- Client registration process
- Claim mapping for tenant_id
- Role mapping configuration

#### Task 2.3: Tenant Provisioning API
**Estimated Effort:** 8 hours

Implement the provisioning orchestration endpoint.

**Modified File:** `services/layer4-agents/src/layer4_agents/tenants/api/routes/tenants.py`

New endpoints:
- `POST /tenants` — Create tenant (super_admin only)
- `POST /tenants/{id}/provision` — Trigger provisioning workflow
- `GET /tenants/{id}/provision-status` — Check provisioning status

**Workflow:**
1. Create tenant record (status=pending)
2. Create Infisical secret path
3. Seed default secrets
4. Update status to active
5. Emit audit event

#### Task 2.4: Provisioning Webhook Handler
**Estimated Effort:** 4 hours

Create endpoint for external systems to trigger tenant provisioning.

**New File:** `services/layer4-agents/src/layer4_agents/tenants/api/routes/provisioning_webhook.py`

```python
@router.post("/webhooks/provision-tenant")
async def provision_tenant_webhook(
    payload: ProvisionWebhookPayload,
    signature: str = Header(..., alias="X-Webhook-Signature"),
):
    """Receive provisioning triggers from external systems."""
```

#### Task 2.5: Provisioning Audit Events
**Estimated Effort:** 3 hours

Add comprehensive audit logging for provisioning operations.

**Modified Files:**
- `shared/audit/models.py` (add provisioning actions)
- `layer4-agents/src/tenants/provisioning.py` (emit audit events)

#### Task 2.6: Provisioning Tests
**Estimated Effort:** 6 hours

Create integration tests for provisioning workflow.

**New File:** `tests/integration/test_tenant_provisioning.py`

### 2.3 Acceptance Criteria

1. `POST /tenants` creates tenant with status=pending
2. Provisioning workflow creates Infisical path and seeds secrets
3. Webhook endpoint accepts external provisioning triggers
4. All provisioning steps emit audit events
5. Failed provisioning can be retried
6. Integration tests pass with test Infisical instance

### 2.4 File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `shared/secrets/tenant_secrets.py` | Infisical integration service |
| **Create** | `docs/operations/tenant-oidc-configuration.md` | OIDC setup guide |
| **Create** | `layer4-agents/src/tenants/api/routes/provisioning_webhook.py` | Webhook handler |
| **Create** | `tests/integration/test_tenant_provisioning.py` | Integration tests |
| **Modify** | `layer4-agents/src/tenants/provisioning.py` | Full provisioning implementation |
| **Modify** | `layer4-agents/src/tenants/api/routes/tenants.py` | Add provisioning endpoints |
| **Modify** | `shared/audit/models.py` | Add provisioning audit actions |

---

## Phase 3: Self-Service Control Plane

### Objective
Deliver user-facing APIs for tenant management: registration, admin dashboard, usage metrics. Schema-per-tenant remains a future Phase 4+ consideration.

### 3.1 Design Decisions

| Feature | Phase 3 Approach | Future Phase 4+ |
|---------|-----------------|-----------------|
| Tenant Isolation | RLS (enhanced in Phase 1) | Schema-per-tenant (when needed) |
| Billing | Usage metrics only | Stripe integration (if required) |
| Subscription Tiers | Config-based (JSON/YAML) | Database-driven with billing |
| Admin Dashboard | Read-only metrics | Full CRUD operations |

### 3.2 Tasks

#### Task 3.1: Subscription Tier Configuration
**Estimated Effort:** 3 hours

Create tier definitions without billing integration.

**New File:** `services/layer4-agents/src/layer4_agents/tenants/tiers.py`

```python
TIERS = {
    "free": {"max_users": 5, "max_agents": 2, "rate_limit": 100},
    "basic": {"max_users": 20, "max_agents": 10, "rate_limit": 1000},
    "pro": {"max_users": 100, "max_agents": 50, "rate_limit": 10000},
    "enterprise": {"max_users": None, "max_agents": None, "rate_limit": None},
}
```

#### Task 3.2: Tier Enforcement Middleware
**Estimated Effort:** 4 hours

Add tier-based limits to existing middleware.

**Modified File:** `shared/identity/middleware.py`

Add checks for:
- Max users per tenant
- Max agents per tenant
- Rate limits

#### Task 3.3: Usage Metrics Collection
**Estimated Effort:** 6 hours

Implement usage tracking for billing preparation.

**New File:** `services/layer4-agents/src/layer4_agents/tenants/usage.py`

Track:
- Agent executions per tenant
- Token consumption (LLM calls)
- Storage usage (Neo4j nodes, PostgreSQL rows)
- API request counts

#### Task 3.4: Tenant Admin Dashboard API
**Estimated Effort:** 8 hours

Create endpoints for tenant admin dashboard.

**New File:** `services/layer4-agents/src/layer4_agents/tenants/api/routes/admin.py`

Endpoints:
- `GET /tenants/{id}/users` — List tenant users
- `GET /tenants/{id}/usage` — Usage metrics
- `GET /tenants/{id}/settings` — Tenant settings
- `PATCH /tenants/{id}/settings` — Update settings
- `GET /tenants/{id}/audit-log` — Tenant-scoped audit events

#### Task 3.5: Tenant Registration API
**Estimated Effort:** 6 hours

Public endpoint for tenant self-registration.

**Modified File:** `services/layer4-agents/src/layer4_agents/tenants/api/routes/registration.py`

Endpoints:
- `POST /tenants/register` — Submit registration
- `POST /tenants/verify-email` — Verify email address
- `GET /tenants/validate-subdomain` — Check subdomain availability

**Workflow:**
1. Collect org name, admin email, desired subdomain
2. Validate subdomain uniqueness
3. Send verification email
4. On verification, trigger provisioning (Phase 2 workflow)

#### Task 3.6: API Key Management Enhancements
**Estimated Effort:** 4 hours

Enhance existing API key system for tenant self-service.

**Modified File:** `services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py`

Add:
- Tenant admin can create/revoke keys
- Key expiration settings
- Last used tracking

#### Task 3.7: Control Plane Tests
**Estimated Effort:** 6 hours

E2E tests for control plane functionality.

**New File:** `tests/e2e/test_tenant_control_plane.py`

### 3.3 Acceptance Criteria

1. Users can register tenants via API
2. Email verification triggers provisioning
3. Tenant admins can view usage metrics
4. Tier limits enforced at middleware level
5. API keys manageable by tenant admins
6. Audit log shows tenant-scoped events

### 3.4 File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `layer4-agents/src/tenants/tiers.py` | Tier definitions |
| **Create** | `layer4-agents/src/tenants/usage.py` | Usage tracking |
| **Create** | `layer4-agents/src/tenants/api/routes/admin.py` | Admin dashboard API |
| **Create** | `layer4-agents/src/tenants/api/routes/registration.py` | Registration endpoints |
| **Create** | `tests/e2e/test_tenant_control_plane.py` | E2E tests |
| **Modify** | `shared/identity/middleware.py` | Add tier enforcement |
| **Modify** | `layer4-agents/src/tenants/api/routes/api_keys.py` | Enhance key management |

---

## Phase 4+: Future Considerations (Out of Scope)

### Schema-per-Tenant Migration
When enterprise customers require strict isolation:
- Leverage existing `isolation_tier` field (already in Tenant model)
- Implement `schema` tier in `get_tiered_db_session()`
- Create per-schema migration runner
- Migrate tenants individually

### Billing Integration
If monetization is required:
- Stripe integration for subscription management
- Invoice generation based on Phase 3 usage metrics
- Automated tier upgrades/downgrades

### Advanced IdP Integration
If specific IdP automation needed:
- Keycloak realm provisioning
- Auth0 organization management
- Azure AD tenant provisioning

---

## Document Locations

Upon approval, these documents should be moved to:

| Document | Target Location |
|----------|-----------------|
| Phase 1 Plan (rescoped) | `docs/operations/tenant-management-phase-1-rls-hardening.md` |
| Phase 2 Plan (new) | `docs/operations/tenant-management-phase-2-provisioning.md` |
| Phase 3 Plan (new) | `docs/operations/tenant-management-phase-3-control-plane.md` |
| Original Phase 1 (deprecated) | `docs/archive/tenant-management-phase-1-original-schema-per-tenant.md` |
| Original Project Plan (deprecated) | `docs/archive/tenant-management-project-plan-original.md` |

---

## Verification Checklist

- [ ] `fastapi-tenancy` removed from all recommendations
- [ ] Keycloak references removed
- [ ] Stripe references removed (or marked Phase 4+)
- [ ] Schema-per-tenant moved to Phase 4+
- [ ] All references align with actual codebase (`database.py`, `oidc.py`, `context.py`)
- [ ] File paths use actual project structure
- [ ] Acceptance criteria are measurable
