---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Threat Model

Value Fabric's threat model is structured around real adversaries, specific attack surfaces, and comprehensive OWASP Top 10 coverage. Every threat is paired with automated tests, static analysis rules, and runtime controls.

!!! danger "Behavior-first security"
    No critical security behavior exists unless it is tested. The security test suite is the executable contract. Untested behavior is not production-ready.

## Threat Actors

| Actor | Motivation | Capability | Primary Targets |
|---|---|---|---|
| **External attacker (unauthenticated)** | Data theft, service disruption, credential harvesting | Public internet access, automated scanning | Public endpoints, auth boundaries, injection vectors |
| **Tenant A adversary** | Access Tenant B data, lateral movement | Valid JWT for Tenant A | Cross-tenant APIs, IDOR endpoints, cache keys |
| **Insider (standard user)** | Privilege escalation, unauthorized admin access | Valid standard-user JWT | RBAC endpoints, mass assignment, role tampering |
| **Compromised service account** | Lateral movement between layers | Valid service JWT | Service-to-service APIs, internal queues |
| **Malicious LLM prompt** | Data exfiltration, prompt injection | Control over input text to agent workflows | Layer 4 agent prompts, tool invocation boundaries |
| **Supply chain attacker** | Backdoor injection, dependency compromise | Publish malicious package | npm/pnpm packages, Docker base images |

## Attack Surfaces

| Surface | Layer | Controls |
|---|---|---|
| Public HTTP API | API Gateway + all layers | JWT validation, rate limiting, input validation, tenant isolation |
| OIDC authentication endpoints | API Gateway | Pre-auth rate limiting, PKCE, state parameter validation |
| GraphQL / Cypher query APIs | Layer 3 | Parameterized queries, `cypher-dynamic-guard.yml`, tenant scoping |
| File upload / import | Layer 1, Layer 2 | Path traversal protection, content-type validation, size limits |
| WebSocket streams | Layer 4 | Auth handshake before upgrade, tenant-scoped message routing |
| Agent tool invocation | Layer 4 | Schema-first validation, tenant context inheritance, output contracts |
| Admin dashboards | API Gateway + frontend | RBAC (`admin` role required), MFA for high-risk operations |
| Metrics / health endpoints | All layers | Auth-gated or IP-restricted in production; no secret exposure |
| CI/CD pipeline | GitHub Actions | OIDC-based auth, branch protection, required status checks |
| Kubernetes cluster | Infrastructure | `SecurityContext` hardening, non-root containers, read-only root FS |

## OWASP Top 10 Coverage

### A01: Broken Access Control

**Threats:** IDOR, path traversal, method-level access control, mass assignment, cross-tenant access.

**Controls:**
- UUIDv4 identifiers (not sequential) for all entities
- Tenant isolation at every data boundary (PostgreSQL RLS, Neo4j tenant filters)
- RBAC enforced on every request
- Mass assignment protection: protected fields (`role`, `is_admin`, `password_hash`) are stripped or rejected
- Path traversal blocklists for file operations

**Tests:**
- `test_idor_prevention_on_entity_endpoints`
- `test_path_traversal_blocked`
- `test_mass_assignment_protection`
- `test_http_method_not_allowed_for_role`
- `tests/security/test_auth_boundaries.py`
- `tests/security/test_tenant_isolation.py`

### A02: Cryptographic Failures

**Threats:** Weak password hashing, insecure JWT algorithms, secret leakage, exposed connection strings.

**Controls:**
- API keys use HMAC-SHA256 (64 hex chars), not bcrypt
- JWT uses HS256, RS256, or ES256 only; `none` algorithm rejected
- Passwords never logged (verified by caplog inspection)
- Database connection strings never exposed via API
- Error messages sanitized with `sanitize_log_error()`

**Tests:**
- `test_passwords_not_logged`
- `test_api_keys_use_hmac_not_bcrypt`
- `test_jwt_uses_secure_algorithm`
- `test_secrets_not_in_error_messages`
- `test_database_connection_strings_not_exposed`

### A03: Injection

**Threats:** SQL injection, Cypher injection, XXE, SSTI, LDAP injection.

**Controls:**
- All SQL queries are parameterized; raw f-string SQL is blocked by CI
- Cypher queries use `$tenant_id` parameters; dynamic label interpolation blocked by `.semgrep/cypher-dynamic-guard.yml`
- XML parsing disables external entity expansion
- Template engines (if any) auto-escape user input
- LDAP queries use parameterized filters

**Tests:**
- `test_cypher_injection_blocked`
- `test_xxe_prevention`
- `test_template_injection_blocked`
- `test_ldap_injection_blocked`
- `tests/security/test_injection.py`

### A04: Insecure Design

**Threats:** Missing rate limiting, mutable audit logs, unprotected high-risk operations, resource exhaustion.

**Controls:**
- Rate limiting per tenant + user + endpoint (Redis-backed, fail-closed fallback)
- Audit logs are immutable (DB triggers block UPDATE/DELETE)
- High-risk operations (`delete-tenant`) require confirmation/MFA
- Resource limits on pagination (`limit` capped at 1000)
- Constant-time authentication to prevent user enumeration

**Tests:**
- `test_rate_limiting_enforced`
- `test_audit_logs_immutable`
- `test_sensitive_operations_require_confirmation`
- `test_resource_exhaustion_protection`
- `test_business_logic_timing_attack_mitigation`

### A05: Security Misconfiguration

**Threats:** Default credentials, unnecessary features enabled, verbose error messages, insecure headers.

**Controls:**
- `ProductionSafetyValidator` blocks `DEBUG=true` and dev bypass flags in production
- Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options) enforced
- Kubernetes `SecurityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`, `drop: ALL`
- No default passwords in seed data

**Tests:**
- `tests/security/test_security_misconfiguration.py`
- `tests/security/test_security_headers.py`
- `tests/security/test_seed_data_no_hardcoded_passwords.py`
- `tests/security/test_container_policy.py`

### A06: Vulnerable and Outdated Components

**Threats:** Known CVEs in dependencies, supply chain attacks.

**Controls:**
- Dependabot enabled for automated dependency updates
- `pnpm install --frozen-lockfile` ensures reproducible builds
- Pre-commit hooks block accidental lockfile modifications
- Dockerfile uses pinned base image versions

**Tests:**
- `tests/security/test_dependency_policy.py`
- `tests/security/test_dockerfile_lockfile_fix.py`

### A07: Identification and Authentication Failures

**Threats:** Brute force, credential stuffing, session hijacking, weak password policy.

**Controls:**
- Rate limiting on login and callback endpoints (separate buckets)
- Rate limit uses socket peer IP, not `X-Forwarded-For` (prevents spoofing)
- Session IDs are cryptographically random
- Token refresh rotation

**Tests:**
- `tests/security/test_auth_rate_limiting.py`
- `tests/security/test_auth_session_hijacking.py`
- `tests/security/test_rate_limit_safety.py`

### A08: Software and Data Integrity Failures

**Threats:** CI/CD pipeline compromise, unauthorized code changes.

**Controls:**
- Branch protection on `main` requires PR + passing CI
- Required status checks: `structural-preflight`, per-layer tests, `contract-checks`, `production-readiness-gate`
- `make check-conflict-markers` blocks unresolved merge conflicts
- `make check-pytest-skip-governance` blocks unauthorized test skips

**Tests:**
- `tests/security/test_mandatory_security_regression_gate.py`
- `tests/security/test_collection_verification.py`

### A09: Security Logging and Monitoring Failures

**Threats:** Undetected breaches, insufficient audit trails, log tampering.

**Controls:**
- Structured logs with `request_id`, `tenant_id`, `user_id`
- Immutable audit tables with DB-level protection
- Correlation logging across layers (`test_correlation_logging_contract.py`)
- Security events emitted for tenant context changes, auth failures, and RBAC denials

**Tests:**
- `tests/security/test_audit_event_emission.py`
- `tests/security/test_audit_resilience.py`
- `tests/security/test_audit_retry_queue.py`
- `tests/security/test_correlation_logging_contract.py`

### A10: Server-Side Request Forgery (SSRF)

**Threats:** Crawlers accessing internal metadata services, private IPs, cloud APIs.

**Controls:**
- Layer 1 crawler uses SSRF blocklists for private IP ranges (169.254.x.x, 10.x.x.x, etc.)
- Metadata service endpoints (`169.254.169.254`) are explicitly blocked
- URL validation before HTTP requests

**Tests:**
- `tests/security/test_l1_ssrf_blocklist.py`

## Input Validation

All inputs are validated against JSON Schema / OpenAPI contracts before reaching business logic.

| Input Type | Validation | Layer |
|---|---|---|
| HTTP request body | Pydantic v2 models + OpenAPI spec | API Gateway / all layers |
| Query parameters | Typed validators, max limits | API Gateway |
| Path parameters | UUID format, existence checks | Route handlers |
| File uploads | Content-type, size, path traversal | Layer 1, Layer 2 |
| LLM prompts | Prompt delimiter validation (`test_p1_12_prompt_delimiters.py`) | Layer 4 |
| Graph queries | Cypher parameterization + allowlists | Layer 3 |

## Rate Limiting

Rate limiting is enforced by `GovernanceMiddleware` with the following scopes:

| Scope | Key Dimensions | Endpoints |
|---|---|---|
| `USER` | `tenant_id` + `user_id` | Authenticated API calls |
| `IP` | Client socket peer IP | Pre-auth endpoints (`/auth/oidc/.../login`) |
| `TENANT` | `tenant_id` | Tenant-wide quotas |
| `GLOBAL` | Global key | Health checks, public metadata |

!!! note "Fail-closed behavior"
    If Redis is unavailable, the rate limiter falls back to an in-memory limiter capped at 5 requests per window. This prevents unbounded access while maintaining partial service.

## Audit Logging for Security Events

Security-relevant events are logged to an immutable audit store:

| Event | When | Data |
|---|---|---|
| `TENANT_CONTEXT_SET` | DB session initialization | `tenant_id`, `isolation_tier`, `bypass=False` |
| `AUTHENTICATION_FAILURE` | Invalid/missing token | `request_id`, `endpoint`, `error_code` |
| `AUTHORIZATION_DENIED` | RBAC mismatch | `user_id`, `required_permission`, `endpoint` |
| `RATE_LIMIT_EXCEEDED` | 429 response | `key`, `limit`, `retry_after` |
| `AUDIT_MUTATION_BLOCKED` | Attempt to modify audit log | `user_id`, `attempted_action` |

Audit emission is non-blocking: if the audit backend is unavailable, the request flow continues without raising.

## Validation Commands

```bash
# OWASP Top 10 tests
pytest tests/security/test_owasp_top10.py -v
pytest tests/security/test_owasp_top10_complete.py -v

# Injection tests
pytest tests/security/test_injection.py -v
pytest tests/security/test_p1_20_xxe_prevention.py -v

# SSRF
pytest tests/security/test_l1_ssrf_blocklist.py -v

# Rate limiting
pytest tests/security/test_rate_limit_safety.py -v
pytest tests/security/test_rate_limit_response.py -v
pytest tests/security/test_rate_limit_window.py -v

# Audit and logging
pytest tests/security/test_audit_event_emission.py -v
pytest tests/security/test_audit_resilience.py -v
pytest tests/security/test_correlation_logging_contract.py -v

# Security headers and misconfiguration
pytest tests/security/test_security_headers.py -v
pytest tests/security/test_security_misconfiguration.py -v

# Container and dependency policy
pytest tests/security/test_container_policy.py -v
pytest tests/security/test_dependency_policy.py -v

# Full security suite
pytest tests/security/ -v
```
