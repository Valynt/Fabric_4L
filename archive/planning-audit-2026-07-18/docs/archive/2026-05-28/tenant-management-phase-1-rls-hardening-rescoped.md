# Fabric 4L Tenant Management — Phase 1: RLS Hardening & Contract Alignment

**Status:** Ready for Implementation
**Replaces:** `docs/archive/tenant-management-phase-1-original-schema-per-tenant.md`

---

## 1. Objective

Phase 1 focuses on hardening the existing **Row-Level Security (RLS)** tenant isolation strategy, which has been ratified as the Enforced Canon per the Unified Recommendation memo. This phase abandons the schema-per-tenant migration in favor of strengthening the current architecture.

The goals of this phase are:
1. **Normalize Naming:** Standardize `organization_id` to `tenant_id` across all layers.
2. **Lifecycle Management:** Implement tenant status transitions (pending → active → suspended → deleted).
3. **Contract Alignment:** Update `contract.md` to reflect the ratified RLS decision and consolidate duplicate CI gates.
4. **RLS Hardening:** Ensure 100% table coverage and fix enforcement gaps in Layer 5.

---

## 2. Current State Audit & Gaps

### 2.1 Existing Infrastructure
- **RLS Session Manager:** `layer4-agents/src/database.py` (Mature, fail-safe validation)
- **RequestContext:** `shared/identity/context.py` (Complete)
- **GovernanceMiddleware:** `shared/identity/middleware.py` (Complete, handles JWT/API key resolution)

### 2.2 Identified Gaps to Fix in Phase 1
1. **Naming Inconsistencies:** Layer 1 and Layer 5 use `organization_id` instead of `tenant_id`.
2. **Layer 5 Enforcement Gap:** `layer5-ground-truth/src/layer5_ground_truth/database.py` does not execute `SET LOCAL app.tenant_id` in its `db_session()` generator, meaning RLS is not enforced at the session level.
3. **Contract Misalignment:** `contract.md` Section 2.2 still specifies `TenantAwarePool` instead of the ratified RLS pattern.
4. **Duplicate CI Gates:** Both `.github/workflows/contract-compliance.yml` and `.github/workflows/platform-contract-gate.yml` exist and overlap.
5. **Linting Conflicts:** `platform_contract_lint.py` flags `get_db_with_tenant()` as an error, which conflicts with current Layer 4 patterns.

---

## 3. Task Breakdown

### Task 1.1: Contract Alignment & CI Consolidation
**Estimated Effort:** 4 hours | **Priority:** P0

1. **Update `contract.md`:** Rewrite Section 2.2 to ratify "PostgreSQL RLS via `SET LOCAL`" as the canonical pattern. Move `TenantAwarePool` to the Target Architecture section.
2. **Consolidate CI:** Merge `platform-contract-gate.yml` into `contract-compliance.yml`. Remove the duplicate file.
3. **Scaffold Experimental:** Create `examples/experimental/tenant-aware-pool/` with a README explaining its non-blocking status.

### Task 1.2: Layer 1 Column Rename Migration
**Estimated Effort:** 4 hours | **Priority:** P1

Create Alembic migration to rename `organization_id` to `tenant_id` in Layer 1 tables (`scraping_targets`, `scraping_jobs`, `raw_content`, `extracted_data`).
- Update `services/layer1-ingestion/src/models.py`
- Update `services/layer1-ingestion/src/shared/tasks.py`
- Update Layer 1 RLS migration (`004_add_rls_policies.py`) to reference the new column name.

### Task 1.3: Layer 5 Column Rename & RLS Enforcement
**Estimated Effort:** 5 hours | **Priority:** P1

1. Create Alembic migration to rename `organization_id` to `tenant_id` in Layer 5 tables.
2. Update `services/layer5-ground-truth/src/layer5_ground_truth/models.py`.
3. **Fix Enforcement Gap:** Update `layer5_ground_truth/database.py` `db_session()` to execute `SET LOCAL app.tenant_id = :tenant_id` using the context, matching the Layer 4 pattern.

### Task 1.4: Tenant Status Lifecycle Implementation
**Estimated Effort:** 6 hours | **Priority:** P1

Implement proper status lifecycle with transition validation in `layer4-agents/src/tenants/models/tenant.py`.
- Add `TenantStatus` enum (PENDING, ACTIVE, SUSPENDED, DELETED).
- Add `status_changed_at` and `status_reason` columns.
- Implement `transition_to()` method with validation logic.

### Task 1.5: Suspended Tenant Enforcement
**Estimated Effort:** 3 hours | **Priority:** P1

Add middleware check to block suspended tenants in `shared/identity/middleware.py`.
- Query tenant status after resolving `tenant_id`.
- Raise `403 Forbidden` if suspended or pending.

### Task 1.6: RLS Coverage Audit & Completion
**Estimated Effort:** 4 hours | **Priority:** P2

Create migration `layer4-agents/migrations/versions/012_add_missing_rls.py` to ensure all tenant-scoped tables have RLS policies enabled and enforced.

### Task 1.7: Tenant Service Lifecycle Methods & API
**Estimated Effort:** 5 hours | **Priority:** P2

1. Update `layer4-agents/src/tenants/service.py` with `suspend_tenant`, `reactivate_tenant`, and `soft_delete_tenant` methods.
2. Add corresponding endpoints to `layer4-agents/src/tenants/api/routes/tenants.py` (restricted to super_admin).

### Task 1.8: Test Updates
**Estimated Effort:** 6 hours | **Priority:** P1

Update all existing tests to reflect column renames and add new tests for status lifecycle and suspended tenant blocking.

---

## 4. Execution Order

1. **Task 1.1** (Contract Alignment) — Unblocks governance.
2. **Task 1.2 & 1.3** (Column Renames & L5 Fix) — Database foundation.
3. **Task 1.4** (Status Lifecycle) — Model foundation.
4. **Task 1.5** (Middleware Enforcement) — Security enforcement.
5. **Task 1.7** (Service & API) — Control plane.
6. **Task 1.6** (RLS Audit) — Cleanup.
7. **Task 1.8** (Tests) — Validation.

---

## 5. Acceptance Criteria

1. `contract.md` accurately reflects RLS as the Enforced Canon.
2. Only one contract compliance CI workflow exists.
3. All `organization_id` columns renamed to `tenant_id` in Layers 1 and 5.
4. Layer 5 `db_session()` correctly executes `SET LOCAL app.tenant_id`.
5. Tenant status transitions validated (invalid transitions rejected).
6. Suspended tenants receive 403 Forbidden at the middleware level.
7. All tenant-scoped tables have RLS policies.
8. All tests pass.
