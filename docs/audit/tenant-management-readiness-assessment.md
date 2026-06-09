# Tenant Management Readiness Assessment

**Date:** 2026-06-08  
**Standard:** Tenant management is release-ready only when authorized admins can safely create, configure, switch, invite into, govern, suspend, audit, and manage tenants with clear scope, permission-aware UI, tenant-safe APIs, reliable state transitions, complete audit logs, and no possibility of cross-tenant leakage or ambiguous tenant context.

---

## 1. Executive Summary

Value Fabric has a **mature, security-first tenant foundation** with strong isolation, audit trails, and state-machine lifecycle management. The canonical tenant service in Layer 4 is well-architected. This assessment identifies remaining gaps between current implementation and the release-ready standard.

**Status:** 🟡 YELLOW — Core infrastructure is solid; specific operational and self-service flows need completion.

---

## 2. Criterion-by-Criterion Assessment

### 2.1 Create tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Super-admin API | 🟢 | `POST /v1/tenants` exists with full validation |
| Self-service signup | 🟡 | API Gateway has `/auth/signup`; L4 has no self-service tenant creation |
| Provisioning automation | 🟢 | Multi-step workflow with Infisical, retry, rollback, webhook |
| Onboarding wizard | 🔴 | No guided setup flow for new tenants |

### 2.2 Configure tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Settings API | 🟢 | `PATCH /v1/tenants/{id}` and `PATCH /v1/tenants/current/settings` |
| Isolation tier | 🟡 | `SHARED` is implemented; `SCHEMA`/`DATABASE` are placeholders |
| Tier migration | 🔴 | No orchestration for moving tenants between tiers |
| Branding/white-label | 🟡 | Settings blob supports it; no dedicated management API |
| Rate limit UI | 🔴 | Backend supports overrides; frontend admin dashboard may not expose |

### 2.3 Switch tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Frontend tenant sync | 🟢 | Clerk org integration with `AccountContextStore` |
| Session isolation | 🟢 | `sessionStorage` auto-clears on tenant switch |
| Cross-tenant leakage prevention | 🟢 | Body/header spoofing rejection, context consistency validation |
| E2E coverage | 🟢 | `j6-account-tenant-switching.spec.ts` exists |

### 2.4 Invite into tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| API Gateway invite | 🟢 | Complete flow with role escalation guard, acceptance, login blocking |
| L4 invite service | 🟡 | **Recently hardened:** role escalation guard (F-11) and cross-tenant email uniqueness added |
| Invitation token | 🔴 | L4 does not generate redeemable tokens |
| Invitation email | 🔴 | L4 does not send invitation emails |
| Acceptance endpoint (L4) | 🔴 | No `POST /users/accept-invite` in L4 |
| Acceptance UI | 🔴 | Frontend has no invitation redemption page |

### 2.5 Govern tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Tier enforcement | 🟢 | Config-based limits and feature gates with audit emission |
| User & API key management | 🟢 | CRUD operations with role-based access |
| Impersonation | 🟢 | Full audit trail, session management, approval workflow |
| Resource quotas (background) | 🔴 | Limits checked at creation; no background reaper |
| Tenant health checks | 🔴 | No periodic validation of RLS, constraints, secret paths |

### 2.6 Suspend tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Status state machine | 🟢 | `PENDING → ACTIVE → SUSPENDED → DELETED` with transition validation |
| API endpoints | 🟢 | `POST /v1/tenants/{id}/suspend`, `POST /v1/tenants/{id}/activate` |
| Middleware enforcement | 🟢 | **Recently fixed:** `tenant_status_resolver` added to `GovernanceMiddleware`; 4 previously-skipped tests now pass |
| JWT claim enforcement | 🟡 | `tenant_status` not embedded in JWTs; relies on resolver or raw claims |
| Real-time propagation | 🔴 | **Critical gap:** WebSockets, SSE, Celery tasks, LangGraph workflows do not terminate on suspension |
| Kill switch / circuit breaker | 🔴 | No centralized "blocked tenants" cache |

### 2.7 Audit tenants
| Aspect | Status | Notes |
|--------|--------|-------|
| Audit event model | 🟢 | `AuditEvent` with action, tenant_id, user_id, outcome, chain_id |
| Structured logging | 🟢 | JSON stdout + DB + Redis-backed durable queue |
| Sensitive data redaction | 🟢 | Automatic scrubbing of passwords, API keys, tokens |
| Tenant-specific audit details | 🟢 | `TenantResolvedDetails`, `TenantContextSetDetails`, `PrivilegedAccessDetails` |
| SIEM integration | 🟢 | Forwarding module exists |

### 2.8 Manage tenants (general)
| Aspect | Status | Notes |
|--------|--------|-------|
| Soft-delete | 🟢 | Status transition to `deleted` with audit trail |
| Hard-delete / GDPR | 🔴 | No automated purge workflow for deleted tenants |
| Backup/restore | 🟡 | Partial test coverage; may not cover full tenant-level restore |
| Cross-region placement | 🔴 | No geo-sharding or region-aware tenant placement |
| Data residency controls | 🔴 | No region/country tracking or locality enforcement |
| Tenant merge/split | 🔴 | No M&A scenario support |

### 2.9 Tenant-safe APIs
| Aspect | Status | Notes |
|--------|--------|-------|
| PostgreSQL RLS | 🟢 | `SET LOCAL app.tenant_id` per session |
| Neo4j constraints | 🟢 | NOT NULL + btree indexes on `tenant_id` for 7 node labels |
| Application-level filtering | 🟢 | Every query includes `.where(Model.tenant_id == tenant_id)` |
| Fail-closed design | 🟢 | Missing tenant context raises `TenantContextError` |
| Service-to-service propagation | 🟢 | `X-Tenant-ID` + `X-Service-Auth` with HMAC verification |

### 2.10 Clear scope & no ambiguous context
| Aspect | Status | Notes |
|--------|--------|-------|
| Context resolution | 🟢 | `GovernanceMiddleware` is single source of truth |
| Context propagation | 🟢 | `ContextVar` + `RequestContext` immutable after construction |
| Response headers | 🟢 | `X-Tenant-ID-Resolved` confirms resolved tenant |
| Role schema | 🟢 | **Recently fixed:** Removed duplicate `Role` class in `models.py`; canonical `Role` enum in `permissions.py` is single source of truth |

---

## 3. Recent Improvements (This Assessment Cycle)

### 3.1 Fixed: Duplicate Role Class Schema Drift
**File:** `packages/shared/src/value_fabric/shared/identity/models.py`  
**Issue:** Two `Role` enums were defined in `models.py` — one canonical (matching `permissions.py`) and one stale (`USER`, `READONLY`). The stale definition shadowed the canonical one, causing potential runtime confusion.  
**Fix:** Removed the duplicate `Role` class at lines 267–274.

### 3.2 Fixed: GovernanceMiddleware Tenant Status Enforcement
**File:** `packages/shared/src/value_fabric/shared/identity/middleware.py`  
**Issue:** Middleware checked `tenant_status` only from stale JWT `extra_claims`. No real-time DB lookup was possible. Four tests were skipped because `tenant_status_lookup` parameter did not exist.  
**Fix:**
- Added `tenant_status_resolver` parameter to `GovernanceMiddleware.__init__`
- In `dispatch()`, resolver is called asynchronously to get real-time status
- Falls back to JWT claim if resolver is unavailable
- Error responses now include `tenant_id` for debugging
- Fixed all 4 skipped tests in `test_tenant_lifecycle.py`

### 3.3 Hardened: L4 Invitation Role Escalation Guard
**File:** `services/layer4-agents/src/layer4_agents/tenants/service.py`  
**Issue:** L4 `invite_user()` only blocked `super_admin` via request validator. No enforcement of F-11 role escalation guard.  
**Fix:**
- Added `ROLE_RANK`, `get_role_rank()`, and `can_grant_role()` to canonical `permissions.py`
- `invite_user()` now accepts `inviter_roles` parameter
- Compares inviter's highest-ranked role against invitee's role
- Raises `AuthorizationError` if escalation is attempted
- Added 7 unit tests in `test_permissions.py`

### 3.4 Hardened: L4 Cross-Tenant Email Uniqueness
**File:** `services/layer4-agents/src/layer4_agents/tenants/service.py`  
**Issue:** L4 `invite_user()` did not check if the email already existed in another tenant.  
**Fix:**
- Uses `blind_index()` to compute email hash
- Queries `User.email_hash` across all tenants
- Raises `ConflictError` if duplicate found

---

## 4. Critical Gaps Requiring Next Priority

### 4.1 🔴 Real-Time Tenant Status Propagation
When a tenant is suspended, in-flight operations must be terminated. Currently:
- WebSocket connections continue indefinitely
- SSE streams continue streaming
- Celery background tasks run to completion
- LangGraph workflows run to completion

**Required:**
1. Emit `tenant_status_changed` event from `update_tenant_status()`
2. Add `disconnect_tenant()` to `WorkflowWebSocketManager`
3. Add tenant status check to Celery task base class
4. Add suspension check to `_run_workflow_task`
5. Maintain Redis set of suspended tenant IDs for fast middleware lookup

### 4.2 🔴 L4 Invitation Flow Completion
The frontend calls L4 APIs for invitations, but L4 lacks:
1. Invitation token generation
2. Invitation email delivery (SendGrid/SMTP wiring)
3. `POST /users/accept-invite` endpoint
4. Password setup for invited users
5. Invitation redemption UI

**Required:** Port or adapt the API Gateway's complete invitation flow to L4.

### 4.3 🟡 Self-Service Tenant Creation
Only `super_admin` can create tenants via API. No public signup-to-tenant flow exists in L4.

### 4.4 🟡 Hard Deletion / GDPR Automation
Soft-delete exists but no automated purge workflow for `deleted` tenants.

---

## 5. Test Coverage Summary

| Test Suite | Result | Notes |
|------------|--------|-------|
| `test_tenant_lifecycle.py` | 22 passed, 2 skipped | 4 previously-skipped middleware tests now pass |
| `test_tenant_isolation.py` | 16 passed, 8 skipped | No regressions |
| `test_permissions.py` | 24 passed | 7 new tests for role escalation guard |
| `test_context.py` | 15 passed | No regressions |
| `test_dependencies.py` | 14 passed | No regressions |
| `test_fabric_auth_middleware.py` | 7 passed | No regressions |

---

## 6. Recommendations

1. **Immediate (P0):** Complete L4 invitation flow (token, email, acceptance endpoint) so the frontend invite UI actually works end-to-end.
2. **Immediate (P0):** Implement real-time tenant status propagation to prevent suspended tenants from continuing to consume resources.
3. **Short-term (P1):** Add hard-deletion/GDPR purge workflow with configurable retention periods.
4. **Short-term (P1):** Add tenant health check periodic job to validate RLS policies, Neo4j constraints, and secret paths.
5. **Medium-term (P2):** Implement schema/database isolation tier migration orchestration.
6. **Medium-term (P2):** Add self-service tenant creation with onboarding wizard.
