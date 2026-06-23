# Test Gap Matrix - Production Assurance

## Severity Legend
- **P0**: Data/security boundary untested or bypassable - BLOCKS RELEASE
- **P1**: Core production workflow lacks failure/negative coverage
- **P2**: Brittle, incomplete, or overly mocked coverage
- **P3**: Cleanup or maintainability improvement

## Production Invariants and Test Coverage

| Boundary | Production Invariant | Existing Coverage | Missing Positive | Missing Negative | Severity | File Target |
|----------|---------------------|-------------------|------------------|------------------|----------|-------------|
| **Authentication** | | | | | | |
| Auth - Missing | Unauthenticated requests to protected routes return 401 | `test_shared_security_middleware.py` | ✅ | ❌ Adversarial (malformed authz header) | P1 | `test_auth_negative.py` |
| Auth - Expired | Expired JWTs are rejected with 401 | `test_jwt_security.py` (quarantined) | ✅ (can't run) | ❌ Same | **P0** | Rewrite quarantined |
| Auth - Invalid | Invalid signatures return None (falls through) | `test_jwt_security.py` (quarantined) | ✅ (can't run) | ❌ Same | **P0** | Rewrite quarantined |
| **Tenant Isolation** | | | | | | |
| Tenant - Spoof Header | X-Tenant-ID header cannot override JWT claim | `test_tenant_isolation.py` | ✅ | ❌ Specific adversarial (UUID swap) | P1 | Add to `test_tenant_isolation.py` |
| Tenant - Cross-Query | DB queries filter by tenant_id (RLS) | `test_rls_enforcement.py` | ✅ | ❌ Direct SQL injection | P1 | `test_rls_enforcement.py` |
| Tenant - Graph Query | Neo4j queries inject tenant_id | `test_neo4j_tenant_query_enforcement.py` | ✅ | ❌ Graph traversal across tenants | P1 | `test_neo4j_tenant_query_enforcement.py` |
| **Authorization** | | | | | | |
| RBAC - Role Check | require_role() enforces role membership | `test_rbac.py` | ✅ | ❌ Role confusion attacks | P1 | `test_rbac_negative.py` |
| RBAC - Permission | require_permission() works | `test_rbac.py` | ✅ | ❌ Permission bypass attempts | P1 | `test_rbac_negative.py` |
| Privileged - Reason | Super admin access requires X-Privileged-Reason | `test_privileged_audit.py` | ✅ | ✅ | ✅ | None |
| Privileged - Audit | Privileged access emits audit event | `test_privileged_audit.py` | ✅ | ❌ Audit failure handling | P2 | Add to existing |
| **Input Validation** | | | | | | |
| Validation - Schema | Pydantic schemas reject invalid input | `test_owasp_top10.py` | ✅ | ❌ Nested injection attempts | P1 | `test_input_validation.py` |
| Validation - SQL | No SQL injection in queries | `test_injection.py` | ✅ | ❌ Advanced SQLi vectors | P1 | Add to `test_injection.py` |
| **Secrets Protection** | | | | | | |
| Secrets - Logs | API keys not in logs | `test_supply_chain.py` | ✅ | ❌ Log injection | P2 | Add negative case |
| Secrets - Errors | No secrets in error messages | `test_owasp_top10.py` | ✅ | ❌ Verbose error enumeration | P1 | Add to existing |
| **Quarantined (P0)** | | | | | | |
| JWT Security | Full JWT test suite | `test_jwt_security.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |
| OIDC PKCE | OIDC flow security | `test_oidc_pkce.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |
| API Key Auth | API key lifecycle | `test_api_key_security.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |
| Middleware | Context building | `test_middleware_security.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |
| RBAC Detailed | Permission dependencies | `test_rbac_permissions.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |
| Auth Integration | E2E auth flows | `test_auth_integration.py` | ✅ (can't run) | ✅ (can't run) | **P0** | Fix imports or delete |

## P0 Test Coverage Gaps (Blocks Release)

### 1. Quarantined Test Files Cannot Collect

| File | Tests | Import Error | Impact |
|------|-------|--------------|--------|
| `test_jwt_security.py` | 40+ | `_DEFAULT_JWT_SECRET` doesn't exist | No JWT validation coverage |
| `test_oidc_pkce.py` | 30+ | Relative import breaks | No OIDC flow security coverage |
| `test_api_key_security.py` | 35+ | `value_fabric` package doesn't exist | No API key auth coverage |
| `test_middleware_security.py` | 30+ | `_build_context_from_role` missing | No middleware security coverage |
| `test_rbac_permissions.py` | 35+ | `get_current_context` missing | No RBAC dependency coverage |
| `test_auth_integration.py` | 20+ | `value_fabric` package doesn't exist | No integration auth coverage |

**Total:** ~170 tests giving false confidence

**Evidence:** `tests/security/_quarantine/README.md`

**Required Action:**
1. Either fix the imports (rewrite tests against actual API)
2. Or delete the tests (if capability covered elsewhere)
3. Add CI gate to prevent future quarantine accumulation

## P1 Test Coverage Gaps

### 1. Missing Adversarial Auth Tests

Current tests verify valid auth works, but missing:
- Malformed Authorization header ("Bearer " with no token)
- Wrong auth scheme ("Basic xxx" instead of Bearer)
- Multiple auth headers
- Token in query param (bypass attempt)

### 2. Missing Tenant Isolation Negative Cases

Current tests verify JWT claim takes precedence, but missing:
- Tenant ID UUID swapping attempts
- Tenant ID case sensitivity attacks
- Null/empty tenant handling
- Concurrent tenant context pollution

### 3. Missing Input Validation Edge Cases

Current tests verify schema validation, but missing:
- Unicode normalization attacks
- Nested object injection
- Array boundary attacks
- Type confusion (string vs number)

### 4. Missing RBAC Negative Tests

Current tests verify RBAC works, but missing:
- Role confusion (admin in tenant A on tenant B)
- Permission enumeration attacks
- Privilege escalation via parameter pollution

## Production Invariants Extracted

From `shared/identity/dependencies.py`:

```python
# Invariant: Missing auth fails with 401
require_authenticated() -> HTTPException 401 if no tenant_id/user_id

# Invariant: Unknown auth source fails with 401  
require_authenticated() -> HTTPException 401 if auth_source == 'unknown'

# Invariant: Missing tenant context fails with 400
require_tenant_context() -> HTTPException 400 if no tenant_id

# Invariant: Non-admin access to admin endpoints fails with 403
require_tenant_admin() -> HTTPException 403 if not is_tenant_admin()

# Invariant: Super admin only for privileged endpoints fails with 403
require_super_admin() -> HTTPException 403 if not is_super_admin()

# Invariant: Privileged access requires audit reason fails with 400
require_privileged_access() -> HTTPException 400 if no X-Privileged-Reason header

# Invariant: Missing permission fails with 403
require_permission(perm) -> HTTPException 403 if not has_permission(perm)

# Invariant: Startup validation fails if JWT misconfigured in production
validate_jwt_config() -> ValueError if production + weak/missing config
```

## Recommended Test Priority

### Immediate (This Session)
1. ✅ Delete or fix quarantined tests (P0)
2. ✅ Add adversarial auth tests (P1)
3. ✅ Add negative RBAC tests (P1)

### Next Session
4. Add tenant UUID swap tests (P1)
5. Add input validation edge cases (P1)
6. Add CI collection verification gate

### Backlog
7. Property-based tests for validation (P2)
8. Chaos tests for auth context (P2)
