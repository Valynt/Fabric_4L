# Test Gap Matrix — Fabric 4L Production Assurance

**Generated:** 2026-04-28
**Auditor:** Autonomous Test Assurance Agent

---

## Severity Definitions

- **P0**: Data/security boundary untested or bypassable - BLOCKS RELEASE
- **P1**: Core production workflow lacks failure/negative coverage
- **P2**: Brittle, incomplete, or overly mocked coverage
- **P3**: Cleanup or maintainability improvement

---

## Gap Matrix

| Boundary | Risk | Existing Coverage | Missing Positive | Missing Negative | Layer | Severity | File Target | Status |
|----------|------|-------------------|------------------|------------------|-------|----------|-------------|--------|
| **Tenant Isolation** |
| Cross-tenant entity read | Data leak between tenants | `test_tenant_isolation.py` has basic test | Tenant A reads own data | Tenant A cannot read Tenant B data | Unit + Integration | P1 | test_tenant_isolation.py | ✅ EXISTS |
| Tenant header spoofing | Header injection bypass | `test_cross_tenant_api.py` | Header matches JWT claim | Spoofed header rejected | Unit + Integration | P0 | test_cross_tenant_api.py | ✅ EXISTS |
| RLS policy enforcement | DB-level bypass | `test_rls_enforcement.py` | Tenant-scoped query works | Cross-tenant query returns no rows | DB Integration | P0 | test_rls_enforcement.py | ✅ EXISTS |
| Neo4j tenant isolation | Graph query bypass | `test_neo4j_tenant_query_enforcement.py` | Tenant-scoped graph query | Cross-tenant graph access blocked | Integration | P0 | test_neo4j_tenant_query_enforcement.py | ✅ EXISTS |
| **Authentication** |
| Missing auth header | Unprotected endpoint access | `test_adversarial_auth.py` | Valid auth succeeds | Missing auth returns 401 | Unit | P0 | test_adversarial_auth.py | ✅ EXISTS |
| Invalid JWT signature | Token forgery | `test_adversarial_auth.py` | Valid JWT accepted | Invalid signature rejected | Unit | P0 | test_adversarial_auth.py | ✅ EXISTS |
| Expired JWT | Session hijacking with old token | `test_oidc.py` | Valid token works | Expired token returns 401 | Unit | P0 | test_oidc.py | ✅ EXISTS |
| Malformed JWT | Parsing vulnerabilities | `test_adversarial_auth.py` | Well-formed token works | Malformed token rejected | Unit | P0 | test_adversarial_auth.py | ✅ EXISTS |
| **Authorization** |
| Role-based access | Privilege escalation | `test_rbac.py` (8 negative tests) | Admin action with admin role | Admin action with user role fails | Unit | P0 | test_rbac.py | ✅ EXISTS |
| Resource ownership | Access other user's data | `test_rbac.py` | Owner accesses own resource | Non-owner access rejected | Unit | P0 | test_rbac.py | ✅ EXISTS |
| Super admin bypass | Unrestricted access tracking | `test_privileged_audit.py` | Super admin action succeeds | Privileged action is audited | Unit | P1 | test_privileged_audit.py | ✅ EXISTS |
| **Input Validation** |
| SQL injection | Data exfiltration | `test_injection.py` | Valid query succeeds | Malicious query rejected/sanitized | Unit | P0 | test_injection.py | ✅ EXISTS |
| NoSQL injection | Graph query manipulation | `test_neo4j_tenant_query_enforcement.py` | Valid graph query works | Malicious graph query blocked | Integration | P0 | test_neo4j_tenant_query_enforcement.py | ✅ EXISTS |
| Oversized payload | DoS via large input | None found | Normal payload accepted | Oversized payload rejected | Unit | **P1** | **TO ADD** | 🔴 GAP |
| Unknown fields | Schema pollution | None found | Known fields accepted | Unknown fields rejected/ignored | Unit | **P2** | **TO ADD** | 🔴 GAP |
| **Secrets Protection** |
| Secrets in logs | Credential exposure | `test_owasp_top10.py` (5 matches) | Normal log entry | Secrets redacted in logs | Unit | **P1** | **TO ADD** | 🔴 GAP |
| Secrets in errors | Stack trace exposure | `test_security_misconfiguration.py` | Generic error message | Secrets not in error detail | Unit | **P1** | **TO ADD** | 🔴 GAP |
| API key in audit | Audit log exposure | None found | Audit entry created | API key redacted in audit | Unit | **P2** | **TO ADD** | 🔴 GAP |
| **Idempotency** |
| Webhook deduplication | Duplicate side effects | `test_webhook_security.py` (9 matches) | First delivery succeeds | Duplicate delivery ignored | Integration | P1 | test_webhook_security.py | ✅ EXISTS |
| Job retry safety | Multiple job execution | `test_usage_idempotency.py` (7 matches) | Job succeeds on first run | Retry doesn't duplicate effects | Integration | P1 | test_usage_idempotency.py | ✅ EXISTS |
| Idempotency key missing | Missing key handling | None found | Request with key processed | Missing key handled safely | Unit | **P2** | **TO ADD** | 🔴 GAP |
| **Operational** |
| Rate limiting | Resource exhaustion | `test_tenant_rate_limiting.py` | Request within limit succeeds | Excess requests throttled (429) | Integration | P0 | test_tenant_rate_limiting.py | ✅ EXISTS |
| Tenant suspension | Suspended tenant access | None found | Active tenant access works | Suspended tenant denied (403) | Integration | **P0** | **TO ADD** | 🔴 GAP |
| Tenant pending | Pending tenant access | None found | Activated tenant works | Pending tenant denied with message | Integration | **P1** | **TO ADD** | 🔴 GAP |
| **Agent/LLM Safety** |
| Tool output validation | Malformed tool output | `test_tool_manifests.py` | Valid tool output accepted | Invalid output schema rejected | Unit | P1 | test_tool_manifests.py | ✅ EXISTS |
| Agent provenance | Action traceability | `test_provenance.py` | Action with provenance | Missing provenance rejected | Unit | P1 | `services/layer4-agents/tests/test_provenance.py` | ✅ EXISTS |
| **Frontend** |
| Protected route guard | Unauthenticated page access | `AgentWorkflows.test.tsx` | Authenticated sees page | Unauthenticated redirected | E2E | **P1** | **TO ADD** | 🔴 GAP |
| Tenant switch clear | Stale tenant data | None found | Switch shows new data | Old tenant data cleared | E2E | **P2** | **TO ADD** | 🔴 GAP |
| **Cross-Layer** |
| Layer-to-layer auth | Service bypass | `test_cross_layer_tenant.py` | Valid inter-service call | Invalid service auth rejected | Integration | P0 | test_cross_layer_tenant.py | ✅ EXISTS |
| Context propagation | Tenant context loss | `test_tenant_context_contract.py` | Context preserved | Missing context detected | Unit | P0 | test_tenant_context_contract.py | ✅ EXISTS |

---

## Summary of Gaps

| Severity | Count | Boundaries |
|----------|-------|------------|
| **P0** | 2 | Tenant suspension, Tenant pending |
| **P1** | 5 | Oversized payload, Secrets in logs, Secrets in errors, Protected route guard |
| **P2** | 4 | Unknown fields, API key in audit, Idempotency key missing, Tenant switch clear |
| **P3** | 0 | |

**Total Gaps: 11**

---

## Priority Actions

### Immediate (P0)

1. **Tenant Suspension Enforcement**
   - File: `tests/security/test_tenant_lifecycle.py`
   - Test: Verify `GovernanceMiddleware` blocks suspended tenants with 403
   - Code: `@/shared/identity/middleware.py:314-319`

2. **Tenant Pending Enforcement**
   - File: `tests/security/test_tenant_lifecycle.py`
   - Test: Verify pending tenants get proper onboarding message
   - Code: `@/shared/identity/middleware.py:321-326`

### High Priority (P1)

3. **Secrets Redaction in Logs**
   - File: `tests/security/test_secrets_protection.py`
   - Test: Verify API keys, JWTs, passwords redacted in log output
   - Code: Audit logging infrastructure in `@/shared/audit/`

4. **Secrets in Error Responses**
   - File: `tests/security/test_secrets_protection.py`
   - Test: Verify stack traces and error details don't expose secrets
   - Code: Error handlers across all layers

5. **Oversized Payload Rejection**
   - File: `tests/security/test_input_validation.py`
   - Test: Verify large payloads rejected with 413
   - Code: FastAPI/Starlette request size limits

6. **Frontend Protected Route Guard**
   - File: `frontend/client/src/routes/ProtectedRoute.test.tsx`
   - Test: Verify unauthenticated users redirected to login
   - Code: React Router protected routes

### Medium Priority (P2)

7. **Unknown Field Handling**
8. **API Key Redaction in Audit**
9. **Missing Idempotency Key**
10. **Tenant Switch State Clearance**
