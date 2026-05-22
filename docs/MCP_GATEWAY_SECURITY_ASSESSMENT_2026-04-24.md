> **STATUS: ARCHIVED** — historical security assessment (2026-04-24). See [docs/archive/INDEX.md](archive/INDEX.md). Current MCP gateway docs live under [reference/](reference/) and [security/](security/).

# MCP Gateway Security Assessment (2026-04-24)

## Scope

Assessed `packages/shared/src/value_fabric/shared/mcp_gateway/` and directly related test coverage to evaluate:

- secure implementation quality,
- hardening level for production use,
- multi-tenant isolation posture,
- priority actions to improve customer confidence.

## Executive Summary

**Overall readiness: NOT production hardened yet (high risk if internet-exposed).**

The MCP gateway has a good architectural intent (tenant-scoped registry, OAuth/PKCE concepts, token exchange, audit hooks), but several critical controls are currently placeholder or optional in ways that can permit bypass.

### Security posture scorecard

- **Design intent:** Moderate-to-strong
- **Implementation maturity:** Low-to-moderate
- **Production hardening:** Low
- **Multi-tenant assurance:** Moderate design, weak enforcement at runtime

## What is already good

1. **Tenant-aware registry pattern exists.**
   The gateway builds tool requests through tenant authorization checks in `ToolRegistry.get_tenant_scoped_request()`. This is a strong baseline for isolation-by-default when consistently enforced.

2. **OAuth + PKCE support is present.**
   `OAuthHandler` includes PKCE challenge generation with S256 and uses constant-time comparison for challenge verification.

3. **Delegation model exists (RFC 8693 pattern).**
   `TokenExchanger.exchange_token()` models subject-token to delegated-token exchange and carries tool/tenant metadata.

4. **Audit instrumentation hooks exist.**
   Gateway attempts to emit audit events per invocation including tenant, actor, timing, and token details.

5. **Some unit test coverage passes.**
   Unit suite runs with 17 tests passing (11 skipped), indicating core scaffolding is testable.

## Critical findings (must fix before production)

### 1) Manifest signature verification is not cryptographically enforced (CRITICAL)

- `ManifestVerifier` explicitly states verification is placeholder.
- `_verify_jws()` returns `True` without real RSA signature validation for non-empty signatures after basic payload checks.
- `ManifestSigner` also generates placeholder signatures.

**Impact:** Tool provenance can be forged; malicious tool manifests may be accepted.

### 2) Actor token generation is insecure placeholder (CRITICAL)

- `TokenExchanger._create_actor_token()` returns base64-encoded JSON and comments “not for production”.

**Impact:** Actor token can be forged/tampered; delegated identity chain is not trustworthy.

### 3) Gateway allows invocation without token exchange (HIGH)

- `MCPGateway.invoke_tool()` falls back to direct invocation when no `delegated_token` and no `user_token`/`token_exchanger` are provided, logging only a warning.

**Impact:** Authentication and delegation controls can be bypassed by configuration or caller misuse.

### 4) Tool execution path is placeholder (HIGH)

- `_execute_tool()` returns synthetic success payload instead of secure outbound call logic.

**Impact:** Security properties for upstream communication (mTLS, audience-bound tokens, retry/circuit behavior, egress policy, SSRF prevention) are not yet implemented in this module.

### 5) Registry permits unverified tool registration (HIGH)

- `ToolRegistry.register_tool()` only warns when tool is unverified/unsigned and still registers it.

**Impact:** Supply-chain trust model is optional; weakens integrity guarantees.

## Significant quality signals from tests

1. **Security suite appears out of sync with implementation.**
   `tests/security/test_auth_security.py` references manifest fields that no longer exist (`input_schema`, `required_permissions`, etc.), causing fixture/type errors.

2. **Async security tests fail without plugin context when run with local addopts override.**
   Many async tests fail due plugin/runtime setup in this environment when bypassing global pytest options.

3. **Observed command outcomes:**
   - unit: `17 passed, 11 skipped`
   - security: `18 failed, 4 errors`

**Impact:** Security claims are currently not strongly validated by reliable, passing automated tests.

## Multi-tenant risk analysis

### Current positives

- Tenant-specific enablement exists (`_tenant_tools`, `is_tool_enabled`, `get_tool`).
- Tool request carries `tenant_id` and `user_id` into audit path.

### Remaining multi-tenant gaps

- Tenant boundary depends on caller-provided `tenant_id`; no built-in binding of `tenant_id` to validated token claims in `MCPGateway.invoke_tool()`.
- Direct invocation fallback can execute without delegated token.
- Unverified manifests can be registered and tenant-enabled.

**Bottom line:** isolation model is present but not yet strongly non-bypassable.

## Recommended remediation plan

### Phase 0 (immediate, blocker for production)

1. Enforce fail-closed auth path in gateway:
   - Require either valid delegated token or successful token exchange.
   - Remove/feature-flag-off insecure direct invocation path.

2. Implement real JWS verification/signing:
   - Use `python-jose` or `PyJWT` + `cryptography`.
   - Require allowed algorithms (`RS256`/`ES256`), validate `kid`, issuer, and JWKS rotation.
   - Reject unsigned manifests in registry (hard fail).

3. Replace actor token placeholder with signed JWT:
   - Sign with platform private key in HSM/KMS-backed flow.
   - Add audience/resource binding and short TTL.

4. Bind tenant identity to authenticated claims:
   - Derive effective tenant from verified token claims (`org_id`/`tenant_id`) and compare to request context.

### Phase 1 (hardening)

1. Build secure upstream invocation in `_execute_tool()`:
   - outbound allowlist,
   - strict URL/protocol validation,
   - mTLS/service identity,
   - per-tool timeout + circuit breaker,
   - no user token forwarding.

2. Strengthen policy model:
   - explicit per-tool/per-tenant/per-user policy checks,
   - deny-by-default authorization policies,
   - scoped consent checks where required.

3. Improve audit integrity:
   - guaranteed delivery strategy (queue/outbox),
   - tamper-evident audit chaining/hash.

### Phase 2 (assurance and customer trust)

1. Repair and align security test suite with current datamodel.
2. Add threat-model-driven tests (confused deputy, cross-tenant token replay, forged manifest, JWKS key rotation).
3. Add SAST/DAST + dependency scanning gates for gateway package.
4. Publish customer-facing security controls document for MCP gateway (authn, authz, isolation, key mgmt, logging).

## Suggested release gate for this component

Do not call this gateway production-ready until all are true:

- cryptographic manifest verification enabled and mandatory,
- delegated token path enforced (no insecure fallback),
- tenant claim binding validated server-side,
- security test suite green and included in CI merge gate,
- third-party security review completed for this package.
