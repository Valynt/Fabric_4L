---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Authentication Boundaries

Value Fabric enforces strict authentication boundaries at every layer. No unauthenticated request may access protected resources. This page documents the OIDC/Keycloak integration, JWT validation rules, service-to-service authentication, session and token refresh semantics, and the dev auth bypass flags that are categorically blocked in production.

!!! danger "Production Invariant"
    No unauthenticated or improperly authenticated access to protected resources is permitted. The `ProductionSafetyValidator` will cause startup failure if any dev auth bypass flag is set in a production-like environment.

## Authentication Architecture

The platform uses a layered middleware stack for request processing. The **auth** phase (order 3) validates credentials and establishes tenant context. Downstream code never re-validates authentication; it consumes the `RequestContext` established by the middleware.

| Phase | Order | Responsibility | Can Terminate |
|---|---|---|---|
| request_id | 1 | Assign `x-request-id` | No |
| correlation | 2 | Extract/inject correlation IDs | No |
| **auth** | **3** | **Validate credentials, establish tenant context** | **Yes (401/403)** |
| tenant_scope | 4 | Validate tenant access | Yes (403) |
| rate_limit | 5 | Apply rate limiting | Yes (429) |
| validation | 6 | Validate request against OpenAPI | Yes (400) |
| handler | 7 | Execute business logic | Yes |
| error_boundary | Global | Catch errors, normalize shape | Yes |

## OIDC / Keycloak Integration

User-facing authentication is delegated to Keycloak via the OpenID Connect (OIDC) protocol. The platform does not implement its own password storage for end users.

- **Identity Provider:** Keycloak (self-hosted or external OIDC-compatible IdP)
- **Protocol:** OpenID Connect (Authorization Code Flow with PKCE)
- **Token Format:** JWT (JSON Web Token)
- **Signing Algorithms:** HS256, RS256, or ES256 only

### Token Claims

Every JWT issued by the platform's auth boundary must contain the following claims:

| Claim | Purpose | Example |
|---|---|---|
| `sub` | User identifier (UUID) | `"user-123"` |
| `tenant_id` | Tenant scope (UUID) | `"tenant-a"` |
| `role` | RBAC role | `"standard"`, `"admin"`, `"read_only"` |
| `exp` | Expiration timestamp | `1704067200` |
| `iat` | Issued-at timestamp | `1704063600` |
| `iss` | Token issuer | `"https://auth.example.com"` |
| `aud` | Intended audience | `"value-fabric-api"` |

!!! warning "JWT claim precedence"
    The `tenant_id` claim inside the JWT takes precedence over any `X-Tenant-ID` header or request body field. Header-based tenant spoofing is ignored. Attempts to supply a mismatched `X-Tenant-ID` header are either rejected with 403 or the JWT tenant is enforced.

## Token Validation

The platform enforces strict JWT validation at the middleware layer. The following tests in `tests/security/test_auth_boundaries.py` verify these invariants:

### Rejected Token Types (401)

| Scenario | Expected Behavior | Test Reference |
|---|---|---|
| Missing `Authorization` header | `401` + `WWW-Authenticate` header | `test_no_auth_header_rejected` |
| Empty / whitespace-only header | `401` | `test_empty_auth_header_rejected` |
| Invalid `Bearer` token format | `401` | `test_invalid_token_format_rejected` |
| `Basic` auth prefix | `401` | `test_wrong_token_prefix_rejected` |
| Gibberish / random string token | `401` | `test_gibberish_token_rejected` |
| SQL injection in token payload | `401` | `test_sql_injection_in_token_blocked` |
| XSS attempt in token payload | `401` + no reflection | `test_xss_in_token_sanitized` |
| Truncated JWT (missing signature) | `401` | `test_truncated_token_rejected` |
| Extra JWT parts | `401` | `test_extra_parts_token_rejected` |
| Invalid base64 | `401` | `test_invalid_base64_token_rejected` |
| Empty payload JWT | `401` | `test_empty_payload_token_rejected` |
| Expired JWT | `401` + expired detail | `test_expired_token_rejected` |
| JWT with `iat` in the future | `401` (clock skew protection) | `test_future_issued_jwt_rejected` |
| JWT with `none` algorithm | `401` / `403` | `test_none_algorithm_rejected` |
| Algorithm confusion (RS256 → HS256) | `401` / `403` | `test_algorithm_confusion_attack_blocked` |
| Tampered signature | `401` | `test_invalid_signature_rejected` |
| Modified `role` claim | `401` / `403` | `test_modified_role_claim_rejected` |
| Modified `tenant_id` claim | `401` / `403` | `test_modified_tenant_claim_rejected` |

!!! danger "Algorithm policy"
    Only `HS256`, `RS256`, and `ES256` are permitted. The `none` algorithm and weak algorithms (`HS1`, `HS384`, `HS512` without explicit validation) are rejected. Algorithm confusion attacks (e.g., claiming `RS256` but signing with HMAC) are blocked.

### Role-Based Access Control (RBAC)

RBAC is validated on every request, not just at login. The permission model supports both OR-logic (`has_any_permission`) and AND-logic (`has_all_permissions`).

| Role | Typical Permissions |
|---|---|
| `read_only` | `read` only |
| `standard` | `read`, limited `write` |
| `advanced` | `read`, `write`, formula access |
| `admin` | Full CRUD, admin endpoints, user management |

!!! warning "Permission bypass prevention"
    Wildcard permissions (`permissions: ["*"]`) are discarded during JWT context extraction. The `has_any_permission` OR-logic returns `False` when the permission set is empty. The `has_all_permissions` AND-logic requires every listed permission; partial matches are rejected. These invariants are tested in `tests/security/test_rbac.py`.

### API Key Authentication

API keys use HMAC-SHA256 for fast verification (not bcrypt). Keys are scoped to a specific tenant and cannot escalate beyond the associated user's role.

```python
# Secure: API key scoped to tenant
headers = {"X-API-Key": "test-tenant-a-key"}

# Insecure (blocked): API key with attempted cross-tenant header
headers = {
    "X-API-Key": "test-tenant-a-key",
    "X-Tenant-ID": "tenant-b",  # Rejected — key is scoped to tenant-a
}
```

## Service-to-Service Authentication

Internal communication between layers (L1–L6) uses JWT-based service authentication. Each service validates the calling service's token against a shared secret or public key.

| Concern | Pattern |
|---|---|
| Cross-service header | `x-fabric-tenant-id` with signature verification |
| Message queue | Explicit `tenant_id` field in every Celery/Redis payload |
| Service identity | `service_account_id` claim in JWT |
| Validation | Same JWT middleware as user tokens, with additional `iss`/`aud` checks |

Tests in `tests/security/test_l1l2_service_to_service_jwt.py` and `tests/security/test_cross_stack_jwt_contract.py` enforce that service-to-service tokens:
- Are validated with the same strictness as user tokens
- Carry correct tenant context
- Cannot be replayed across service boundaries

## Session Management

- **Token lifetime:** Short-lived access tokens (recommended: 15 minutes)
- **Refresh tokens:** Long-lived refresh tokens stored securely by the frontend; rotation is enforced
- **Session correlation:** `x-fabric-session-id` header for cross-request continuity
- **Logout:** Token revocation list (Redis) for immediate invalidation

### Token Refresh

The OIDC refresh endpoint (`/auth/oidc/{provider}/refresh`) is rate-limited independently from login and callback endpoints. Rate limit keys include both tenant and user dimensions to prevent cross-tenant refresh abuse.

```bash
# Rate limit key format for authenticated auth-scope requests
ratelimit:user:{tenant_id}:{user_id}:auth
```

## Dev Auth Bypass Flags

!!! danger "NEVER enable in production"
    The following environment variables are for **local development only**. They are validated by `ProductionSafetyValidator` and will cause startup failure in production-like environments:

| Variable | Purpose | Production Effect |
|---|---|---|
| `DEV_AUTH_BYPASS=true` | Skip auth checks in dev | **Startup failure** |
| `ALLOW_DEV_AUTH_BYPASS=true` | Allow dev bypass | **Startup failure** |
| `AUTH_BYPASS_ENABLED=true` | Enable auth bypass | **Startup failure** |
| `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` | Insecure bypass | **Startup failure** |

### Bypass Flag Enforcement

The `validate_production_safety()` function (from `value_fabric.shared.security.config`) is called during service startup. It rejects:
- All bypass flags in `production`, `prod`, `staging`, `stage`, and `preprod` environments
- `DEBUG=true` in production
- Case-insensitive and whitespace-padded variants (`TRUE`, `True`, `1`, `yes`, ` true `)

```python
# tests/security/test_dev_bypass.py
@pytest.mark.parametrize("bypass_var,bypass_value", _BYPASS_VARS)
def test_bypass_flag_rejected_in_production(monkeypatch, bypass_var, bypass_value):
    _set_base_env(monkeypatch, "production")
    monkeypatch.setenv(bypass_var, bypass_value)
    with pytest.raises(RuntimeError, match=bypass_var):
        validate_production_safety(environment="production")
```

In development, bypass flags are allowed but emit a `WARNING` log so operators are aware.

## Frontend Auth Bypass Detection

The frontend build pipeline includes a dedicated test that asserts no dev auth bypass code is present in the production bundle:

```bash
pnpm --dir apps/web run test:prod-auth-bypass
```

This scans the built output for strings like `DEV_AUTH_BYPASS`, mock auth providers, or hardcoded tokens.

## Secure vs Insecure Patterns

### Secure

```python
# Extract tenant from authenticated context, never from the request body
tenant_id = ctx.tenant_id
repo.method(..., tenant_id=tenant_id)

# Validate JWT with explicit allowed algorithms
jwt.decode(token, secret, algorithms=["HS256", "RS256"], options={"require": ["exp", "iat"]})

# Rate-limit auth endpoints by tenant + user
key = f"ratelimit:user:{tenant_id}:{user_id}:auth"
```

### Insecure (Blocked by CI)

```python
# NEVER trust request body tenant IDs
tenant_id = request.json().get("tenant_id")  # BLOCKED

# NEVER allow the 'none' algorithm
jwt.decode(token, secret, algorithms=["none"])  # BLOCKED

# NEVER hardcode bypass flags in application code
if os.getenv("DEV_AUTH_BYPASS") == "true":  # BLOCKED in production
    skip_auth()
```

## Validation Commands

```bash
# Auth boundary tests
pytest tests/security/test_auth_boundaries.py -v

# RBAC and permission logic
pytest tests/security/test_rbac.py -v
pytest tests/security/test_rbac_expanded.py -v

# Default-deny behavior
pytest tests/security/test_auth_default_deny.py -v

# JWT configuration validation
pytest tests/security/test_jwt_config_validation.py -v
pytest tests/security/test_jwt_validation.py -v
pytest tests/security/test_jwt_rotation.py -v

# Dev bypass guardrails
pytest tests/security/test_dev_bypass.py -v
pytest tests/security/test_production_bypass_guardrails.py -v

# OIDC-specific tests
pytest tests/security/test_oidc.py -v

# Rate limiting on auth endpoints
pytest tests/security/test_auth_rate_limiting.py -v
```
