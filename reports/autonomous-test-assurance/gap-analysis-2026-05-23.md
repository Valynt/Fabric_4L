# Gap Analysis

Generated: 2026-05-23

## Identified Gaps

### Gap 1: JWT Expiration Edge Cases (P1)
- **Invariant**: Expired or near-expiry JWTs must be rejected
- **Current State**: `test_auth_boundaries.py` tests invalid tokens but not clock skew, near-expiry, or future-issued tokens
- **Impact**: Clock skew or timing edge cases may allow expired token acceptance
- **Action**: Add `TestJWTExpirationEdgeCases` to `tests/security/test_auth_boundaries.py`

### Gap 2: Permission Dependency Fail-Closed (P1)
- **Invariant**: `require_permission` must fail closed when auth context is missing
- **Current State**: No direct test for `require_permission` dependency with missing `api_key`
- **Impact**: Permission bypass if auth dependency returns None silently
- **Action**: Add test for `require_permission` raising 403 when `get_current_api_key` returns None

### Gap 3: Signup Plan Field Rejection (P2)
- **Invariant**: Unauthenticated callers must not self-assign billing tier via signup
- **Current State**: `SignupRequest` omits `plan` but no test verifies extra fields are rejected/ignored
- **Impact**: Attackers could self-elevate to paid tier during signup
- **Action**: Add test for signup with injected `plan` field

## Coverage Summary
| Category | Status |
|----------|--------|
| Tenant Isolation | Strong (91 security files) |
| Auth Boundaries | Good, missing edge cases |
| RLS Enforcement | Strong (migration files + tests) |
| Input Validation | Good (Pydantic + regex) |
| RBAC | Good, missing fail-closed direct test |
