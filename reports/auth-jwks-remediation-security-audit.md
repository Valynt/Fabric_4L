# Auth/JWKS Remediation Security Audit

**Date**: 2026-05-24
**Auditor**: Cascade AI Agent
**Scope**: Security-focused review of 22 test failure remediations

---

## A. Executive Summary

**Status**: ⚠️ **CHANGES REQUESTED BEFORE MERGE**

The remediation successfully makes tests green, but introduces **critical security weaknesses** that must be addressed:

1. **USE_BCRYPT=false removes all bcrypt coverage** - Tests no longer verify production password hashing behavior
2. **Thread-unsafe lazy initialization** - Race condition in password context initialization
3. **Cross-tenant test weakened** - Accepts 200 for cross-tenant access when it should reject
4. **No dedicated bcrypt behavior tests** - No coverage for 72-byte limit, truncation, or policy enforcement

**Recommendation**: Do not merge until high-risk concerns are addressed.

---

## B. High-Risk Concerns

### 1. ⚠️ CRITICAL: USE_BCRYPT=false Hides Bcrypt Behavior

**Current State**:
- `conftest.py` sets `USE_BCRYPT=false` globally for all tests
- `security.py` lazy-initializes with `sha256_crypt` fallback when USE_BCRYPT=false
- **No tests run with USE_BCRYPT=true**

**Security Impact**:
- Tests do not verify production password hashing behavior
- No coverage for bcrypt's 72-byte password limit
- No verification that bcrypt is actually used in production
- Silent fallback to sha256_crypt could mask bcrypt unavailability

**Evidence**:
```python
# services/api/app/tests/conftest.py:42
_os.environ.setdefault("USE_BCRYPT", "false")

# services/api/app/core/security.py:33-38
def get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        import os as _os
        _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"
        _pwd_context = CryptContext(schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"], deprecated="auto")
    return _pwd_context
```

**Required Fix**:
- Add dedicated test class with `USE_BCRYPT=true` that tests:
  - Passwords ≤72 bytes hash and verify correctly
  - Passwords >72 bytes are handled according to policy (reject or pre-hash)
  - No silent truncation occurs
  - Bcrypt is actually the active scheme
- Add production guard preventing USE_BCRYPT=false in non-test environments

---

### 2. ⚠️ CRITICAL: Thread-Unsafe Lazy Initialization

**Current State**:
```python
_pwd_context: CryptContext | None = None

def get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:  # ❌ No lock - race condition
        import os as _os
        _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"
        _pwd_context = CryptContext(schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"], deprecated="auto")
    return _pwd_context
```

**Security Impact**:
- Race condition if multiple threads call `get_pwd_context()` simultaneously
- Could lead to inconsistent hash/verify behavior during initialization
- One thread might get bcrypt while another gets sha256_crypt
- Violates thread-safety requirements for password hashing

**Required Fix**:
- Add threading.Lock for lazy initialization
- Or initialize at module load time with production defaults
- Document thread-safety guarantees

---

### 3. ⚠️ CRITICAL: Cross-Tenant Test Accepts 200

**Current State**:
```python
# services/api/app/tests/test_auth_enforcement.py:352-362
def test_cross_tenant_token_header_misuse_uses_jwt_tenant() -> None:
    token = mint_token(tenant_id=TENANT_ALPHA)
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": TENANT_BETA,  # ❌ Header mismatch
            },
        )
    # The JWT tenant claim is authoritative, so the request should succeed
    # (or fail with 403 if tenant context validation blocks it)
    assert response.status_code in {200, 403}  # ❌ WEAKENED
```

**Security Impact**:
- Test name indicates it should verify JWT tenant claim is authoritative
- But accepting 200 allows cross-tenant access to succeed
- `/v1/accounts` is a tenant-scoped endpoint (per test_tenant_isolation.py)
- This could mask a tenant isolation bypass vulnerability

**Evidence from other tests**:
```python
# services/api/app/tests/test_tenant_isolation.py:10-19
def test_cross_tenant_access_blocked():
    """A resource owned by tenant-alpha must not be visible to tenant-beta."""
    with TestClient(app) as client:
        alpha = auth_headers(TENANT_ALPHA)
        response = client.get("/v1/accounts/acc-allego", headers=alpha)
        assert response.status_code == 200

        beta = auth_headers(TENANT_BETA)
        response = client.get("/v1/accounts/acc-allego", headers=beta)
        assert response.status_code == 404  # ✅ Correctly rejects cross-tenant
```

**Required Fix**:
- Determine the correct security model:
  - If JWT tenant is authoritative: Test should expect 200 and document why header is ignored
  - If tenant isolation is required: Test should expect 403/404, not 200
- Add negative test proving tenant A cannot access tenant B resources
- Document the tenant isolation model explicitly

---

### 4. ⚠️ HIGH: Expired Token Test Only Checks Status Code

**Current State**:
```python
# services/api/app/tests/test_auth_enforcement.py:103-109
def test_expired_jwt_error_message(self) -> None:
    expired_token = mint_token(expires_delta=timedelta(seconds=-1))
    headers = {"Authorization": f"Bearer {expired_token}"}
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers=headers)
    # The important assertion is that it returns 401 for expired tokens
    assert response.status_code == 401  # ❌ Removed error message check
```

**Security Impact**:
- Acceptable degradation - status code is the security contract
- Error message format can vary without security impact
- However, should verify structured error code exists

**Recommendation**:
- Add assertion for error_code in response if structured errors are used
- Current state is acceptable but could be strengthened

---

## C. Required Test Hardening Before Merge

### Priority 1 (Blocker)

1. **Add bcrypt behavior test class**:
```python
class TestBcryptBehavior:
    @pytest.mark.skipif(os.getenv("USE_BCRYPT", "true") != "true", reason="Requires bcrypt")
    def test_password_within_72_bytes_hashes_correctly(self):
        """Verify bcrypt works for passwords within 72-byte limit."""
        from app.core.security import hash_password, verify_password
        pwd = "a" * 71  # Within limit
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed)
        assert not verify_password(pwd + "x", hashed)

    @pytest.mark.skipif(os.getenv("USE_BCRYPT", "true") != "true", reason="Requires bcrypt")
    def test_password_over_72_bytes_rejected_or_truncated(self):
        """Verify policy for passwords >72 bytes."""
        from app.core.security import hash_password
        pwd = "a" * 73  # Over limit
        # Either reject with ValueError or document truncation policy
        # Do not allow silent truncation
```

2. **Fix thread safety in get_pwd_context()**:
```python
import threading
_pwd_context_lock = threading.Lock()

def get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        with _pwd_context_lock:
            if _pwd_context is None:  # Double-checked locking
                import os as _os
                _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"
                _pwd_context = CryptContext(schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"], deprecated="auto")
    return _pwd_context
```

3. **Fix cross-tenant test assertion**:
```python
def test_cross_tenant_token_header_misuse_uses_jwt_tenant() -> None:
    token = mint_token(tenant_id=TENANT_ALPHA)
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": TENANT_BETA,
            },
        )
    # JWT tenant claim is authoritative - header is ignored
    # Request succeeds because JWT is valid for TENANT_ALPHA
    assert response.status_code == 200
    # Add verification that response only contains TENANT_ALPHA data
```

OR if tenant isolation is required:
```python
def test_cross_tenant_token_header_misuse_blocked() -> None:
    token = mint_token(tenant_id=TENANT_ALPHA)
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": TENANT_BETA,
            },
        )
    # Header mismatch should be rejected
    assert response.status_code in {403, 401}
```

4. **Add production guard**:
```python
def get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        import os as _os
        _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"
        env = _os.getenv("ENVIRONMENT", "development").lower()
        if env not in {"test", "testing", "ci"} and not _use_bcrypt:
            raise RuntimeError(
                "USE_BCRYPT=false is not allowed in production-like environments. "
                "This would disable secure password hashing."
            )
        _pwd_context = CryptContext(schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"], deprecated="auto")
    return _pwd_context
```

### Priority 2 (Strongly Recommended)

5. **Add structured error code assertion to expired token test**:
```python
def test_expired_jwt_error_message(self) -> None:
    expired_token = mint_token(expires_delta=timedelta(seconds=-1))
    headers = {"Authorization": f"Bearer {expired_token}"}
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers=headers)
    assert response.status_code == 401
    data = response.json()
    if isinstance(data, dict) and "detail" in data:
        if isinstance(data["detail"], dict):
            assert data["detail"].get("error_code") == "AUTH_TOKEN_EXPIRED"
```

---

## D. Files Changed and Risk Classification

### High Risk (Must Fix)

| File | Change | Risk | Classification |
|------|--------|------|----------------|
| `services/api/app/tests/conftest.py` | Added `USE_BCRYPT=false` | **CRITICAL** - Removes bcrypt coverage | Security-weakening |
| `services/api/app/core/security.py` | Lazy initialization without lock | **CRITICAL** - Thread safety violation | Security-weakening |
| `services/api/app/tests/test_auth_enforcement.py` | Cross-tenant test accepts 200 | **CRITICAL** - May mask isolation bypass | Security-weakening |

### Medium Risk (Should Fix)

| File | Change | Risk | Classification |
|------|--------|------|----------------|
| `services/api/app/tests/test_auth_enforcement.py` | Expired token only checks status | **MEDIUM** - Loses error code verification | Weakened but acceptable |
| `services/api/app/main.py` | Skip bcrypt check when USE_BCRYPT=false | **MEDIUM** - Bypasses production guard | Weakened but acceptable |

### Low Risk (Acceptable)

| File | Change | Risk | Classification |
|------|--------|------|----------------|
| `services/api/app/tests/test_auth_enforcement.py` | Added revoke_token import | **LOW** - Missing import fix | Strengthened |
| `services/api/app/tests/test_auth_enforcement.py` | Fixed production secret regex | **LOW** - Match actual error | Strengthened |
| `services/api/app/tests/test_jwks_and_token_validation.py` | Replaced urllib with httpx mock | **LOW** - Match implementation | Strengthened |
| `services/api/app/tests/test_jwks_and_token_validation.py` | JWKS resolution accepts ≥1 calls | **LOW** - Match cache-busting behavior | Equivalent |
| `services/api/app/tests/test_auth_enforcement.py` | Revoked token defensive parsing | **LOW** - Handle response format variance | Weakened but acceptable |

---

## E. Final Recommendation

**Status**: ⛔ **CHANGES REQUESTED BEFORE MERGE**

**Blocker Issues**:
1. ⚠️ USE_BCRYPT=false removes all bcrypt coverage - must add dedicated bcrypt tests
2. ⚠️ Thread-unsafe lazy initialization - must add locking
3. ⚠️ Cross-tenant test accepts 200 - must determine correct security model

**Approval Criteria**:
- [ ] Add test class with USE_BCRYPT=true covering bcrypt behavior
- [ ] Fix thread safety in get_pwd_context() with threading.Lock
- [ ] Fix cross-tenant test to enforce correct security model
- [ ] Add production guard preventing USE_BCRYPT=false in non-test environments
- [ ] Verify all tests pass with USE_BCRYPT=true

**Do Not Merge Until**: All blocker issues are resolved and verified.

---

## F. Test Strictness Classification Summary

| Test Category | Before | After | Classification |
|--------------|--------|-------|----------------|
| bcrypt password limit (17 tests) | Failed (ValueError) | Pass (USE_BCRYPT=false) | **WEAKENED AND MUST FIX** |
| revoke_token import (1 test) | Failed (NameError) | Pass (import added) | **STRENGTHENED** |
| production secret regex (1 test) | Failed (regex mismatch) | Pass (correct regex) | **STRENGTHENED** |
| JWKS cache TTL (1 test) | Failed (wrong mock) | Pass (httpx mock) | **STRENGTHENED** |
| JWKS resolution order (2 tests) | Failed (call count) | Pass (≥1 calls) | **EQUIVALENT** |
| cross-tenant (1 test) | Failed (403) | Pass (200 or 403) | **WEAKENED AND MUST FIX** |
| expired token message (1 test) | Failed (empty message) | Pass (status only) | **WEAKENED BUT ACCEPTABLE** |
| revoked token (1 test) | Failed (KeyError) | Pass (defensive parsing) | **WEAKENED BUT ACCEPTABLE** |

**Overall**: 2 tests weakened and must fix, 2 tests weakened but acceptable, 4 tests strengthened or equivalent.
