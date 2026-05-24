# Auth/JWKS Test Failure Report

**Date**: 2026-05-24
**Analysis Scope**: Pre-existing test failures in auth enforcement and JWKS validation

## Executive Summary

22 pre-existing test failures were identified across two test files. These failures are **not caused by current changes** and should be tracked as a separate remediation effort.

## Verification of Current Changes

### Modified File: services/api/app/main.py
- **Change**: Added `clerk_webhooks` router import and mounted it at `/internal/*`
- **Impact**: NEW router for Clerk webhook handling - not a modification to existing security/config/JWKS paths
- **Boundaries Verified**:
  - ✅ Does NOT modify `app/core/security.py`
  - ✅ Does NOT modify `app/core/config.py`
  - ✅ Does NOT modify JWKS validation, JWKS cache, JWKS fetch, or token validation paths
  - ✅ Does NOT modify password hashing helpers
  - ✅ Does NOT modify bcrypt behavior

### Other Modified Files
All other modified files are unrelated to authentication/security:
- Docker compose files
- Layer service main.py files (L1, L2, L3, L4, L5, L6)
- Environment example files
- Frontend files (App.tsx, routing, auth context)
- Migration files

## Test Results

### Commands Run
```bash
python -m pytest services/api/app/tests/test_auth_enforcement.py -v --tb=short
python -m pytest services/api/app/tests/test_jwks_and_token_validation.py -v --tb=short
```

### Failure Breakdown

#### services/api/app/tests/test_auth_enforcement.py
**Status**: 19 failed, 8 passed

**Failure Categories**:
1. **bcrypt 72-byte password limit (17 failures)**
   - Error: `ValueError: password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])`
   - Affected tests:
     - test_cross_tenant_token_header_misuse_uses_jwt_tenant
     - TestUnauthenticatedRequests::test_no_credentials_returns_401[GET-/v1/accounts]
     - TestUnauthenticatedRequests::test_tenant_header_alone_returns_401[GET-/v1/governance/review-queue]
     - TestUnauthenticatedRequests::test_no_credentials_returns_401[GET-/v1/governance/review-queue]
     - TestUnauthenticatedRequests::test_tenant_header_alone_returns_401[GET-/v1/accounts]
     - TestTamperedToken::test_empty_bearer_returns_401
     - TestTamperedToken::test_malformed_bearer_returns_401
     - TestTamperedToken::test_wrong_audience_returns_401
     - TestTamperedToken::test_wrong_issuer_returns_401
     - TestTamperedToken::test_tampered_signature_returns_401
     - TestTamperedToken::test_unsigned_token_returns_401
     - TestPublicEndpoints::test_public_endpoint_accessible_without_auth[GET-/metrics]
     - TestPublicEndpoints::test_public_endpoint_accessible_without_auth[GET-/health]
     - TestExpiredToken::test_expired_jwt_returns_401
     - TestExpiredToken::test_expired_jwt_error_message
     - TestTenantClaimRequired::test_missing_tenant_claim_returns_401
     - TestTenantClaimRequired::test_blank_tenant_claim_returns_401

2. **Missing function (1 failure)**
   - Error: `NameError: name 'revoke_token' is not defined`
   - Affected test: test_revoked_token_returns_401

3. **Regex assertion (1 failure)**
   - Error: `AssertionError: Regex pattern did not match`
   - Affected test: TestProductionSecretGuard::test_custom_secret_still_requires_production_persistence_policy

#### services/api/app/tests/test_jwks_and_token_validation.py
**Status**: 3 failed, 8 passed

**Failure Categories**:
1. **JWKS cache TTL test (1 failure)**
   - Error: `AssertionError: assert 0 == 1` (mock_urlopen.call_count)
   - Affected test: TestJWKSCaching::test_jwks_cache_ttl_expires
   - Root cause: Network resolution failure in test environment

2. **JWKS resolution order tests (2 failures)**
   - Error: `AssertionError: Expected '_fetch_fjwks_from_url' to be called once. Called 2 times`
   - Affected tests:
     - TestKeycloakJWKSResolution::test_jwks_resolution_order_explicit_url_second
     - TestKeycloakJWKSResolution::test_jwks_resolution_order_keycloak_third

## Classification: Pre-existing / Out of Scope

These failures are **pre-existing** and **out of scope** for the current PR because:

1. **Current changes did not touch security/config/JWKS code**: The only API service change was adding a new Clerk webhook router, which is unrelated to existing auth enforcement or JWKS validation logic.

2. **bcrypt 72-byte limit failures**: These are a known bcrypt limitation requiring a dedicated password policy design decision. The current work did not modify any password hashing code.

3. **JWKS cache TTL failures**: These relate to JWKS cache timing/TTL expectations. The current work did not modify JWKS cache behavior or token validation paths.

4. **Missing revoke_token function**: This is a pre-existing test implementation issue, not caused by current changes.

5. **Production secret guard regex**: This is a pre-existing test assertion issue, not caused by current changes.

## Recommended Follow-up Ticket

**Title**: Remediate pre-existing auth enforcement and JWKS validation test failures

**Acceptance Criteria**:
- Decide and document password length policy for bcrypt's 72-byte limit
- Add deterministic tests for over-72-byte passwords
- Fix or stabilize JWKS cache TTL test behavior
- Ensure JWKS cache tests avoid wall-clock flakiness where possible
- Confirm all tests in test_auth_enforcement.py and test_jwks_and_token_validation.py pass independently
- Address the missing `revoke_token` function in test_revoked_token_returns_401
- Fix the production secret guard regex assertion in test_custom_secret_still_requires_production_persistence_policy

## PR Note Section (Ready to Use)

```markdown
## Pre-existing Test Failures (Out of Scope)

The following test failures are pre-existing and not caused by this PR:

- **services/api/app/tests/test_auth_enforcement.py**: 19 failures
  - 17 failures: bcrypt 72-byte password limit (requires dedicated password policy design)
  - 1 failure: missing revoke_token function
  - 1 failure: production secret guard regex assertion

- **services/api/app/tests/test_jwks_and_token_validation.py**: 3 failures
  - 1 failure: JWKS cache TTL test (mock_urlopen.call_count assertion)
  - 2 failures: JWKS resolution order tests (call count assertion)

**Total**: 22 pre-existing failures

**Confirmation**: Current changes did not modify app/core/security.py, app/core/config.py, JWKS paths, or password hashing logic. The only API service change was adding a new Clerk webhook router.

**Follow-up**: Track remediation in separate ticket: "Remediate pre-existing auth enforcement and JWKS validation test failures"
```

## Test Commands for Reference

```bash
# Run the failing tests to verify current status
python -m pytest services/api/app/tests/test_auth_enforcement.py -v --tb=short
python -m pytest services/api/app/tests/test_jwks_and_token_validation.py -v --tb=short

# Run both together
python -m pytest services/api/app/tests/test_auth_enforcement.py services/api/app/tests/test_jwks_and_token_validation.py -v --tb=short
```
