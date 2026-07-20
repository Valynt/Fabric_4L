# OIDC Audit & Hardening Spec

## Problem Statement

The OIDC/Keycloak authentication stack is largely implemented but has a set of
real gaps that need to be closed before the flow can be considered production-hardened:

1. `OIDCClient.discover()` retries on **all** exceptions (bare `except Exception:`),
   not just transient 5xx/network errors — a 4xx from the IdP causes a redundant
   retry that masks the real error. Non-transient failures (4xx, malformed JSON,
   missing required discovery fields, TLS errors, configuration errors) must fail
   fast without a retry.
2. `services/api/app/core/security.py` uses `python-jose` while
   `packages/shared/identity/jwt.py` uses `PyJWT` — two JWT libraries with no
   cross-contract test, creating silent drift risk.
3. `tests/security/test_adversarial_auth.py` uses a `client` fixture that is not
   wired to a real FastAPI app with `GovernanceMiddleware` — the tests exist but
   do not exercise the actual middleware.
4. `KEYCLOAK_URL` and `KEYCLOAK_REALM` are present in the root `.env.example` but
   commented without example values; service-level `.env.example` files that read
   OIDC vars have no OIDC documentation at all.
5. `docs/how-to-guides/configure-sso.md` **already exists** and is comprehensive —
   no creation needed, but it must be verified to be accurate against the current
   implementation.
6. No test covers the `discover()` retry path or the dual-library token
   acceptance contract.

---

## Scope

### In scope
- Fix `OIDCClient.discover()` retry logic (narrow bare `except` to transient errors).
- Add a cross-contract test: same token accepted by both `decode_jwt` (PyJWT) and
  `decode_token` (python-jose / `services/api`).
- Fix `test_adversarial_auth.py` fixture wiring so tests exercise real middleware.
- Uncomment and add safe example values for `KEYCLOAK_URL` / `KEYCLOAK_REALM` in
  root `.env.example`; add a minimal OIDC comment block to
  `services/layer4-agents` `.env.example` (create if absent).
- Verify `docs/how-to-guides/configure-sso.md` is accurate; apply targeted
  corrections only if discrepancies are found.
- Add unit tests for the `discover()` retry fix.
- Add adversarial tests for: invalid issuer, invalid audience, expired token,
  malformed token, missing `tenant_id`, cross-tenant attempt, service-auth bypass
  attempt — all wired to real `GovernanceMiddleware`.

### Out of scope
- Rebuilding or replacing the existing OIDC flow.
- Migrating `services/api` from `python-jose` to `PyJWT` (document drift, add
  contract test — no migration).
- Frontend changes (audit found no OIDC integration bugs in `AuthContext`,
  `authClient`, or `sessionService`; findings documented in final report only).
- Adding OIDC vars to every service `.env.example` (only layer4-agents is
  directly involved in OIDC flows).
- Marking production readiness complete from unit tests alone.

---

## Acceptance Criteria

- [ ] `OIDCClient.discover()` defines two custom exception types:
      `TransientOIDCDiscoveryError` (retryable) and `OIDCDiscoveryError`
      (non-retryable). The retry wrapper retries only `TransientOIDCDiscoveryError`.
- [ ] Transient: HTTP 5xx, HTTP 429, `httpx.TimeoutException`, `httpx.RequestError`
      (connection refused, DNS failure). Non-transient: HTTP 4xx (except 429),
      malformed JSON, missing required discovery fields, TLS/certificate errors,
      any other `Exception` not explicitly classified.
- [ ] 4xx responses (400, 401, 403, 404) propagate immediately as
      `OIDCDiscoveryError` without a retry attempt.
- [ ] Malformed JSON in the discovery response raises `OIDCDiscoveryError`
      immediately (no retry).
- [ ] Missing required OIDC discovery fields (`authorization_endpoint`,
      `token_endpoint`, `jwks_uri`) raise `OIDCDiscoveryError` immediately.
- [ ] Root cause is preserved in all raised exceptions (`raise ... from exc`).
- [ ] A new test `tests/contract/test_jwt_library_parity.py` passes: a token
      encoded by `encode_jwt` (PyJWT) is accepted by `decode_token` (python-jose)
      and vice versa.
- [ ] `tests/security/test_adversarial_auth.py` fixtures are wired to a real
      `GovernanceMiddleware` FastAPI app; all existing tests in that file pass.
- [ ] Root `.env.example` has `KEYCLOAK_URL` and `KEYCLOAK_REALM` uncommented with
      safe local-dev example values (`http://localhost:8080` and `fabric`).
- [ ] `services/layer4-agents/.env.example` exists and documents the OIDC env vars
      consumed by that service.
- [ ] `docs/how-to-guides/configure-sso.md` accurately reflects the current
      implementation (no stale instructions).
- [ ] New adversarial tests pass: invalid issuer → 401, invalid audience → 401,
      expired token → 401, malformed token → 401, missing `tenant_id` → 401/403,
      cross-tenant header conflict → 403, service-auth bypass without secret → 401.
- [ ] No production secrets committed.
- [ ] Final report lists: files changed, tests added, validation commands, residual
      risks, and follow-up items.

---

## Implementation Approach

Steps are ordered by dependency; each step is independently testable.

### Step 1 — Fix `OIDCClient.discover()` retry logic

**File:** `packages/shared/src/value_fabric/shared/identity/oidc.py`

#### 1a. Add exception types

Add two exception classes at module level (before `OIDCClient`):

```python
class OIDCDiscoveryError(Exception):
    """Non-retryable OIDC discovery failure (config error, 4xx, bad response)."""

class TransientOIDCDiscoveryError(OIDCDiscoveryError):
    """Retryable OIDC discovery failure (5xx, 429, timeout, connection error)."""
```

#### 1b. Add required-field validation

Add a module-level constant and helper:

```python
_REQUIRED_DISCOVERY_FIELDS = ("authorization_endpoint", "token_endpoint", "jwks_uri")

def _validate_discovery_document(doc: dict, issuer_url: str) -> None:
    """Raise OIDCDiscoveryError if required fields are missing."""
    missing = [f for f in _REQUIRED_DISCOVERY_FIELDS if not doc.get(f)]
    if missing:
        raise OIDCDiscoveryError(
            f"OIDC discovery document from {issuer_url!r} is missing required "
            f"fields: {missing}"
        )
```

#### 1c. Replace `discover()` implementation

Replace the current `discover()` method body with:

```python
async def discover(self, issuer_url: str) -> dict:
    """Fetch OpenID Provider metadata from well-known endpoint.

    Retries once on transient failures (5xx, 429, timeout, connection error).
    Fails immediately on 4xx, malformed JSON, missing required fields, and
    any other non-transient error.
    """
    well_known = issuer_url.rstrip("/") + "/.well-known/openid-configuration"

    async def _attempt() -> dict:
        try:
            response = await self._http_client.get(well_known)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429 or status >= 500:
                raise TransientOIDCDiscoveryError(
                    f"OIDC discovery returned transient HTTP {status} from {issuer_url!r}"
                ) from exc
            raise OIDCDiscoveryError(
                f"OIDC discovery failed with HTTP {status} from {issuer_url!r}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TransientOIDCDiscoveryError(
                f"OIDC discovery timed out for {issuer_url!r}"
            ) from exc
        except httpx.RequestError as exc:
            # Connection refused, DNS failure — operationally transient.
            raise TransientOIDCDiscoveryError(
                f"OIDC discovery connection error for {issuer_url!r}: {exc}"
            ) from exc

        try:
            doc = response.json()
        except Exception as exc:
            raise OIDCDiscoveryError(
                f"OIDC discovery document from {issuer_url!r} contains invalid JSON"
            ) from exc

        _validate_discovery_document(doc, issuer_url)
        return doc

    try:
        return await _attempt()
    except TransientOIDCDiscoveryError:
        logger.warning(
            "OIDC discovery transient failure for %r; retrying once", issuer_url
        )
        return await _attempt()
```

**Key properties of this implementation:**
- `TransientOIDCDiscoveryError` is the only exception that triggers a retry.
- 4xx responses, malformed JSON, and missing fields raise `OIDCDiscoveryError`
  directly — no retry, no swallowed root cause.
- `httpx.RequestError` (connection refused, DNS) is classified as transient
  deliberately, not caught as a generic `Exception`.
- TLS/certificate errors (`httpx.ConnectError` with SSL context) are subclasses
  of `httpx.RequestError` and will be retried once. This is acceptable — a
  single retry on a TLS handshake failure is low risk and operationally useful
  for transient cert-chain issues. If stricter TLS handling is needed later,
  `httpx.ConnectError` can be split out and classified as non-transient.
- Root cause is always preserved via `raise ... from exc`.
- Log message on retry includes the issuer URL for observability.

### Step 2 — Add unit tests for `discover()` retry fix

**File:** `tests/shared/identity/test_oidc_discover_retry.py` (new)

Use `respx` to mock HTTP calls. All tests are `@pytest.mark.asyncio`.

Import `OIDCDiscoveryError` and `TransientOIDCDiscoveryError` from
`value_fabric.shared.identity.oidc` and assert on the correct exception type.

**Retry tests (transient — one retry, second attempt succeeds):**
- `test_discover_retries_on_500` — first call returns 500; second returns 200
  with valid discovery doc; result returned.
- `test_discover_retries_on_502` — first call returns 502; second returns 200.
- `test_discover_retries_on_503` — first call returns 503; second returns 200.
- `test_discover_retries_on_504` — first call returns 504; second returns 200.
- `test_discover_retries_on_429` — first call returns 429; second returns 200.
- `test_discover_retries_on_timeout` — first call raises
  `httpx.TimeoutException`; second returns 200.
- `test_discover_retries_on_connection_error` — first call raises
  `httpx.ConnectError`; second returns 200.

**No-retry tests (non-transient — single attempt, immediate failure):**
- `test_discover_does_not_retry_on_400` — returns 400; raises
  `OIDCDiscoveryError`; exactly one HTTP call made.
- `test_discover_does_not_retry_on_401` — returns 401; raises
  `OIDCDiscoveryError`; one call.
- `test_discover_does_not_retry_on_403` — returns 403; raises
  `OIDCDiscoveryError`; one call.
- `test_discover_does_not_retry_on_404` — returns 404; raises
  `OIDCDiscoveryError`; one call.
- `test_discover_does_not_retry_on_malformed_json` — returns 200 with body
  `"not json"`; raises `OIDCDiscoveryError`; one call.
- `test_discover_does_not_retry_on_missing_required_fields` — returns 200 with
  `{"issuer": "https://example.com"}` (no `authorization_endpoint`,
  `token_endpoint`, `jwks_uri`); raises `OIDCDiscoveryError`; one call.
- `test_discover_does_not_retry_on_partial_missing_fields` — returns 200 with
  only `authorization_endpoint` present; raises `OIDCDiscoveryError` listing the
  two missing fields.

**Exhausted retry tests (transient — both attempts fail):**
- `test_discover_raises_after_two_5xx_attempts` — both calls return 503; raises
  `TransientOIDCDiscoveryError`; exactly two HTTP calls made.
- `test_discover_raises_after_two_connection_errors` — both calls raise
  `httpx.ConnectError`; raises `TransientOIDCDiscoveryError`; two calls.

**Root cause preservation:**
- `test_discover_error_preserves_cause_on_4xx` — `OIDCDiscoveryError.__cause__`
  is an `httpx.HTTPStatusError` with the original status code.
- `test_discover_error_preserves_cause_on_timeout` — `TransientOIDCDiscoveryError.__cause__`
  is an `httpx.TimeoutException`.

**Happy path:**
- `test_discover_success` — returns 200 with a valid discovery document
  containing all required fields; result dict matches the document.

### Step 3 — Add JWT library parity contract test

**File:** `tests/contract/test_jwt_library_parity.py` (new)

Purpose: detect silent drift between `packages/shared` (PyJWT) and
`services/api` (python-jose).

Tests to add:
- `test_pyjwt_token_accepted_by_jose` — encode a token with `encode_jwt`
  (PyJWT); decode it with `services/api`'s `decode_token` (python-jose); assert
  claims match.
- `test_jose_token_accepted_by_pyjwt` — encode a token with
  `create_access_token` (python-jose); decode it with `decode_jwt` (PyJWT);
  assert claims match.
- `test_expired_token_rejected_by_both` — expired token is rejected by both
  libraries with the appropriate error type.
- `test_wrong_secret_rejected_by_both` — token signed with wrong secret is
  rejected by both.

**Note:** This test documents the dual-library situation and will catch future
drift. It does not migrate either library.

### Step 4 — Fix `test_adversarial_auth.py` fixture wiring

**File:** `tests/security/test_adversarial_auth.py`

The `client` fixture is currently undefined in this file (it relies on a
conftest fixture that is not wired to a real app). Fix by adding a module-level
`client` fixture that mirrors the pattern in `test_cross_tenant_jwt.py`:

```python
@pytest.fixture(scope="module")
def app():
    from fastapi import FastAPI
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    _app = FastAPI()
    _app.add_middleware(GovernanceMiddleware, rate_limiter=None)

    @_app.get("/api/v1/entities")
    def entities(request: Request):
        ctx = getattr(request.state, "governance_context", None)
        if ctx is None:
            raise HTTPException(status_code=401, detail="Unauthenticated")
        return {"items": []}

    return _app

@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)
```

Also add a `standard_user_token` fixture that produces a valid HS256 token using
`encode_jwt` with a known test secret (matching the pattern in
`test_cross_tenant_jwt.py`).

After wiring, verify all existing test classes pass:
- `TestMalformedAuthorizationHeader`
- `TestTenantContextAttacks`
- `TestTokenManipulation`
- `TestRBACNegative`

### Step 5 — Add new adversarial tests

**File:** `tests/security/test_adversarial_auth.py` (extend existing)

Add a new class `TestOIDCAdversarialPaths` with tests wired to the same
`GovernanceMiddleware` app:

| Test | Attack vector | Expected result |
|---|---|---|
| `test_invalid_issuer_rejected` | Token with `iss` not matching `JWT_ISSUER` or `OIDC_ISSUER` | 401 |
| `test_invalid_audience_rejected` | Token with wrong `aud` | 401 |
| `test_expired_token_rejected` | Token with `exp` in the past | 401 |
| `test_malformed_token_rejected` | Garbage string, truncated JWT, `alg:none` | 401 |
| `test_missing_tenant_id_rejected` | Valid signature, no `tenant_id` claim | 401/403 |
| `test_cross_tenant_header_conflict_rejected` | Valid JWT for tenant A + `X-Tenant-ID` header for tenant B | 403 |
| `test_service_auth_bypass_without_secret_rejected` | `X-Tenant-ID` only, no `X-Service-Auth`, no `SERVICE_AUTH_SECRET` | 401 |
| `test_hs256_rejected_for_oidc_issuer` | HS256 token when `OIDC_ISSUER` is configured | 401 |

### Step 6 — Update `.env.example` files

**File:** `/.env.example`

Uncomment `KEYCLOAK_URL` and `KEYCLOAK_REALM` and add safe local-dev example
values:

```bash
# Keycloak-specific: used to auto-construct the JWKS URL when OIDC_JWKS_URL is
# not set. The constructed URL is: {KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs
# Local dev default: KEYCLOAK_URL=http://localhost:8080, KEYCLOAK_REALM=fabric
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=fabric
```

**File:** `services/layer4-agents/.env.example` (create)

Minimal file documenting the OIDC env vars consumed by Layer 4:

```bash
# Layer 4 Agents Service — local environment template
# Copy to .env and fill real values. Never commit secrets.

# ============================================
# OIDC / Keycloak Configuration
# ============================================
# Required for OIDC SSO flows. See docs/how-to-guides/configure-sso.md.
OIDC_ISSUER=http://localhost:8080/realms/fabric
OIDC_AUDIENCE=fabric-api
OIDC_JWKS_URL=http://localhost:8080/realms/fabric/protocol/openid-connect/certs

# Alternative: Keycloak auto-URL construction (used when OIDC_JWKS_URL is unset)
# KEYCLOAK_URL=http://localhost:8080
# KEYCLOAK_REALM=fabric

# ============================================
# Internal JWT (service-to-service)
# ============================================
JWT_SECRET=
JWT_ISSUER=value-fabric-internal
JWT_AUDIENCE=value-fabric-services

# ============================================
# Database / Redis
# ============================================
DATABASE_URL=
REDIS_URL=redis://localhost:6379/0
```

### Step 7 — Verify `docs/how-to-guides/configure-sso.md`

Read the current file against the implementation and apply targeted corrections
only if discrepancies are found. Specific things to verify:

- JWKS resolution order matches `jwt.py` (`OIDC_JWKS_JSON` → `OIDC_JWKS_URL` →
  Keycloak auto-URL). ✓ Already correct.
- `client_secret_ref` resolution order matches `oidc.py`. Verify.
- Local dev Keycloak credentials match `docker-compose.dev.yml`. Verify.
- Troubleshooting table entries match actual error messages in the route handler.
  Verify against `services/layer4-agents/src/tenants/api/routes/oidc.py`.

If no discrepancies: no changes needed; note "verified accurate" in final report.

### Step 8 — Validation

Run the following commands and report results:

```bash
# Unit tests for discover() retry fix
pytest tests/shared/identity/test_oidc_discover_retry.py -v

# JWT library parity contract test
pytest tests/contract/test_jwt_library_parity.py -v

# Adversarial auth tests (fixed wiring + new tests)
pytest tests/security/test_adversarial_auth.py -v

# Full security test suite
pytest tests/security/ -v --timeout=30

# Existing OIDC/JWT tests (regression check)
pytest tests/security/test_jwt_validation.py tests/security/test_cross_tenant_jwt.py tests/shared/identity/test_jwks_url.py tests/shared/identity/test_jwt_rotation_and_issuer.py tests/integration/test_oidc_flow.py -v
```

### Step 9 — Final report

Produce a report with:
- Files changed (with brief reason for each)
- Tests added (count and file)
- Validation commands run and results
- Residual risks (dual JWT library, no live Keycloak integration test in CI)
- Follow-up items (e.g., migrate `services/api` to PyJWT, add Keycloak container
  to CI smoke suite)

---

## Key Design Decisions

**`discover()` retry scope:** The fix introduces two exception types —
`OIDCDiscoveryError` (non-retryable) and `TransientOIDCDiscoveryError`
(retryable). The retry wrapper only catches `TransientOIDCDiscoveryError`, so
the classification is explicit and auditable. Transient: HTTP 5xx, 429,
`httpx.TimeoutException`, `httpx.RequestError`. Non-transient: HTTP 4xx (except
429), malformed JSON, missing required discovery fields, any unclassified
exception. `httpx.RequestError` (which includes `httpx.ConnectError` for TLS
failures) is classified as transient deliberately — a single retry on a
connection-level error is operationally useful and low risk. Root cause is always
preserved via `raise ... from exc`.

**Dual JWT library:** Not migrating. `services/api` is a compatibility layer with
its own `python-jose` dependency chain. A contract test is the right tool here —
it catches drift without requiring a migration that could break the services/api
auth path.

**`test_adversarial_auth.py` wiring:** Fixing the fixture rather than replacing
the tests preserves the existing test intent and avoids churn. The fix mirrors the
already-proven pattern in `test_cross_tenant_jwt.py`.

**Frontend:** No code changes. The audit found `AuthContext`, `authClient`, and
`sessionService` to be correctly implemented (httpOnly cookie model, CSRF double-
submit, state validation, no token in JS). This is documented in the final report.

**`configure-sso.md`:** Already exists and is comprehensive. Verification only —
no rewrite.

---

# Spec: Fix authorize_action type guard in signal_tools.py

**Status:** Draft  
**Scope:** Single file — `services/layer4-agents/src/tools/signal_tools.py`  
**Type:** Bug fix / correctness

---

## 1. Problem Statement

In `services/layer4-agents/src/tools/signal_tools.py`, the post-`authorize_action` guard uses `isinstance(ctx, type(_ctx))` to validate the return value. This is a structural check against the dynamic runtime type of the input object rather than a direct check against the known `RequestContext` class.

**Why it is wrong:**

- `type(_ctx)` returns the concrete class of `_ctx` at runtime. If `_ctx` is a plain `RequestContext`, the check happens to be equivalent to `isinstance(ctx, RequestContext)` — but only by accident.
- If `authorize_action` is ever changed to return a `RequestContext` subclass, `isinstance(ctx, type(_ctx))` would **fail** even though the return is a valid context, because `type(_ctx)` is the base class and the return is a subclass.
- The intent is "did `authorize_action` return a valid `RequestContext`", which is expressed correctly and unambiguously as `isinstance(ctx, RequestContext)`.

The guard appears in two functions: `get_account_signals` and `create_signal`.

---

## 2. Root Cause

The guard was introduced as a defensive runtime check against `authorize_action` returning an unexpected type. The implementation used `type(_ctx)` (dynamic lookup of the input's concrete class) instead of `RequestContext` (the statically-known expected type). These are equivalent today but diverge if a subclass is ever returned.

---

## 3. Requirements

1. Replace `isinstance(ctx, type(_ctx))` with `isinstance(ctx, RequestContext)` in both occurrences in `signal_tools.py`.
2. Retain the `tenant_id` presence check (`not getattr(ctx, "tenant_id", None)`) — it is a valid runtime safety check independent of the type guard.
3. No other files are changed.
4. All existing tests continue to pass.

---

## 4. Acceptance Criteria

- `get_account_signals`: guard reads `if not isinstance(ctx, RequestContext) or not getattr(ctx, "tenant_id", None):`
- `create_signal`: guard reads `if not isinstance(ctx, RequestContext) or not getattr(ctx, "tenant_id", None):`
- `isinstance(ctx, type(_ctx))` does not appear anywhere in `signal_tools.py`.
- `RequestContext` is already imported at the top of the file — no new imports needed.
- `PYTHONPATH=src python -m pytest tests/` passes in `services/layer2-5-signal-refinery` (no regression).

---

## 5. Implementation Steps

1. In `services/layer4-agents/src/tools/signal_tools.py`, locate the two occurrences of:
   ```python
   if not isinstance(ctx, type(_ctx)) or not getattr(ctx, "tenant_id", None):
   ```
2. Replace each with:
   ```python
   if not isinstance(ctx, RequestContext) or not getattr(ctx, "tenant_id", None):
   ```
3. Confirm `RequestContext` is imported (it is — imported on line 21 from `value_fabric.shared.identity.context`).
4. Run the test suite to confirm no regressions.
