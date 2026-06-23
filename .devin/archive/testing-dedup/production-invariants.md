# Production Invariants - Fabric 4L

**Document:** Production Security & Isolation Invariants  
**Version:** 2026-04-28  
**Author:** Autonomous Test Assurance Agent  

---

## Tenant Isolation

### Rule: No Cross-Tenant Data Access
**Statement:** Users can only read/write data belonging to their authenticated tenant.

**Enforcement Points:**
1. **Middleware Level:** `shared/identity/middleware.py:GovernanceMiddleware` validates JWT tenant claims
2. **API Level:** Layer routes use `Depends(get_current_tenant)` dependencies
3. **Database Level:** RLS policies on PostgreSQL tables (via SQLAlchemy query filters)

**Code Paths:**
- `shared/identity/middleware.py:282-309` - Unauthenticated request rejection
- `shared/identity/middleware.py:312-334` - Tenant status validation (suspended/pending/deleted)
- `shared/identity/middleware.py:657-679` - JWT/header tenant consistency validation

**Tests:**
- `tests/security/test_tenant_isolation.py` - Cross-tenant access prevention
- `tests/security/test_rls_enforcement.py` - DB-level RLS enforcement

---

## Authentication

### Rule: No Unauthenticated Access to Protected Resources
**Statement:** All protected endpoints require valid JWT or API key authentication.

**Enforcement Points:**
1. **Middleware:** `GovernanceMiddleware._authenticate()` extracts and validates credentials
2. **Token Format:** Bearer JWT or API key (`vf_*` prefix)
3. **Token Validation:** Signature verification via `shared/identity/jwt.py:decode_jwt()`

**Code Paths:**
- `shared/identity/middleware.py:419-480` - Authentication logic
- `shared/identity/middleware.py:532-557` - API key extraction
- `shared/identity/jwt.py` - JWT decode and validation

**Tests:**
- `tests/security/test_adversarial_auth.py` - 20 negative auth tests
- `tests/security/test_oidc.py` - OIDC flow tests

---

## Authorization

### Rule: No Authorization Bypass
**Statement:** Role-based permissions are enforced; no header/body/param can override.

**Enforcement Points:**
1. **Role Resolution:** `middleware.py` extracts roles from JWT
2. **Permission Derivation:** `shared/identity/permissions.py:get_permissions_for_role()`
3. **RBAC Enforcement:** Route decorators check `context.permissions`

**Code Paths:**
- `shared/identity/middleware.py:458-462` - Permission derivation from roles
- `shared/identity/permissions.py` - Role-to-permission mapping

**Tests:**
- `tests/security/test_rbac.py` - Role-based access control tests

---

## Input Validation

### Rule: No Unvalidated Input Reaches Persistence/LLM
**Statement:** All inputs validated via Pydantic schemas before processing.

**Enforcement Points:**
1. **Schema Validation:** FastAPI Pydantic models on request bodies
2. **Query Validation:** `layer3-knowledge/src/security/query_validator.py` for Neo4j queries
3. **Sanitization:** XSS/Injection filters in input handlers

**Code Paths:**
- `layer3-knowledge/src/security/query_validator.py` - Graph query validation
- `shared/identity/middleware.py:594-595` - User ID XSS check

**Tests:**
- `tests/security/test_input_validation.py` - Input sanitization tests
- `tests/security/test_injection.py` - Injection attack tests

---

## Secrets Protection

### Rule: No Secrets in Logs/Errors/Responses
**Statement:** API keys, tokens, passwords redacted from all outputs.

**Enforcement Points:**
1. **Audit Logging:** `shared/audit/emitter.py` with automatic redaction
2. **Error Handling:** `shared/error_handling/` with safe error responses
3. **Response Filtering:** Pydantic `SecretStr` types

**Tests:**
- `tests/security/test_secrets_protection.py` - Secret exposure prevention

---

## Rate Limiting

### Rule: No Unbounded Request Rates
**Statement:** Per-tenant rate limiting enforced with Redis in multi-worker deployments.

**Enforcement Points:**
1. **In-Memory:** Per-process rate limiting for dev/test
2. **Redis-Backed:** Distributed rate limiting for production
3. **Multi-Worker Safety:** Fails if Redis unavailable in multi-worker mode

**Code Paths:**
- `shared/identity/middleware.py:336-356` - Rate limit enforcement
- `shared/identity/middleware.py:102-151` - Redis rate limiting
- `shared/identity/middleware.py:177-228` - In-memory rate limiting

**Tests:**
- `tests/test_tenant_rate_limiting.py` - Rate limiting behavior

---

## Tenant Lifecycle

### Rule: No Access for Suspended/Deleted/Pending Tenants
**Statement:** Tenant status checked before request processing.

**Status Codes:**
- `suspended` → 403 with "tenant_suspended" error
- `pending` → 403 with "tenant_pending" error
- `deleted` → 404 (don't reveal existence)

**Code Paths:**
- `shared/identity/middleware.py:312-334` - Tenant status enforcement

---

## WebSocket Security

### Rule: WebSocket Connections Require Authentication
**Statement:** WebSocket upgrade requests must include valid auth token.

**Enforcement Points:**
1. **Token Extraction:** Query parameter `token` validated via JWT decode
2. **Tenant Context:** Extracted from JWT and applied to all events

**Code Paths:**
- `layer4-agents/src/api/websocket/routes.py` - WebSocket route handling
- `layer4-agents/src/api/websocket/manager.py` - Connection management

**Gap:** No negative tests found for WebSocket auth bypass

---

## Audit Logging

### Rule: All Tenant Resolution Events Logged
**Statement:** Every authentication attempt emits audit event with outcome.

**Code Paths:**
- `shared/identity/middleware.py:482-531` - Audit emission logic

**Tests:**
- `tests/security/test_tenant_audit.py` - Tenant audit verification

---

## Idempotency

### Rule: Duplicate Events Don't Duplicate Side Effects
**Statement:** Webhooks, jobs, and events processed exactly once.

**Code Paths:**
- `layer4-agents/tests/test_usage_idempotency.py` - Idempotency tests exist

---

## Cross-Layer Boundaries

### Layer1 → Layer2
- API contract validation via OpenAPI specs

### Layer2 → Layer3
- Tenant context propagated in all calls

### Layer3 → Layer4
- Knowledge graph queries tenant-scoped

### Layer4 → Layer5
- Ground truth model access controlled

**Tests:**
- `tests/security/test_cross_layer_tenant.py` - 16 cross-layer tests
- `tests/integration/test_cross_layer_tenant_isolation.py` - Integration tests

---

## Violations & Risks

| Invariant | Risk if Violated | Current Test Coverage | Confidence |
|-----------|-----------------|----------------------|------------|
| Tenant Isolation | Data breach | Strong (27 security tests) | High |
| Authentication | Unauthorized access | Strong (20 adversarial tests) | High |
| Authorization | Privilege escalation | Moderate (18 RBAC tests) | Medium |
| Input Validation | Injection attacks | Moderate (17 tests) | Medium |
| Secrets Protection | Credential exposure | Moderate (11 tests) | Medium |
| Rate Limiting | DoS / resource exhaustion | Low (rate tests exist) | Low |
| WebSocket Auth | Session hijacking | **None** | **Critical Gap** |
| Tenant Lifecycle | Suspended tenant access | Low | Low |
| Audit Logging | Undetected breaches | Moderate | Medium |

---

## Test Enforcement Summary

| Invariant | Positive Tests | Negative Tests | Adversarial Tests |
|-----------|---------------|----------------|-------------------|
| Tenant Isolation | ✅ | ✅ | ✅ |
| Authentication | ✅ | ✅ | ✅ |
| Authorization | ✅ | ⚠️ | ⚠️ |
| Input Validation | ✅ | ✅ | ⚠️ |
| Secrets Protection | ✅ | ✅ | ⚠️ |
| Rate Limiting | ⚠️ | ⚠️ | ❌ |
| WebSocket Auth | ❌ | ❌ | ❌ |
| Tenant Lifecycle | ⚠️ | ❌ | ❌ |

**Legend:** ✅ Strong coverage | ⚠️ Moderate | ❌ Gap identified
